"""Subida de foto/logo para contactos (por organización)."""

from __future__ import annotations

import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename

_ALLOWED_EXT = frozenset({'.jpg', '.jpeg', '.png', '.webp', '.gif'})


def contacts_upload_dir(organization_id: int) -> str:
    root = os.path.join(
        current_app.root_path,
        '..',
        'static',
        'uploads',
        'contacts',
        str(int(organization_id)),
    )
    os.makedirs(root, exist_ok=True)
    return root


def save_contact_photo(organization_id: int, file_storage) -> str:
    if not file_storage or not getattr(file_storage, 'filename', None):
        raise ValueError('No se recibió archivo de imagen.')
    name = secure_filename(file_storage.filename or '') or 'photo'
    ext = os.path.splitext(name)[1].lower()
    if ext not in _ALLOWED_EXT:
        raise ValueError('Formato no permitido. Use JPG, PNG, WebP o GIF.')
    new_name = f'{uuid.uuid4().hex}{ext}'
    path = os.path.join(contacts_upload_dir(organization_id), new_name)
    file_storage.save(path)
    return f'/static/uploads/contacts/{int(organization_id)}/{new_name}'
