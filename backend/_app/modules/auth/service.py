# Lógica de negocio para auth.
from . import repository


def safe_next_path(candidate):
    """Path relativo interno seguro para redirect post-login; None si no es válido."""
    if not candidate:
        return None
    s = str(candidate).strip()
    if not s.startswith('/') or s.startswith('//'):
        return None
    if '\\' in s or '\n' in s or '\r' in s:
        return None
    return s


def login(email, password):
    user = repository.get_user_by_email(email)
    if not user:
        return False, None, 'Credenciales inválidas.'
    if not user.is_active:
        return False, None, 'Cuenta desactivada.'
    if not user.check_password(password):
        return False, None, 'Credenciales inválidas.'
    return True, user, None


def change_password(user, new_password, confirm_password):
    if not new_password or len(new_password) < 8:
        return False, 'La contraseña debe tener al menos 8 caracteres.'
    if new_password != confirm_password:
        return False, 'Las contraseñas no coinciden.'
    repository.update_password_and_clear_must_change(user, new_password)
    return True, None
