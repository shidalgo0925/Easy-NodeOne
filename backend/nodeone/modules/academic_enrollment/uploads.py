"""Subida de imagen/flyer de programas de inscripción → /static/uploads/academic_programs/."""

from __future__ import annotations

import os
import secrets
from flask import current_app
from werkzeug.utils import secure_filename

IMAGE_EXTENSIONS = frozenset({'png', 'jpg', 'jpeg', 'gif', 'webp'})
FLYER_EXTENSIONS = IMAGE_EXTENSIONS | frozenset({'pdf'})
PDF_ONLY_EXTENSIONS = frozenset({'pdf'})
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_FLYER_BYTES = 10 * 1024 * 1024
MAX_ACADEMIC_PROGRAM_PDF_BYTES = 25 * 1024 * 1024
RESOURCE_EXTENSIONS = frozenset(
    {'pdf', 'jpg', 'jpeg', 'png', 'webp', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'}
)
MAX_RESOURCE_BYTES = 25 * 1024 * 1024


def _uploads_dir(organization_id: int) -> str:
    root = os.path.normpath(
        os.path.join(current_app.root_path, '..', 'static', 'uploads', 'academic_programs', str(int(organization_id)))
    )
    os.makedirs(root, exist_ok=True)
    return root


def _ext_allowed(filename: str, allowed: frozenset[str]) -> bool:
    if not filename or '.' not in filename:
        return False
    return filename.rsplit('.', 1)[1].lower() in allowed


def _remove_stored_if_local(path: str | None) -> None:
    p = (path or '').strip()
    if not p or p.startswith('http://') or p.startswith('https://'):
        return
    rel = p.lstrip('/')
    if not rel.startswith('static/uploads/'):
        return
    fs = os.path.normpath(os.path.join(current_app.root_path, '..', rel))
    try:
        if os.path.isfile(fs):
            os.remove(fs)
    except OSError:
        pass


def save_program_media_upload(
    organization_id: int,
    storage,
    *,
    kind: str,
    slug: str,
) -> tuple[str | None, str | None]:
    """
    Guarda archivo y devuelve (ruta pública /static/..., error).
    kind: 'image' | 'flyer' | 'wp_landing'
    """
    if not storage or not getattr(storage, 'filename', None) or not (storage.filename or '').strip():
        return None, None

    filename = secure_filename(storage.filename) or 'file'
    if kind == 'image':
        if not _ext_allowed(filename, IMAGE_EXTENSIONS):
            return None, 'Imagen: use PNG, JPG, WEBP o GIF.'
        max_bytes = MAX_IMAGE_BYTES
        prefix = 'cover'
    elif kind == 'flyer':
        if not _ext_allowed(filename, FLYER_EXTENSIONS):
            return None, 'Flyer: use imagen (PNG, JPG, WEBP) o PDF.'
        max_bytes = MAX_FLYER_BYTES
        prefix = 'flyer'
    elif kind == 'wp_landing':
        if not _ext_allowed(filename, FLYER_EXTENSIONS):
            return None, 'Landing WP: use imagen (PNG, JPG, WEBP) o PDF.'
        max_bytes = MAX_FLYER_BYTES
        prefix = 'wp_landing'
    elif kind == 'academic_pdf':
        if not _ext_allowed(filename, PDF_ONLY_EXTENSIONS):
            return None, 'Programa académico: solo PDF.'
        max_bytes = MAX_ACADEMIC_PROGRAM_PDF_BYTES
        prefix = 'program_pdf'
    elif kind == 'resource':
        if not _ext_allowed(filename, RESOURCE_EXTENSIONS):
            return None, 'Recurso: use PDF, imagen u Office (doc, ppt, xls).'
        max_bytes = MAX_RESOURCE_BYTES
        prefix = 'resource'
    else:
        return None, 'Tipo de archivo no válido.'

    ext = filename.rsplit('.', 1)[1].lower()
    slug_bit = secure_filename((slug or 'program').replace('-', '_'))[:40] or 'program'
    new_name = f'{slug_bit}_{prefix}_{secrets.token_hex(6)}.{ext}'
    dest_dir = _uploads_dir(organization_id)
    dest_path = os.path.join(dest_dir, new_name)

    try:
        storage.stream.seek(0, os.SEEK_END)
        size = storage.stream.tell()
        storage.stream.seek(0)
    except Exception:
        size = None
    if size is not None and size > max_bytes:
        mb = max_bytes // (1024 * 1024)
        return None, f'El archivo supera {mb} MB.'

    storage.save(dest_path)
    if os.path.getsize(dest_path) > max_bytes:
        try:
            os.remove(dest_path)
        except OSError:
            pass
        mb = max_bytes // (1024 * 1024)
        return None, f'El archivo supera {mb} MB.'

    public_path = f'/static/uploads/academic_programs/{int(organization_id)}/{new_name}'
    return public_path, None


def program_media_path(program, slot: str) -> str | None:
    """Ruta almacenada por uso: catalog → image_url; inscripcion → flyer_url; wp_landing aislado."""
    if slot == 'catalog':
        return (program.image_url or '').strip() or None
    if slot == 'inscripcion':
        return (program.flyer_url or '').strip() or None
    if slot == 'wp_landing':
        return (getattr(program, 'image_wp_landing', None) or '').strip() or None
    return None


def program_media_absolute(program, slot: str, *, external_base: str | None = None) -> str | None:
    return absolute_public_asset_url(program_media_path(program, slot), external_base=external_base)


def is_apps_local_media_path(path: str | None) -> bool:
    p = (path or '').strip()
    return p.startswith('/static/uploads/academic_programs/')


def import_remote_media_url(
    organization_id: int,
    slug: str,
    remote_url: str,
    *,
    kind: str = 'image',
) -> tuple[str | None, str | None]:
    """
    Descarga URL externa (p. ej. WP) y guarda en /static/uploads/academic_programs/.
    Devuelve (ruta pública /static/..., error).
    """
    import urllib.parse
    import urllib.request

    url = (remote_url or '').strip()
    if not url or not url.startswith(('http://', 'https://')):
        return None, 'URL remota no válida.'
    if 'apps.internationalinstitute.us' in url and '/static/uploads/academic_programs/' in url:
        parsed = urllib.parse.urlparse(url)
        return parsed.path, None

    slug_bit = secure_filename((slug or 'program').replace('-', '_'))[:40] or 'program'
    prefix = 'flyer' if kind == 'flyer' else 'cover'
    path_part = urllib.parse.urlparse(url).path
    ext = 'png'
    if '.' in path_part:
        ext = path_part.rsplit('.', 1)[-1].lower().split('?')[0]
        if ext not in (IMAGE_EXTENSIONS | FLYER_EXTENSIONS):
            ext = 'png'
    if kind == 'image' and ext == 'pdf':
        ext = 'png'

    dest_dir = _uploads_dir(organization_id)
    new_name = f'{slug_bit}_{prefix}.{ext}'
    dest_path = os.path.join(dest_dir, new_name)
    max_bytes = MAX_FLYER_BYTES if kind == 'flyer' else MAX_IMAGE_BYTES

    try:
        parts = urllib.parse.urlsplit(url)
        safe_path = urllib.parse.quote(parts.path, safe='/:@!$&\'()*+,;=-._~')
        url = urllib.parse.urlunsplit((parts.scheme, parts.netloc, safe_path, parts.query, parts.fragment))
        req = urllib.request.Request(url, headers={'User-Agent': 'NodeOne/1.0 (media-import)'})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        if len(data) > max_bytes:
            mb = max_bytes // (1024 * 1024)
            return None, f'El archivo supera {mb} MB.'
        with open(dest_path, 'wb') as f:
            f.write(data)
    except Exception as e:
        return None, f'No se pudo descargar: {e}'

    public_path = f'/static/uploads/academic_programs/{int(organization_id)}/{new_name}'
    return public_path, None


def absolute_public_asset_url(stored: str | None, *, external_base: str | None = None) -> str | None:
    """URL absoluta para WordPress / API (apps host)."""
    p = (stored or '').strip()
    if not p:
        return None
    if p.startswith('http://') or p.startswith('https://') or p.startswith('//'):
        return p
    if not p.startswith('/'):
        p = '/' + p
    if external_base:
        return f'{external_base.rstrip("/")}{p}'
    try:
        from flask import url_for

        return url_for('static', filename=p.lstrip('/static/'), _external=True)
    except Exception:
        return p
