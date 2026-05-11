"""Almacenamiento de comprobantes Yappy manual bajo uploads/payments/yappy/{org_id}/."""

from __future__ import annotations

import os
import secrets

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = frozenset({'jpg', 'jpeg', 'png', 'webp', 'pdf'})
ALLOWED_MIMES = frozenset(
    {
        'image/jpeg',
        'image/jpg',
        'image/png',
        'image/webp',
        'application/pdf',
    }
)


def extension_allowed(filename: str) -> bool:
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def mime_allowed(content_type: str | None) -> bool:
    if not content_type:
        return False
    return content_type.split(';')[0].strip().lower() in ALLOWED_MIMES


def yappy_upload_root(app) -> str:
    return getattr(app, 'YAPPY_PAYMENT_UPLOAD_ROOT', None) or os.path.normpath(
        os.path.join(app.root_path, '..', 'uploads', 'payments', 'yappy')
    )


def save_yappy_receipt_file(
    app,
    file_storage: FileStorage,
    *,
    organization_id: int | None,
) -> tuple[str, str]:
    """
    Guarda el archivo y devuelve (receipt_disk_path relativo al YAPPY_PAYMENT_UPLOAD_ROOT, nombre original saneado).
    receipt_disk_path ej.: \"12/ab3f....pdf\"
    """
    if not file_storage or not file_storage.filename:
        raise ValueError('Archivo vacío')

    raw_name = file_storage.filename
    if not extension_allowed(raw_name):
        raise ValueError('Extensión no permitida')

    ct = (file_storage.content_type or '').strip()
    if ct and not mime_allowed(ct):
        raise ValueError('Tipo de archivo no permitido')

    max_bytes = int(getattr(app, 'YAPPY_RECEIPT_MAX_BYTES', 5 * 1024 * 1024))
    stream = file_storage.stream
    try:
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(0)
    except Exception:
        size = None
    if size is not None and size > max_bytes:
        raise ValueError('El archivo supera el tamaño máximo permitido (5 MB).')

    ext = raw_name.rsplit('.', 1)[1].lower()
    safe_base = secure_filename(raw_name.rsplit('.', 1)[0]) or 'comprobante'
    if len(safe_base) > 80:
        safe_base = safe_base[:80]
    unique = f"{safe_base}_{secrets.token_hex(6)}.{ext}"

    oid = int(organization_id) if organization_id is not None else 0
    root = yappy_upload_root(app)
    dest_dir = os.path.join(root, str(oid))
    os.makedirs(dest_dir, exist_ok=True)

    dest_path = os.path.join(dest_dir, unique)
    try:
        stream.seek(0)
    except Exception:
        pass
    file_storage.save(dest_path)

    if os.path.getsize(dest_path) > max_bytes:
        try:
            os.remove(dest_path)
        except Exception:
            pass
        raise ValueError('El archivo supera el tamaño máximo permitido (5 MB).')

    rel = f"{oid}/{unique}"
    return rel, raw_name


def absolute_path_for_disk_rel(app, receipt_disk_path: str | None) -> str | None:
    if not receipt_disk_path or '..' in receipt_disk_path.replace('\\', '/'):
        return None
    root = yappy_upload_root(app)
    full = os.path.normpath(os.path.join(root, receipt_disk_path))
    if not full.startswith(os.path.normpath(root) + os.sep) and full != os.path.normpath(root):
        return None
    return full if os.path.isfile(full) else None
