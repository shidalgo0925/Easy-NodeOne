"""Subida de foto/PDF de contrato en Contactos EN1."""

from __future__ import annotations

import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename

_ALLOWED_EXT = frozenset({'.jpg', '.jpeg', '.png', '.webp', '.pdf'})


def contracts_upload_dir(organization_id: int) -> str:
    root = os.path.join(
        current_app.root_path,
        '..',
        'static',
        'uploads',
        'contacts',
        str(int(organization_id)),
        'contracts',
    )
    os.makedirs(root, exist_ok=True)
    return root


def save_contact_contract_file(organization_id: int, file_storage) -> str:
    if not file_storage or not getattr(file_storage, 'filename', None):
        raise ValueError('No se recibió archivo del contrato.')
    name = secure_filename(file_storage.filename or '') or 'contrato'
    ext = os.path.splitext(name)[1].lower()
    if ext not in _ALLOWED_EXT:
        raise ValueError('Formato de contrato no permitido. Use JPG, PNG, WebP o PDF.')
    new_name = f'{uuid.uuid4().hex}{ext}'
    path = os.path.join(contracts_upload_dir(organization_id), new_name)
    file_storage.save(path)
    return f'/static/uploads/contacts/{int(organization_id)}/contracts/{new_name}'
