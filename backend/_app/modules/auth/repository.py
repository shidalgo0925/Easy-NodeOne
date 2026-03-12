# Acceso a datos para auth.
def get_user_by_email(email):
    from app import db, User
    if not email or not isinstance(email, str):
        return None
    return User.query.filter_by(email=email.strip().lower()).first()


def update_password_and_clear_must_change(user, new_password):
    from app import db
    user.set_password(new_password)
    user.must_change_password = False
    db.session.add(user)
    db.session.commit()
