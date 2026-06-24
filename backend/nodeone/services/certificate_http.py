"""URLs base y rutas de upload compartidas por certificados (membresía y eventos)."""

from __future__ import annotations

import os
import uuid

_ALLOWED_CERT_IMAGE_EXT = frozenset({'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'})


def certificate_base_url() -> str:
    """URL pública del sitio para QR, verify y assets en PDF."""
    try:
        from flask import request

        if request and request.url_root:
            return request.url_root.rstrip('/')
    except Exception:
        pass
    base = (os.getenv('BASE_URL') or '').strip().rstrip('/')
    if base:
        return base
    return 'https://app.easynodeone.com'


def certificates_upload_dir(*, app=None) -> str:
    """Directorio `static/uploads/certificates` (fondos, logos, sellos)."""
    if app is None:
        try:
            from flask import current_app

            app = current_app
        except Exception:
            app = None
    if app is not None:
        path = os.path.abspath(os.path.join(app.root_path, '..', 'static', 'uploads', 'certificates'))
    else:
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.abspath(os.path.join(backend_dir, '..', 'static', 'uploads', 'certificates'))
    os.makedirs(path, exist_ok=True)
    return path


def save_certificate_image_upload(file_storage, *, prefix: str = 'tpl') -> tuple[str | None, str | None]:
    """Guarda imagen en uploads/certificates. Retorna (url /static/..., mensaje error)."""
    if not file_storage or not getattr(file_storage, 'filename', None):
        return None, 'Falta el archivo'
    ext = (os.path.splitext(file_storage.filename)[1] or '.png').lower()
    if ext not in _ALLOWED_CERT_IMAGE_EXT:
        return None, 'Formato no permitido. Use PNG, JPG, GIF, WebP o SVG.'
    safe_name = f'{prefix}_{uuid.uuid4().hex[:12]}{ext}'
    path = os.path.join(certificates_upload_dir(), safe_name)
    file_storage.save(path)
    return f'/static/uploads/certificates/{safe_name}', None
