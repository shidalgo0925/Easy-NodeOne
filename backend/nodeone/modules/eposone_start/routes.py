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


@eposone_start_bp.route('/api/public/eposone-start/complete', methods=['POST'])
def start_complete():
    _require_eposone_surface()
    data = request.get_json(silent=True) or {}
    try:
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


def register_eposone_start_blueprint(app) -> None:
    if 'eposone_start' not in app.blueprints:
        app.register_blueprint(eposone_start_bp)
