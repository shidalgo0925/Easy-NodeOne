"""Recursos descargables por programa académico (brochure, PDF, calendario, etc.)."""

from __future__ import annotations

import os
from urllib.parse import urlparse

from flask import current_app, redirect, send_file, url_for
from flask_login import current_user

from nodeone.modules.academic_enrollment.uploads import RESOURCE_EXTENSIONS
from nodeone.services.academic_access import ACTIVE_ENROLLMENT_STATUSES

BLOCKED_URL_PREFIXES = ('javascript:', 'file:', 'data:', 'vbscript:')

RESOURCE_TYPES: tuple[tuple[str, str], ...] = (
    ('brochure', 'Brochure / folleto'),
    ('academic_program', 'Programa académico'),
    ('calendar', 'Calendario'),
    ('flyer', 'Flyer'),
    ('demo_video', 'Video demo'),
    ('external_link', 'Enlace externo'),
    ('bonus_material', 'Material bonus'),
    ('other', 'Otro'),
)

RESOURCE_TYPE_KEYS = frozenset(k for k, _ in RESOURCE_TYPES)

DEFAULT_BUTTON_LABELS: dict[str, str] = {
    'brochure': 'Descargar brochure',
    'academic_program': 'Descargar programa académico',
    'calendar': 'Descargar calendario',
    'flyer': 'Descargar flyer',
    'demo_video': 'Ver video demo',
    'external_link': 'Abrir enlace',
    'bonus_material': 'Descargar material',
    'other': 'Descargar',
}


def default_button_text(resource_type: str) -> str:
    return DEFAULT_BUTTON_LABELS.get((resource_type or '').strip().lower(), 'Descargar')


def validate_external_url(url: str) -> tuple[bool, str | None]:
    """Solo http/https; bloquea javascript:, file:, data:, etc."""
    raw = (url or '').strip()
    if not raw:
        return False, 'URL externa vacía.'
    lower = raw.lower().replace(' ', '')
    for blocked in BLOCKED_URL_PREFIXES:
        if lower.startswith(blocked):
            return False, f'Esquema de URL no permitido ({blocked.rstrip(":")}).'
    parsed = urlparse(raw)
    if parsed.scheme.lower() not in ('http', 'https'):
        return False, 'Solo se permiten URLs http o https.'
    if not parsed.netloc:
        return False, 'URL externa no válida.'
    return True, None


def validate_local_resource_path(stored: str) -> tuple[str | None, str | None]:
    """Valida ruta local bajo uploads; devuelve (ruta absoluta en disco, error)."""
    p = (stored or '').strip()
    if not p:
        return None, None
    if p.startswith(('http://', 'https://')):
        ok, err = validate_external_url(p)
        return (p if ok else None), err
    normalized = p.replace('\\', '/')
    if '..' in normalized:
        return None, 'Ruta de archivo no permitida.'
    rel = normalized.lstrip('/')
    if not rel.startswith('static/uploads/academic_programs/'):
        return None, 'Ruta de archivo no permitida.'
    fs = os.path.realpath(os.path.join(current_app.root_path, '..', rel))
    uploads_root = os.path.realpath(
        os.path.join(current_app.root_path, '..', 'static', 'uploads', 'academic_programs')
    )
    if not (fs == uploads_root or fs.startswith(uploads_root + os.sep)):
        return None, 'Ruta de archivo no permitida.'
    if not os.path.isfile(fs):
        return None, 'Archivo no encontrado en disco.'
    basename = os.path.basename(fs)
    ext = basename.rsplit('.', 1)[-1].lower() if '.' in basename else ''
    if ext not in RESOURCE_EXTENSIONS:
        return None, f'Extensión «.{ext}» no permitida.'
    return fs, None


def normalize_resource_file_url(stored: str) -> tuple[str | None, str | None]:
    """Valida y normaliza ruta pública `/static/uploads/...` para guardar en BD."""
    p = (stored or '').strip()
    if not p:
        return None, None
    if p.startswith(('http://', 'https://')):
        ok, err = validate_external_url(p)
        return (p if ok else None), err
    fs, err = validate_local_resource_path(p)
    if err or not fs:
        return None, err
    app_root = os.path.realpath(os.path.join(current_app.root_path, '..'))
    rel = os.path.relpath(fs, app_root).replace('\\', '/')
    return f'/{rel}', None


def list_active_resources_for_program(program_id: int):
    from models.academic_program import AcademicProgramResource

    return (
        AcademicProgramResource.query.filter_by(program_id=int(program_id), is_active=True)
        .order_by(AcademicProgramResource.sort_order.asc(), AcademicProgramResource.id.asc())
        .all()
    )


