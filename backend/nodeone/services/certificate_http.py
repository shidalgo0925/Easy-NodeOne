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
            root = request.url_root.rstrip('/')
            proto = (request.headers.get('X-Forwarded-Proto') or request.scheme or '').split(',')[0].strip().lower()
            if proto == 'https' and root.startswith('http://'):
                root = 'https://' + root[len('http://'):]
            return root
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


def membership_certificates_pdf_dir(*, app=None) -> str:
    """
    PDFs de certificados de membresía (tabla ``certificate``).
    Ruta histórica: ``<repo>/instance/certificates`` (antes ``backend/certificate_routes.py``).
    """
    if app is None:
        try:
            from flask import current_app

            app = current_app
        except Exception:
            app = None
    if app is not None:
        base = os.path.dirname(app.root_path)
    else:
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        base = os.path.dirname(backend_dir)
    path = os.path.normpath(os.path.join(base, 'instance', 'certificates'))
    os.makedirs(path, exist_ok=True)
    return path + os.sep


def is_allowed_membership_certificate_pdf_path(real_path: str, *, app=None) -> bool:
    """Acepta PDF bajo instance/certificates (canónico del silo o legacy clonado en el host)."""
    if not real_path:
        return False
    try:
        norm = os.path.normpath(os.path.realpath(real_path))
    except OSError:
        return False
    canonical = membership_certificates_pdf_dir(app=app).rstrip(os.sep)
    if norm == canonical or norm.startswith(canonical + os.sep):
        return True
    marker = f'{os.sep}instance{os.sep}certificates{os.sep}'
    return (norm + os.sep).find(marker) >= 0


def resolve_membership_certificate_pdf_path(
    stored_path: str | None,
    certificate_code: str | None = None,
    *,
    app=None,
) -> str | None:
    """Resuelve ruta legible del PDF (BD, nombre por código, silos legacy en el mismo servidor)."""
    candidates: list[str] = []
    if stored_path:
        candidates.append(stored_path)
    if certificate_code:
        safe = certificate_code.replace('/', '_')
        base = membership_certificates_pdf_dir(app=app).rstrip(os.sep)
        candidates.append(os.path.join(base, f'{safe}.pdf'))
    seen: set[str] = set()
    for raw in candidates:
        if not raw or raw in seen:
            continue
        seen.add(raw)
        try:
            real = os.path.normpath(os.path.realpath(raw))
        except OSError:
            continue
        if not os.path.isfile(real):
            continue
        if is_allowed_membership_certificate_pdf_path(real, app=app):
            return real
    return None


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
