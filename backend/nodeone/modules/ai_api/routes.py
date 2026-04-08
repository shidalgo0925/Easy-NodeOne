"""IA: ping local, config admin, test admin."""

from functools import wraps
from datetime import datetime

from flask import Blueprint, current_app, flash, jsonify, redirect, request, url_for
from flask_login import current_user, login_required

ai_api_bp = Blueprint('ai_api', __name__)


def _admin_required_lazy(f):
    """Misma lógica que app.admin_required; importa app solo en request (evita ciclo al registrar)."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        import app as M

        if bool(getattr(current_user, 'must_change_password', False)):
            flash('Debes cambiar tu contraseña antes de continuar.', 'warning')
            return redirect(url_for('auth.change_password'))
        if not current_user.is_admin and not M._user_has_any_admin_permission(current_user):
            flash('No tienes permisos para acceder a esta página.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)

    return decorated_function


@ai_api_bp.route('/api/ai/ping', methods=['POST'])
def api_ai_ping():
    """Diagnóstico simple de IA sin depender de la sesión web admin. Solo acceso local."""
    remote_addr = (request.headers.get('X-Forwarded-For') or request.remote_addr or '').split(',')[0].strip()
    if remote_addr not in ('127.0.0.1', '::1', 'localhost'):
        return jsonify({'success': False, 'error': 'Acceso permitido solo desde localhost.'}), 403

    import app as M

    M.ensure_ai_config()
    data = request.get_json(silent=True) or {}
    prompt = (data.get('prompt') or 'hola').strip() or 'hola'
    session_id = (data.get('session_id') or 'diagnostic').strip() or 'diagnostic'

    try:
        from _app.services.ai_service import ask_ai_detailed

        result = ask_ai_detailed(
            prompt=prompt, session_id=session_id, extra_context={'source': 'api_ai_ping'}, organization_id=1
        )
        return jsonify(result), (200 if result.get('success') else result.get('status_code') or 502)
    except Exception as e:
        current_app.logger.exception('AI ping failed')
        return jsonify({'success': False, 'error': str(e)}), 500


@ai_api_bp.route('/api/admin/ai/config', methods=['GET', 'POST', 'PUT'])
@_admin_required_lazy
def api_ai_config():
    """GET: obtener config IA. POST/PUT: guardar config IA."""
    import app as M

    M.ensure_ai_config()
    coid = M._catalog_org_for_admin_catalog_routes()
    cfg = M.AIConfig.get_active_config(organization_id=coid)
    if request.method == 'GET':
        return jsonify({'success': True, 'config': cfg.to_dict() if cfg else None})

    data = request.get_json(silent=True) or {}

    api_url = (data.get('api_url') or cfg.api_url or '').strip()
    collection = (data.get('collection') or cfg.collection or 'nodeone').strip()
    try:
        timeout_seconds = int(data.get('timeout_seconds', cfg.timeout_seconds or 30))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'timeout_seconds debe ser numérico.'}), 400

    if not api_url:
        return jsonify({'success': False, 'error': 'API URL es obligatoria.'}), 400
    if not collection:
        return jsonify({'success': False, 'error': 'Collection es obligatoria.'}), 400
    if timeout_seconds < 3 or timeout_seconds > 60:
        return jsonify({'success': False, 'error': 'Timeout debe estar entre 3 y 60 segundos.'}), 400

    cfg.enabled = bool(data.get('enabled', cfg.enabled))
    cfg.api_url = api_url
    cfg.collection = collection
    cfg.timeout_seconds = timeout_seconds
    cfg.fallback_to_local = bool(data.get('fallback_to_local', cfg.fallback_to_local))
    cfg.is_active = True
    if 'api_key' in data and (data.get('api_key') or '').strip():
        cfg.api_key = (data.get('api_key') or '').strip()
    cfg.updated_at = datetime.utcnow()

    try:
        M.db.session.commit()
        return jsonify({'success': True, 'config': cfg.to_dict()})
    except Exception as e:
        M.db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@ai_api_bp.route('/api/admin/ai/test', methods=['POST'])
@_admin_required_lazy
def api_ai_test():
    """Probar un prompt manual contra la IA configurada."""
    import app as M

    M.ensure_ai_config()
    cfg = M.AIConfig.get_active_config(organization_id=M._catalog_org_for_admin_catalog_routes())
    data = request.get_json(silent=True) or {}
    prompt = (data.get('prompt') or '').strip()
    session_id = (data.get('session_id') or f'admin-test-{current_user.id}').strip()

    if not prompt:
        return jsonify({'success': False, 'error': 'El prompt es obligatorio.'}), 400
    if not cfg or not cfg.enabled:
        return jsonify({'success': False, 'error': 'La IA está desactivada. Actívala primero en Configuración -> IA.'}), 400

    try:
        from _app.services.ai_service import ask_ai_detailed

        result = ask_ai_detailed(
            prompt=prompt,
            session_id=session_id,
            extra_context={'source': 'admin_test'},
            organization_id=M._catalog_org_for_admin_catalog_routes(),
        )
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error') or 'La IA no devolvió respuesta.',
                'upstream_http_status': result.get('status_code'),
            }), 200
        return jsonify({'success': True, 'response': result.get('response'), 'session_id': session_id})
    except Exception as e:
        current_app.logger.exception('AI test failed')
        return jsonify({'success': False, 'error': str(e)}), 200