def list_resources_for_admin(program_id: int):
    from models.academic_program import AcademicProgramResource

    return (
        AcademicProgramResource.query.filter_by(program_id=int(program_id))
        .order_by(AcademicProgramResource.sort_order.asc(), AcademicProgramResource.id.asc())
        .all()
    )


def user_has_active_program_enrollment(user, program_id: int, organization_id: int | None = None) -> bool:
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    from models.academic_program import AcademicProgramEnrollment

    q = AcademicProgramEnrollment.query.filter(
        AcademicProgramEnrollment.user_id == int(user.id),
        AcademicProgramEnrollment.program_id == int(program_id),
        AcademicProgramEnrollment.status.in_(ACTIVE_ENROLLMENT_STATUSES),
    )
    if organization_id is not None:
        q = q.filter_by(organization_id=int(organization_id))
    return q.first() is not None


def can_access_program_resource(user, resource, program) -> bool:
    if resource is None or not getattr(resource, 'is_active', False):
        return False
    if program is None:
        return False
    if getattr(resource, 'is_public', False):
        return True
    if getattr(resource, 'requires_purchase', False):
        return user_has_active_program_enrollment(user, program.id, program.organization_id)
    if getattr(resource, 'requires_login', False):
        return user is not None and getattr(user, 'is_authenticated', False)
    return True


def resource_download_url(resource_id: int, *, external: bool = False) -> str:
    return url_for('program_resource_download', resource_id=int(resource_id), _external=external)


def landing_resource_items(resources, program, user=None) -> list[dict]:
    """Contexto para la plantilla pública de inscripción."""
    if user is None:
        user = current_user
    items: list[dict] = []
    for resource in resources:
        can_access = can_access_program_resource(user, resource, program)
        btn = (resource.button_text or '').strip() or default_button_text(resource.resource_type)
        dl_url = resource_download_url(resource.id)
        locked_login = (
            not resource.is_public
            and resource.requires_login
            and not resource.requires_purchase
            and not can_access
        )
        locked_purchase = not resource.is_public and resource.requires_purchase and not can_access
        login_url = None
        if locked_login:
            login_url = url_for('auth.login', next=dl_url)
        items.append(
            {
                'resource': resource,
                'title': resource.title,
                'description': (resource.description or '').strip() or None,
                'button_text': btn,
                'can_access': can_access,
                'locked_login': locked_login,
                'locked_purchase': locked_purchase,
                'download_url': dl_url if can_access else None,
                'login_url': login_url,
            }
        )
    return items


def find_resource_for_download(resource_id: int):
    from models.academic_program import AcademicProgram, AcademicProgramResource

    resource = AcademicProgramResource.query.get(int(resource_id))
    if resource is None or not resource.is_active:
        return None, None
    program = AcademicProgram.query.get(int(resource.program_id))
    if program is None or (program.status or '').strip().lower() != 'published':
        return None, None
    return resource, program


def serve_program_resource(resource, program):
    """Sirve archivo local, redirige URL externa o devuelve None si no hay destino."""
    if not can_access_program_resource(current_user, resource, program):
        return None, 'forbidden'

    external = (resource.external_url or '').strip()
    stored = (resource.file_url or '').strip()

    if not stored and external:
        ok, _ = validate_external_url(external)
        if ok:
            return redirect(external, code=302), None
        return None, 'invalid_external'

    if external and (resource.resource_type or '').strip().lower() in ('external_link', 'demo_video'):
        ok, _ = validate_external_url(external)
        if ok:
            return redirect(external, code=302), None
        return None, 'invalid_external'

    if not stored:
        return None, 'missing_file'

    if stored.startswith(('http://', 'https://')):
        ok, _ = validate_external_url(stored)
        if ok:
            return redirect(stored, code=302), None
        return None, 'invalid_external'

    fs, path_err = validate_local_resource_path(stored)
    if path_err or not fs:
        current_app.logger.warning(
            '[program_resource] ruta inválida id=%s err=%s', resource.id, path_err
        )
        return None, path_err or 'invalid_path'

    download_name = os.path.basename(fs)
    as_attachment = (resource.resource_type or '').strip().lower() not in (
        'demo_video',
        'external_link',
    )
    mimetype = None
    ext = download_name.rsplit('.', 1)[-1].lower() if '.' in download_name else ''
    if ext == 'pdf':
        mimetype = 'application/pdf'
        as_attachment = False
    elif ext in ('jpg', 'jpeg', 'png', 'webp', 'gif'):
        as_attachment = False

    return (
        send_file(fs, mimetype=mimetype, as_attachment=as_attachment, download_name=download_name),
        None,
    )
