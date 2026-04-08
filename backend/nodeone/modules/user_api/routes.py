"""Blueprint /api/user — estado, dashboard, membresía, preferencias."""

import json

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

user_api_bp = Blueprint('user_api', __name__, url_prefix='/api/user')


@user_api_bp.route('/status', methods=['GET'])
@login_required
def get_user_status():
    """API endpoint para obtener el estado completo del usuario."""
    try:
        from app import db
        from user_status_checker import UserStatusChecker

        user_status = UserStatusChecker.check_user_status(current_user.id, db.session)
        return jsonify({'success': True, 'status': user_status}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@user_api_bp.route('/dashboard', methods=['GET'])
@login_required
def get_user_dashboard():
    """API endpoint para obtener datos completos del dashboard."""
    try:
        from app import db
        from user_status_checker import UserStatusChecker

        dashboard_data = UserStatusChecker.get_user_dashboard_data(current_user.id, db.session)
        return jsonify({'success': True, 'dashboard': dashboard_data}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@user_api_bp.route('/membership')
@login_required
def api_user_membership():
    """API para obtener información de membresía del usuario."""
    membership = current_user.get_active_membership()
    if membership:
        return jsonify({
            'type': membership.membership_type,
            'start_date': membership.start_date.isoformat(),
            'end_date': membership.end_date.isoformat(),
            'is_active': membership.is_active,
            'payment_status': membership.payment_status,
        })
    return jsonify({'error': 'No active membership found'}), 404


@user_api_bp.route('/settings', methods=['GET'])
@login_required
def api_user_settings_get():
    """Obtener preferencias de configuración del usuario."""
    try:
        from app import UserSettings, _default_user_preferences

        row = UserSettings.query.filter_by(user_id=current_user.id).first()
        prefs = _default_user_preferences()
        if row and row.preferences:
            prefs.update(json.loads(row.preferences))
        return jsonify({'success': True, 'preferences': prefs})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@user_api_bp.route('/settings', methods=['POST'])
@login_required
def api_user_settings_post():
    """Guardar preferencias de configuración del usuario."""
    from app import UserSettings, _default_user_preferences, db

    data = request.get_json()
    if not data or not isinstance(data.get('preferences'), dict):
        return jsonify({'success': False, 'error': 'Datos no válidos'}), 400
    try:
        prefs = {k: v for k, v in data['preferences'].items() if k in _default_user_preferences()}
        row = UserSettings.query.filter_by(user_id=current_user.id).first()
        if not row:
            row = UserSettings(user_id=current_user.id, preferences=json.dumps(prefs))
            db.session.add(row)
        else:
            row.preferences = json.dumps(prefs)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Configuración guardada'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
