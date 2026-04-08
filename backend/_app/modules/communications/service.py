# Lógica de notificaciones (usuario).
from . import repository


def get_page_data(user_id):
    """Datos para la bandeja /communications/inbox (lista + unread_count)."""
    notifications = repository.get_user_notifications(user_id, 'all', 'all', limit=500)
    unread = repository.unread_count(user_id)
    return notifications, unread


def list_notifications(user_id, notification_type='all', status='all', limit=50):
    notifications = repository.get_user_notifications(user_id, notification_type, status, limit)
    unread_count = repository.unread_count(user_id)
    return {
        'unread_count': unread_count,
        'total': len(notifications),
        'notifications': [_to_dict(n) for n in notifications],
    }


def _to_dict(n):
    return {
        'id': n.id,
        'title': n.title,
        'message': n.message,
        'type': n.notification_type,
        'is_read': n.is_read,
        'event_id': n.event_id,
        'created_at': n.created_at.isoformat() if n.created_at else None,
        'email_sent': n.email_sent,
        'email_sent_at': n.email_sent_at.isoformat() if n.email_sent_at else None,
    }


def toggle_read(user_id, notification_id):
    n = repository.get_by_id_and_user(notification_id, user_id)
    if not n:
        return None, 'Notificación no encontrada'
    is_read = repository.toggle_read(n)
    return {'id': n.id, 'is_read': is_read}, None


def mark_read(user_id, notification_id):
    n = repository.get_by_id_and_user(notification_id, user_id)
    if not n:
        return None, 'Notificación no encontrada'
    if n.is_read:
        return {'id': n.id, 'is_read': True}, None
    repository.mark_read(n)
    return {'id': n.id, 'is_read': True}, None


def mark_all_read(user_id):
    repository.mark_all_read(user_id)
    return True, None


def delete_one(user_id, notification_id):
    n = repository.get_by_id_and_user(notification_id, user_id)
    if not n:
        return False, 'Notificación no encontrada'
    repository.delete_one(n)
    return True, None


def delete_read(user_id):
    return repository.delete_read(user_id), None


def delete_all(user_id):
    return repository.delete_all(user_id), None
