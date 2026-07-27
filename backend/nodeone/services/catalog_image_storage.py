"""Imágenes del catálogo Ventas → Productos (Service.image_url)."""

from __future__ import annotations

import os
import uuid

_ALLOWED_EXT = frozenset({'.png', '.jpg', '.jpeg', '.gif', '.webp'})
_MAX_BYTES = 3 * 1024 * 1024  # 3 MB


def catalog_products_upload_dir() -> str:
    """`static/uploads/catalog/products` (preferir static_folder de Flask)."""
    path = None
    try:
        from flask import current_app, has_app_context

        if has_app_context() and getattr(current_app, 'static_folder', None):
            path = os.path.join(current_app.static_folder, 'uploads', 'catalog', 'products')
    except Exception:
        path = None
    if not path:
        app_root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        path = os.path.join(app_root, 'static', 'uploads', 'catalog', 'products')
    os.makedirs(path, exist_ok=True)
    try:
        os.chmod(path, 0o2775)
    except OSError:
        pass
    return path


def save_catalog_product_image(file_storage, *, organization_id: int) -> tuple[str | None, str | None]:
    """
    Guarda imagen de ítem de catálogo (Producto).
    Retorna (url pública `/static/uploads/catalog/products/...`, mensaje_error).
    """
    if not file_storage or not getattr(file_storage, 'filename', None):
        return None, None
    filename = (file_storage.filename or '').strip()
    if not filename:
        return None, None
    ext = (os.path.splitext(filename)[1] or '').lower()
    if ext not in _ALLOWED_EXT:
        return None, 'Formato no permitido. Usá PNG, JPG, GIF o WebP.'

    try:
        file_storage.stream.seek(0, os.SEEK_END)
        size = int(file_storage.stream.tell() or 0)
        file_storage.stream.seek(0)
        if size > _MAX_BYTES:
            return None, 'La imagen supera 3 MB.'
    except Exception:
        pass

    oid = int(organization_id)
    safe_name = f'o{oid}_{uuid.uuid4().hex[:12]}{ext}'
    path = os.path.join(catalog_products_upload_dir(), safe_name)
    try:
        file_storage.save(path)
    except OSError:
        return None, 'No se pudo guardar la imagen. Revisá permisos de uploads.'
    return f'/static/uploads/catalog/products/{safe_name}', None
