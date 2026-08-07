"""Rutas públicas Asistente de Inicio EPosOne — /start + API."""

from __future__ import annotations

from flask import Blueprint, abort, jsonify, render_template, request

from nodeone.modules.eposone_start.recommend import catalog_payload, recommend_for_business_type
from nodeone.modules.eposone_start.service import (
    StartAssistantError,
    complete_start,
    download_cta_label,
    play_store_url,
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


@eposone_start_bp.route('/start')
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


def _public_base_from_request() -> str | None:
    """Base pública preferida (proxy) para activate_url / transporte."""
    xf_proto = (request.headers.get('X-Forwarded-Proto') or '').split(',')[0].strip()
    xf_host = (request.headers.get('X-Forwarded-Host') or '').split(',')[0].strip()
    if xf_host:
        scheme = xf_proto or 'https'
        return f'{scheme}://{xf_host}'.rstrip('/')
    root = (request.url_root or '').rstrip('/')
    return root or None


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
            plan_code=str(data.get('plan_code') or 'starter'),
            accept_terms=bool(data.get('accept_terms')),
            accept_privacy=bool(data.get('accept_privacy')),
            accept_eula=bool(data.get('accept_eula')),
            ip_address=(request.headers.get('X-Forwarded-For') or request.remote_addr or '')
            .split(',')[0]
            .strip()
            or None,
            public_base=public_base,
        )
        return jsonify(result), 201
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


@eposone_start_bp.route('/activate')
def start_activate_bridge():
    """Puente HTTPS → deep link EP1 (transporte técnico ADR-035; no es QR comercial)."""
    _require_eposone_surface()
    token = (request.args.get('token') or '').strip()
    deep_link = f'eposone://activate?token={token}' if token else ''
    return render_template(
        'eposone_start/activate.html',
        token=token,
        deep_link=deep_link,
        brand_favicon='images/logo-eposone.svg',
    )


@eposone_start_bp.route('/start/install-help')
def start_install_help():
    """Guía pública de instalación Android (QR de ayuda — no descarga APK)."""
    _require_eposone_surface()
    return render_template(
        'eposone_start/install_help.html',
        play_store_url=play_store_url(),
        brand_favicon='images/logo-eposone.svg',
    )


@eposone_start_bp.route('/start/install-help/qr.png')
def start_install_help_qr():
    """QR de ayuda: URL de la guía (nunca el APK)."""
    _require_eposone_surface()
    from flask import Response

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
