# Acceso a datos para members (perfil).
from app import db


def update_profile_picture(user, filename):
    user.profile_picture = filename
    db.session.add(user)
    db.session.commit()


def clear_profile_picture(user):
    user.profile_picture = None
    db.session.add(user)
    db.session.commit()


def update_profile_data(user, first_name, last_name, phone=None, country=None, cedula_or_passport=None):
    user.first_name = first_name
    user.last_name = last_name
    user.phone = phone or None
    user.country = country or None
    user.cedula_or_passport = cedula_or_passport or None
    db.session.add(user)
    db.session.commit()
