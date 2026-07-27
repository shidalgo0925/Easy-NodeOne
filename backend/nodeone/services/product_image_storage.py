"""Almacenamiento de imágenes de producto EPosOne (sin deps nuevas)."""

from __future__ import annotations

import os
import uuid

_ALLOWED_EXT = frozenset({'.png', '.jpg', '.jpeg', '.gif', '.webp'})
_MAX_BYTES = 3 * 1024 * 1024  # 3 MB


def products_upload_dir() -> str:
    """`static/uploads/eposone/products` relativo al repo app."""
    # backend/nodeone/services → app/
    app_root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    path = os.path.join(app_root, 'static', 'uploads', 'eposone', 'products')
    os.makedirs(path, exist_ok=True)
    return path


def save_product_image_upload(file_storage, *, organization_id: int) -> tuple[str | None, str | None]:
    """
    Guarda imagen de producto.
    Retorna (url pública `/static/uploads/eposone/products/...`, mensaje_error).
    """
    if not file_storage or not getattr(file_storage, 'filename', None):
        return None, None
    filename = (file_storage.filename or '').strip()
    if not filename:
        return None, None
    ext = (os.path.splitext(filename)[1] or '').lower()
    if ext not in _ALLOWED_EXT:
        return None, 'Formato no permitido. Usá PNG, JPG, GIF o WebP.'

    # Tamaño si el stream lo permite
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
    path = os.path.join(products_upload_dir(), safe_name)
    try:
        file_storage.save(path)
    except OSError:
        return None, 'No se pudo guardar la imagen en el servidor. Revisá permisos de uploads.'
    return f'/static/uploads/eposone/products/{safe_name}', None


def resolve_product_image_url(
    *,
    organization_id: int,
    file_storage=None,
    image_url_form: str | None = None,
    clear_image: bool = False,
    existing_url: str | None = None,
) -> tuple[str | None, str | None]:
    """
    Prioridad: archivo subido > URL pegada > limpiar > conservar existente.
    Retorna (image_url | None, error | None).
    """
    if clear_image:
        return None, None
    uploaded, err = save_product_image_upload(file_storage, organization_id=organization_id)
    if err:
        return None, err
    if uploaded:
        return uploaded, None
    url = (image_url_form or '').strip() or None
    if url:
        return url[:500], None
    return existing_url, None
