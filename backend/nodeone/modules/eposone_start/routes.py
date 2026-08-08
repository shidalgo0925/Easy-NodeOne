"""Rutas públicas Asistente de Inicio EPosOne — /start + API + App Link."""

from __future__ import annotations

from flask import Blueprint, Response, abort, jsonify, make_response, redirect, render_template, request, url_for

from nodeone.modules.eposone_start.recommend import catalog_payload, recommend_for_business_type
from nodeone.modules.eposone_start.service import (
    StartAssistantError,
    complete_start,
    download_cta_label,
    play_store_url,
    ready_status,
    resend_standalone_verification,
)

eposone_start_bp = Blueprint('eposone_start', __name__)


def _is_eposone_surface() -> bool:
    try:
        from nodeone.core.platform.context_resolver import current_app_context

        return (current_app_context().product.code or '').strip().lower() == 'eposone'
    except Exception:
        return False


def _require_eposone_surface() -> None:
    if not _is_eposone_surface():
        abort(404)


def _public_base_from_request() -> str | None:
    xf_proto = (request.headers.get('X-Forwarded-Proto') or '').split(',')[0].strip()
    xf_host = (request.headers.get('X-Forwarded-Host') or '').split(',')[0].strip()
    if xf_host:
        scheme = xf_proto or 'https'
        return f'{scheme}://{xf_host}'.rstrip('/')
    root = (request.url_root or '').rstrip('/')
    return root or None


@eposone_start_bp.route('/start')
@eposone_start_bp.route('/start/ready')
def start_assistant():
    """SPA del Asistente de Inicio (solo superficie producto EPosOne)."""
    _require_eposone_surface()
    catalog = catalog_payload()
    download_url = play_store_url()
    return render_template(
        'eposone_start/start.html',
        catalog=catalog,
        play_store_url=download_url,
        download_cta_label=download_cta_label(download_url),
        brand_favicon='images/logo-eposone.svg',
        initial_ready_token=(request.args.get('ready_token') or '').strip() or None,
        start_path=request.path,
    )


@eposone_start_bp.route('/api/public/eposone-start/catalog', methods=['GET'])
def start_catalog():
    _require_eposone_surface()
    business_type = request.args.get('business_type')
    return jsonify(catalog_payload(business_type))


@eposone_start_bp.route('/api/public/eposone-start/recommend', methods=['GET', 'POST'])
def start_recommend():
    _require_eposone_surface()
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        business_type = data.get('business_type')
    else:
        business_type = request.args.get('business_type')
    return jsonify(recommend_for_business_type(business_type))


@eposone_start_bp.route('/api/public/eposone-start/complete', methods=['POST'])
def start_complete():
    _require_eposone_surface()
    data = request.get_json(silent=True) or {}
    try:
        public_base = _public_base_from_request()
        result = complete_start(
            full_name=str(data.get('full_name') or data.get('name') or ''),
            email=str(data.get('email') or ''),
            password=str(data.get('password') or ''),
            business_name=str(data.get('business_name') or ''),
            business_type=str(data.get('business_type') or ''),
            country=str(data.get('country') or '') or None,
            plan_code=str(data.get('plan_code') or 'standalone'),
            accept_terms=bool(data.get('accept_terms')),
            accept_privacy=bool(data.get('accept_privacy')),
            accept_eula=bool(data.get('accept_eula')),
            phone=str(data.get('phone') or data.get('whatsapp') or '') or None,
            attribution={
                'channel': data.get('channel') or 'web',
                'source_detail': data.get('source_detail') or data.get('source'),
                'campaign': data.get('campaign'),
                'referral_code': data.get('referral_code'),
                'advisor_user_id': data.get('advisor_user_id'),
                'utm_source': data.get('utm_source') or request.args.get('utm_source'),
                'utm_medium': data.get('utm_medium') or request.args.get('utm_medium'),
                'utm_campaign': data.get('utm_campaign') or request.args.get('utm_campaign'),
                'utm_content': data.get('utm_content') or request.args.get('utm_content'),
                'utm_term': data.get('utm_term') or request.args.get('utm_term'),
                'landing_url': data.get('landing_url') or request.url,
            },
            ip_address=(request.headers.get('X-Forwarded-For') or request.remote_addr or '')
            .split(',')[0]
            .strip()
            or None,
            public_base=public_base,
        )
        resp = make_response(jsonify(result), 201)
        if result.get('ready_token'):
            resp.set_cookie(
                'eposone_ready_token',
                result['ready_token'],
                max_age=7 * 24 * 3600,
                httponly=False,
                samesite='Lax',
                secure=request.is_secure,
                path='/',
            )
        return resp
    except StartAssistantError as exc:
        return jsonify({'ok': False, 'error': exc.code, 'message': exc.message}), exc.http_status
    except Exception:
        return (
            jsonify(
                {
                    'ok': False,
                    'error': 'prepare_failed',
                    'message': (
                        'No pudimos completar este paso. Tu información está guardada. '
                        'Intenta nuevamente.'
                    ),
                }
            ),
            500,
        )


