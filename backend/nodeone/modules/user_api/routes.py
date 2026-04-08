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


@user_api_bp.route('/communication-preferences', methods=['GET'])
@login_required
def api_user_communication_preferences_get():
    """Preferencias por evento y canal (ausencia de fila = canal permitido)."""
    try:
        from models.communication_rules import CommunicationEvent, UserCommunicationPreference

        events = CommunicationEvent.query.order_by(CommunicationEvent.code.asc()).all()
        events = [e for e in events if not (e.code or '').startswith('__')]

        rows = UserCommunicationPreference.query.filter_by(user_id=current_user.id).all()
        by_key = {(p.event_id, p.channel): bool(p.enabled) for p in rows}

        items = []
        for ev in events:
            for ch in ('email', 'in_app'):
                items.append(
                    {
                        'event_id': ev.id,
                        'event_code': ev.code,
                        'event_name': ev.name,
                        'category': ev.category,
                        'channel': ch,
                        'enabled': by_key.get((ev.id, ch), True),
                    }
                )
        return jsonify({'success': True, 'items': items})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@user_api_bp.route('/communication-preferences', methods=['PUT'])
@login_required
def api_user_communication_preferences_put():
    """Body: {\"items\": [{\"event_code\", \"channel\", \"enabled\"}]}."""
    from app import db
    from models.communication_rules import CommunicationEvent, UserCommunicationPreference

    data = request.get_json() or {}
    raw_items = data.get('items')
    if not isinstance(raw_items, list):
        return jsonify({'success': False, 'error': 'items debe ser una lista'}), 400

    try:
        for it in raw_items:
            code = (it.get('event_code') or '').strip()
            channel = (it.get('channel') or '').strip().lower()
            if channel not in ('email', 'in_app', 'sms'):
                continue
            ev = CommunicationEvent.query.filter_by(code=code).first()
            if not ev or (ev.code or '').startswith('__'):
                continue
            enabled = bool(it.get('enabled', True))
            row = UserCommunicationPreference.query.filter_by(
                user_id=current_user.id,
                event_id=ev.id,
                channel=channel,
            ).first()
            if row:
                row.enabled = enabled
            else:
                db.session.add(
                    UserCommunicationPreference(
                        user_id=current_user.id,
                        event_id=ev.id,
                        channel=channel,
                        enabled=enabled,
                    )
                )
        db.session.commit()
        return jsonify({'success': True, 'message': 'Preferencias de comunicación guardadas'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
