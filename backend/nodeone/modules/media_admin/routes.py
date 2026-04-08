"""Panel admin de multimedia y API JSON; GET público /api/media/config/<procedure_key>."""

from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from functools import wraps

media_admin_bp = Blueprint('media_admin', __name__)


def _admin_required_lazy(f):
    """Igual que app.admin_required; importa app en request (evita ciclo)."""
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


def _media_configs_query(M, organization_id=None, procedure_key=None, only_active=False):
    q = M.MediaConfig.query
    if procedure_key is not None:
        q = q.filter(M.MediaConfig.procedure_key == procedure_key)
    if only_active:
        q = q.filter(M.MediaConfig.is_active.is_(True))
    if organization_id is not None and hasattr(M.MediaConfig, 'organization_id'):
        q = q.filter(M.MediaConfig.organization_id == int(organization_id))
    return q


@media_admin_bp.route('/admin/media')
@_admin_required_lazy
def admin_media():
    """Panel de configuración de videos y audios para guías visuales."""
    import app as M

    coid = M._catalog_org_for_admin_catalog_routes()
    all_configs = _media_configs_query(M, organization_id=coid, only_active=True).order_by(
        M.MediaConfig.procedure_key, M.MediaConfig.step_number
    ).all()

    procedures = {}
    for config in all_configs:
        if config.procedure_key not in procedures:
            procedures[config.procedure_key] = []
        procedures[config.procedure_key].append(config.to_dict())

    available_procedures = {
        'register': 'Registro de Usuario',
        'membership': 'Compra de Membresía',
        'payment': 'Proceso de Pago',
        'events': 'Registro a Eventos',
        'appointments': 'Reserva de Citas',
        'admin-payments': 'Configuración de Métodos de Pago',
    }

    return render_template(
        'admin/media.html',
        procedures=procedures,
        available_procedures=available_procedures,
    )


@media_admin_bp.route('/api/admin/media/config', methods=['GET', 'POST', 'PUT', 'DELETE'])
@_admin_required_lazy
def api_media_config():
    """API para gestionar configuración de multimedia."""
    import app as M

    coid = M._catalog_org_for_admin_catalog_routes()
    if request.method == 'GET':
        configs = _media_configs_query(M, organization_id=coid, only_active=True).order_by(
            M.MediaConfig.procedure_key, M.MediaConfig.step_number
        ).all()
        return jsonify({'success': True, 'configs': [c.to_dict() for c in configs]})

    if request.method == 'POST':
        data = request.get_json()
        existing = _media_configs_query(
            M,
            organization_id=coid,
            procedure_key=data.get('procedure_key'),
        ).filter(M.MediaConfig.step_number == data.get('step_number')).first()

        if existing:
            return jsonify({
                'success': False,
                'error': 'Ya existe una configuración para este procedimiento y paso',
            }), 400

        config = M.MediaConfig(
            procedure_key=data.get('procedure_key'),
            step_number=data.get('step_number'),
            video_url=data.get('video_url', ''),
            audio_url=data.get('audio_url', ''),
            step_title=data.get('step_title', ''),
            description=data.get('description', ''),
            is_active=True,
        )
        if hasattr(config, 'organization_id'):
            config.organization_id = int(coid)

        try:
            M.db.session.add(config)
            M.db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Configuración creada exitosamente',
                'config': config.to_dict(),
            })
        except Exception as e:
            M.db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

    if request.method == 'PUT':
        data = request.get_json()
        config_id = data.get('id')

        if not config_id:
            return jsonify({'success': False, 'error': 'ID de configuración requerido'}), 400

        config = M.MediaConfig.query.get(config_id)
        if not config:
            return jsonify({'success': False, 'error': 'Configuración no encontrada'}), 404
        if hasattr(config, 'organization_id') and int(config.organization_id or 1) != int(coid):
            return jsonify({'success': False, 'error': 'Configuración no encontrada'}), 404

        if 'video_url' in data:
            config.video_url = data.get('video_url', '')
        if 'audio_url' in data:
            config.audio_url = data.get('audio_url', '')
        if 'step_title' in data:
            config.step_title = data.get('step_title', '')
        if 'description' in data:
            config.description = data.get('description', '')
        if 'is_active' in data:
            config.is_active = bool(data.get('is_active', True))

        config.updated_at = datetime.utcnow()

        try:
            M.db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Configuración actualizada exitosamente',
                'config': config.to_dict(),
            })
        except Exception as e:
            M.db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

    if request.method == 'DELETE':
        config_id = request.args.get('id')

        if not config_id:
            return jsonify({'success': False, 'error': 'ID de configuración requerido'}), 400

        config = M.MediaConfig.query.get(config_id)
        if not config:
            return jsonify({'success': False, 'error': 'Configuración no encontrada'}), 404
        if hasattr(config, 'organization_id') and int(config.organization_id or 1) != int(coid):
            return jsonify({'success': False, 'error': 'Configuración no encontrada'}), 404

        try:
            M.db.session.delete(config)
            M.db.session.commit()
            return jsonify({'success': True, 'message': 'Configuración eliminada exitosamente'})
        except Exception as e:
            M.db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

    return jsonify({'success': False, 'error': 'Método no permitido'}), 405


@media_admin_bp.route('/api/media/config/<procedure_key>')
def get_media_config(procedure_key):
    """API pública para obtener configuraciones de multimedia (para el frontend)."""
    import app as M

    try:
        coid = M.tenant_data_organization_id()
    except Exception:
        coid = None
    configs = _media_configs_query(
        M,
        organization_id=coid,
        procedure_key=procedure_key,
        only_active=True,
    ).order_by(M.MediaConfig.step_number).all()
    return jsonify({
        'success': True,
        'procedure_key': procedure_key,
        'configs': [c.to_dict() for c in configs],
    })
