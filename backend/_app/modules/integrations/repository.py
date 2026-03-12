# Acceso a datos para integraciones (Office365 solicitudes).
from app import db, Office365Request, User


def create_office365_request(user_id, email, purpose, description, discount_code_id=None):
    req = Office365Request(
        user_id=user_id,
        email=email,
        purpose=purpose[:255],
        description=description[:2000],
        status='pending',
        discount_code_id=discount_code_id,
    )
    db.session.add(req)
    db.session.commit()
    return req


def get_admin_emails():
    admins = User.query.filter_by(is_admin=True).filter(
        User.email.isnot(None)
    ).filter(User.email != '').all()
    return list({a.email for a in admins if a.email})
