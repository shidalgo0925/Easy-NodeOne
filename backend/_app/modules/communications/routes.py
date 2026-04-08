# Rutas de notificaciones (usuario): bandeja + API (URLs API sin cambio).
from flask import Blueprint, redirect, request, jsonify, render_template, url_for
from flask_login import login_required, current_user

from . import service

communications_bp = Blueprint('communications', __name__, url_prefix='')


def _render_notifications_inbox():
    try:
        notifications, unread_count = service.get_page_data(current_user.id)
        return render_template('notifications.html', notifications=notifications, unread_count=unread_count)
    except Exception:
        return render_template('notifications.html', notifications=[], unread_count=0)


@communications_bp.route('/communications/inbox')
@login_required
def communications_inbox():
    """Bandeja in-app (URL canónica)."""
    return _render_notifications_inbox()


@communications_bp.route('/notifications')
@login_required
def notifications_page():
    """Compatibilidad: redirige a la bandeja unificada."""
    return redirect(url_for('communications.communications_inbox'), code=302)


@communications_bp.route('/api/notifications')
@login_required
def api_notifications():
    notification_type = request.args.get('type', 'all')
    status = request.args.get('status', 'all')
    limit = min(int(request.args.get('limit', 50)), 100)
    data = service.list_notifications(current_user.id, notification_type, status, limit)
    return jsonify(data)


@communications_bp.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    result, error = service.mark_read(current_user.id, notification_id)
    if error:
        return jsonify({'success': False, 'error': error}), 404
    return jsonify({'success': True, 'message': 'Notificación marcada como leída', 'notification': result})


@communications_bp.route('/api/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    service.mark_all_read(current_user.id)
    return jsonify({'success': True, 'message': 'Todas las notificaciones han sido marcadas como leídas'})


@communications_bp.route('/api/notifications/<int:notification_id>', methods=['DELETE'])
@login_required
def delete_notification(notification_id):
    ok, error = service.delete_one(current_user.id, notification_id)
    if not ok:
        return jsonify({'success': False, 'error': error or 'Notificación no encontrada'}), 404
    return jsonify({'success': True, 'message': 'Notificación eliminada'})


@communications_bp.route('/api/notifications/<int:notification_id>/toggle-read', methods=['POST'])
@login_required
def toggle_notification_read(notification_id):
    result, error = service.toggle_read(current_user.id, notification_id)
    if error:
        return jsonify({'success': False, 'error': error}), 404
    action = 'leída' if result['is_read'] else 'no leída'
    return jsonify({'success': True, 'message': f'Notificación marcada como {action}', 'notification': result})


@communications_bp.route('/api/notifications/delete-read', methods=['DELETE'])
@login_required
def delete_read_notifications():
    try:
        count, _ = service.delete_read(current_user.id)
        return jsonify({'success': True, 'message': f'{count} notificación(es) leída(s) eliminada(s)', 'deleted_count': count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@communications_bp.route('/api/notifications/delete-all', methods=['DELETE'])
@login_required
def delete_all_notifications():
    try:
        count, _ = service.delete_all(current_user.id)
        return jsonify({'success': True, 'message': f'{count} notificación(es) eliminada(s)', 'deleted_count': count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
