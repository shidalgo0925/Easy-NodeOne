"""Media pública de AcademicProgram — single source of truth (sin overrides por slug).

Uso oficial (documentado):
  - Catálogo ``/programas``     → campo ``image_url`` (admin slot ②, kind ``image``)
  - Inscripción ``/inscripcion`` → campo ``flyer_url`` (admin slot ③, kind ``flyer``)
  - WordPress ``/diplomados/``  → ``image_wp_landing`` (slot ①); no se usa en vitrina Apps

No hay fallback entre ``image_url`` y ``flyer_url`` en vistas públicas.
Programas ``published`` deben tener ambos valores válidos (validación en admin).
"""

from __future__ import annotations

import os
import urllib.error
import urllib.request

from flask import current_app

from nodeone.modules.academic_enrollment.uploads import absolute_public_asset_url

# --- Single source of truth (nombres de columna ORM) ---
CATALOG_IMAGE_FIELD = 'image_url'
ENROLLMENT_MEDIA_FIELD = 'flyer_url'


def catalog_media_path(program) -> str | None:
    """Ruta/URL almacenada para tarjeta de catálogo."""
    raw = (getattr(program, CATALOG_IMAGE_FIELD, None) or '').strip()
    return raw or None


def enrollment_media_path(program) -> str | None:
    """Ruta/URL almacenada para hero de inscripción."""
    raw = (getattr(program, ENROLLMENT_MEDIA_FIELD, None) or '').strip()
    return raw or None


def enrollment_media_is_pdf(media_src: str | None) -> bool:
    return bool(media_src and '.pdf' in media_src.lower())


def resolve_catalog_card_image_absolute(program, *, external_base: str | None = None) -> str | None:
    return absolute_public_asset_url(catalog_media_path(program), external_base=external_base)


def resolve_enrollment_media_absolute(program, *, external_base: str | None = None) -> str | None:
    return absolute_public_asset_url(enrollment_media_path(program), external_base=external_base)


def _filesystem_path_for_stored(stored: str) -> str | None:
    p = (stored or '').strip()
    if not p or p.startswith(('http://', 'https://', '//')):
        return None
    rel = p.lstrip('/')
    if not rel.startswith('static/uploads/'):
        return None
    return os.path.normpath(os.path.join(current_app.root_path, '..', rel))


def media_stored_path_exists(stored: str | None) -> bool | None:
    """
    True si el archivo local existe; True si URL remota responde HEAD 200;
    None si stored vacío; False si local falta o remota falla.
    """
    p = (stored or '').strip()
    if not p:
        return None
    fs = _filesystem_path_for_stored(p)
    if fs is not None:
        return os.path.isfile(fs)
    if p.startswith(('http://', 'https://')):
        try:
            req = urllib.request.Request(p, method='HEAD', headers={'User-Agent': 'NodeOne/1.0 (media-audit)'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return 200 <= int(resp.status) < 400
        except urllib.error.HTTPError as e:
            return 200 <= int(e.code) < 400
        except Exception:
            return False
    return False


def validate_published_program_media(program) -> str | None:
    """Error humano si ``published`` sin media válida en ambos slots oficiales."""
    if (getattr(program, 'status', None) or '').strip().lower() != 'published':
        return None
    cat = catalog_media_path(program)
    if not cat:
        return (
            'No se puede publicar: falta imagen de catálogo (campo image_url, slot ②). '
            'Subí archivo o pegá URL antes de publicar.'
        )
    if media_stored_path_exists(cat) is False:
        return f'No se puede publicar: image_url no accesible ({cat}).'
    enr = enrollment_media_path(program)
    if not enr:
        return (
            'No se puede publicar: falta imagen de inscripción (campo flyer_url, slot ③). '
            'Subí archivo o pegá URL antes de publicar.'
        )
    if media_stored_path_exists(enr) is False:
        return f'No se puede publicar: flyer_url no accesible ({enr}).'
    return None


def audit_program_media_row(program) -> dict:
    """Fila para scripts de auditoría."""
    cat = catalog_media_path(program)
    enr = enrollment_media_path(program)
    cat_ok = media_stored_path_exists(cat)
    enr_ok = media_stored_path_exists(enr)
    status = (getattr(program, 'status', None) or '').strip().lower()
    if status != 'published':
        overall = 'draft_or_archived'
    elif cat and enr and cat_ok is not False and enr_ok is not False:
        overall = 'ok'
    elif not cat or not enr:
        overall = 'missing_field'
    else:
        overall = 'broken_url'
    return {
        'slug': (getattr(program, 'slug', None) or '').strip(),
        'published': status == 'published',
        'status': status,
        'image_url': cat,
        'flyer_url': enr,
        'catalog_file_exists': cat_ok,
        'enrollment_file_exists': enr_ok,
        'audit_status': overall,
    }
