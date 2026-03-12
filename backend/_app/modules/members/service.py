# Lógica de negocio para members (perfil).
import os
from datetime import datetime
from . import repository

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_photo(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def upload_profile_photo(user, file, upload_dir):
    """Guarda el archivo en upload_dir, actualiza user en DB. Retorna (success, photo_url o error_msg)."""
    if not file or file.filename == '':
        return False, 'No se seleccionó ningún archivo'
    if not allowed_photo(file.filename):
        return False, 'Formato de archivo no permitido'
    os.makedirs(upload_dir, exist_ok=True)
    ext = os.path.splitext(file.filename)[1]
    filename = f"{user.id}_{int(datetime.utcnow().timestamp())}{ext}"
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)
    if user.profile_picture:
        old_path = os.path.join(upload_dir, user.profile_picture)
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass
    repository.update_profile_picture(user, filename)
    return True, filename


def remove_profile_photo(user, upload_dir):
    """Elimina archivo físico y limpia en DB. Retorna (success, error_msg)."""
    if not user.profile_picture:
        return False, 'No hay foto de perfil para eliminar'
    filepath = os.path.join(upload_dir, user.profile_picture)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception:
            pass
    repository.clear_profile_picture(user)
    return True, None


def update_profile(user, data):
    """Actualiza first_name, last_name, phone, country, cedula_or_passport. Retorna (success, error_msg)."""
    first_name = (data.get('first_name') or '').strip()
    last_name = (data.get('last_name') or '').strip()
    if not first_name or not last_name:
        return False, 'Nombre y apellido son requeridos'
    repository.update_profile_data(
        user,
        first_name,
        last_name,
        (data.get('phone') or '').strip() or None,
        (data.get('country') or '').strip() or None,
        (data.get('cedula_or_passport') or '').strip() or None,
    )
    return True, None
