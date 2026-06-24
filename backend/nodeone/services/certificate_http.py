"""URLs base y rutas de upload compartidas por certificados (membresía y eventos)."""

from __future__ import annotations

import os


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
