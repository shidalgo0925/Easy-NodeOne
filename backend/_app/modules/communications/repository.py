# Acceso a datos para notificaciones del usuario.
from app import db, Notification


def get_user_notifications(user_id, notification_type='all', status='all', limit=50):
    q = Notification.query.filter_by(user_id=user_id)
    if notification_type != 'all':
        q = q.filter_by(notification_type=notification_type)
    if status == 'read':
        q = q.filter_by(is_read=True)
    elif status == 'unread':
        q = q.filter_by(is_read=False)
    return q.order_by(Notification.created_at.desc()).limit(limit).all()


def unread_count(user_id):
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()


def get_by_id_and_user(notification_id, user_id):
    return Notification.query.filter_by(id=notification_id, user_id=user_id).first()


def toggle_read(notification):
    notification.is_read = not notification.is_read
    db.session.commit()
    return notification.is_read


def mark_read(notification):
    notification.mark_as_read()
    db.session.commit()


def mark_all_read(user_id):
    Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
    db.session.commit()


def delete_one(notification):
    db.session.delete(notification)
    db.session.commit()


def delete_read(user_id):
    c = Notification.query.filter_by(user_id=user_id, is_read=True).delete()
    db.session.commit()
    return c


def delete_all(user_id):
    c = Notification.query.filter_by(user_id=user_id).delete()
    db.session.commit()
    return c