@eposone_start_bp.route('/api/public/eposone-start/ready-status', methods=['GET'])
def start_ready_status():
    """Estado Standalone post-/start. El mail de código lo asegura el service (idempotente)."""
    _require_eposone_surface()
    token = (
        (request.args.get('ready_token') or '').strip()
        or (request.cookies.get('eposone_ready_token') or '').strip()
    )
    if not token:
        return jsonify({'ok': False, 'error': 'ready_token_missing', 'message': 'Falta sesión de instalación.'}), 400
    try:
        result = ready_status(ready_token=token, public_base=_public_base_from_request())
        return jsonify(result), 200
    except StartAssistantError as exc:
        return jsonify({'ok': False, 'error': exc.code, 'message': exc.message}), exc.http_status


@eposone_start_bp.route('/api/public/eposone-start/resend-verification', methods=['POST'])
def start_resend_verification():
    """Reenvío del correo de verificación (misma vía que registro web)."""
    _require_eposone_surface()
    data = request.get_json(silent=True) or {}
    token = (
        (data.get('ready_token') or '').strip()
        or (request.args.get('ready_token') or '').strip()
        or (request.cookies.get('eposone_ready_token') or '').strip()
    )
    if not token:
        return jsonify({'ok': False, 'error': 'ready_token_missing', 'message': 'Falta sesión de instalación.'}), 400
    try:
        result = resend_standalone_verification(ready_token=token)
        return jsonify(result), 200
    except StartAssistantError as exc:
        return jsonify({'ok': False, 'error': exc.code, 'message': exc.message}), exc.http_status


@eposone_start_bp.route('/activate')
def start_activate_bridge_legacy():
    """Legacy ?token=manual_code → redirect a path si resolvemos jti; si no, UI fallback."""
    _require_eposone_surface()
    legacy = (request.args.get('token') or '').strip()
    if legacy:
        try:
            from nodeone.core.platform.activation_service import ActivationService

            _lic, tok = ActivationService._resolve_credential('manual_code', legacy, product_code='eposone')
            if tok and tok.jti:
                return redirect(url_for('eposone_start.start_activate_ref', activation_ref=tok.jti))
        except Exception:
            pass
    return render_template(
        'eposone_start/activate.html',
        activation_ref='',
        app_link='',
        deep_link='',
        manual_mode=True,
        brand_favicon='images/logo-eposone.svg',
    )


@eposone_start_bp.route('/activate/<activation_ref>')
def start_activate_ref(activation_ref: str):
    """App Link HTTPS — transporte técnico ADR-035 v1.3 (no QR comercial)."""
    _require_eposone_surface()
    ref = (activation_ref or '').strip()
    app_link = ''
    deep_link = f'eposone://activate/{ref}' if ref else ''
    modality = None
    status = None
    try:
        from nodeone.core.platform.activation_service import ActivationService

        lic, tok = ActivationService.get_by_activation_ref(ref)
        pub = ActivationService._token_public(tok, lic, public_base=_public_base_from_request())
        app_link = pub.get('app_link') or ''
        deep_link = pub.get('deep_link') or deep_link
        modality = pub.get('modality')
        status = getattr(tok, 'status', None)
    except Exception:
        pass
    return render_template(
        'eposone_start/activate.html',
        activation_ref=ref,
        app_link=app_link or f'{(_public_base_from_request() or "").rstrip("/")}/activate/{ref}',
        deep_link=deep_link,
        modality=modality,
        token_status=status,
        manual_mode=False,
        brand_favicon='images/logo-eposone.svg',
    )


@eposone_start_bp.route('/activate/<activation_ref>/qr.png')
def start_activate_qr(activation_ref: str):
    """QR de activación = App Link (misma autorización)."""
    _require_eposone_surface()
    from nodeone.modules.qr_generator.services import generate_png_bytes

    ref = (activation_ref or '').strip()
    if not ref:
        abort(404)
    try:
        size = int(request.args.get('size') or 320)
    except (TypeError, ValueError):
        size = 320
    size = max(160, min(size, 1024))
    base = (_public_base_from_request() or '').rstrip('/')
    app_link = f'{base}/activate/{ref}'
    png = generate_png_bytes(
        app_link,
        int(size),
        'M',
        style={'fill': '#001a4b', 'bg': '#ffffff', 'border': 2},
    )
    return Response(
        png,
        mimetype='image/png',
        headers={
            'Cache-Control': 'no-store',
            'Content-Disposition': f'inline; filename=eposone-activate-{ref[:12]}.png',
        },
    )


@eposone_start_bp.route('/start/install-help')
def start_install_help():
    _require_eposone_surface()
    return render_template(
        'eposone_start/install_help.html',
        play_store_url=play_store_url(),
        brand_favicon='images/logo-eposone.svg',
    )


@eposone_start_bp.route('/start/install-help/qr.png')
def start_install_help_qr():
    _require_eposone_surface()
    from nodeone.modules.qr_generator.services import generate_png_bytes

    try:
        size = int(request.args.get('size') or 320)
    except (TypeError, ValueError):
        size = 320
    size = max(160, min(size, 1024))
    help_url = request.url_root.rstrip('/') + '/start/install-help'
    png = generate_png_bytes(
        help_url,
        int(size),
        'M',
        style={'fill': '#001a4b', 'bg': '#ffffff', 'border': 2},
    )
    return Response(
        png,
        mimetype='image/png',
        headers={'Cache-Control': 'public, max-age=3600', 'Content-Disposition': 'inline; filename=eposone-install-help-qr.png'},
    )


def register_eposone_start_blueprint(app) -> None:
    if 'eposone_start' not in app.blueprints:
        app.register_blueprint(eposone_start_bp)
