"""PDF programa académico (diplomados): almacenamiento admin y URL pública estable para landings externos."""

from __future__ import annotations

import os
from datetime import datetime

from flask import current_app, has_request_context, redirect, send_file, url_for

DEFAULT_ACADEMIC_PROGRAM_PDF_TITLE = 'Descargar Programa Académico'


def is_diplomado_program(program) -> bool:
    pt = (getattr(program, 'program_type', None) or '').strip().lower()
    if pt == 'diplomado':
        return True
    cat = (getattr(program, 'category', None) or '').strip().lower()
    return cat in ('diplomado', 'diplomados') or cat.startswith('diplomado')


def program_has_public_academic_pdf(program) -> bool:
    if not is_diplomado_program(program):
        return False
    if not bool(getattr(program, 'show_academic_program_pdf', False)):
        return False
    return bool((getattr(program, 'academic_program_pdf_url', None) or '').strip())


def academic_program_pdf_button_label(program) -> str:
    t = (getattr(program, 'academic_program_pdf_title', None) or '').strip()
    return t or DEFAULT_ACADEMIC_PROGRAM_PDF_TITLE


def public_academic_program_pdf_path(slug: str) -> str:
    """Ruta estable por slug (no cambia al reemplazar el archivo en admin)."""
    return url_for('academic_program_public_pdf', slug=(slug or '').strip().lower())


def public_academic_program_pdf_url(slug: str, *, external: bool = True) -> str:
    slug_norm = (slug or '').strip().lower()
    if not slug_norm:
        return ''
    if has_request_context():
        try:
            return url_for('academic_program_public_pdf', slug=slug_norm, _external=external)
        except RuntimeError:
            pass
    return public_academic_program_pdf_path(slug_norm)


def find_program_for_public_pdf(slug: str, organization_id: int | None):
    from models.academic_program import AcademicProgram

    slug = (slug or '').strip().lower()
    if not slug:
        return None
    q = AcademicProgram.query.filter_by(slug=slug, status='published')
    if organization_id is not None:
        q = q.filter_by(organization_id=int(organization_id))
    rows = q.order_by(AcademicProgram.id.asc()).all()
    if not rows:
        return None
    if organization_id is not None:
        return rows[0]
    if len(rows) == 1:
        return rows[0]
    return rows[0]


def serve_academic_program_pdf(program):
    """Sirve el PDF público (inline). Sin login ni compra."""
    if not program_has_public_academic_pdf(program):
        return None
    stored = (program.academic_program_pdf_url or '').strip()
    if stored.startswith('http://') or stored.startswith('https://'):
        return redirect(stored, code=302)

    rel = stored.lstrip('/')
    if not rel.startswith('static/uploads/academic_programs/'):
        current_app.logger.warning('[academic_pdf] ruta no permitida program_id=%s', program.id)
        return None
    fs = os.path.normpath(os.path.join(current_app.root_path, '..', rel))
    uploads_root = os.path.normpath(
        os.path.join(current_app.root_path, '..', 'static', 'uploads', 'academic_programs')
    )
    if not fs.startswith(uploads_root) or not os.path.isfile(fs):
        current_app.logger.warning('[academic_pdf] archivo ausente program_id=%s path=%s', program.id, fs)
        return None

    download_name = (program.academic_program_pdf_filename or '').strip() or 'programa-academico.pdf'
    if not download_name.lower().endswith('.pdf'):
        download_name = f'{download_name}.pdf'

    return send_file(
        fs,
        mimetype='application/pdf',
        as_attachment=False,
        download_name=download_name,
        max_age=3600,
    )


def touch_academic_pdf_upload_metadata(program, *, original_filename: str | None = None) -> None:
    program.academic_program_pdf_uploaded_at = datetime.utcnow()
    if original_filename:
        program.academic_program_pdf_filename = original_filename


def _stored_pdf_filesystem_path(stored: str) -> str | None:
    p = (stored or '').strip()
    if not p or p.startswith('http://') or p.startswith('https://'):
        return None
    rel = p.lstrip('/')
    if not rel.startswith('static/uploads/academic_programs/'):
        return None
    try:
        fs = os.path.normpath(os.path.join(current_app.root_path, '..', rel))
        uploads_root = os.path.normpath(
            os.path.join(current_app.root_path, '..', 'static', 'uploads', 'academic_programs')
        )
        if fs.startswith(uploads_root) and os.path.isfile(fs):
            return fs
    except Exception:
        pass
    return None


def academic_program_pdf_admin_status(program) -> dict:
    """Estado para la ficha admin (badge, enlaces, avisos)."""
    stored = (getattr(program, 'academic_program_pdf_url', None) or '').strip()
    file_ok = bool(_stored_pdf_filesystem_path(stored)) if stored else False
    if stored.startswith('http://') or stored.startswith('https://'):
        file_ok = True
    is_active = bool(getattr(program, 'show_academic_program_pdf', False))
    has_stored = bool(stored)
    ready = program_has_public_academic_pdf(program) and file_ok
    slug = (getattr(program, 'slug', None) or '').strip().lower()
    public_url = public_academic_program_pdf_url(slug) if slug else ''
    if not has_stored:
        state = 'missing'
        label = 'Sin PDF'
        badge = 'danger'
    elif not file_ok:
        state = 'broken'
        label = 'PDF en BD pero archivo no encontrado'
        badge = 'warning'
    elif not is_active:
        state = 'inactive'
        label = 'PDF cargado — inactivo (marcá «PDF activo»)'
        badge = 'warning'
    else:
        state = 'ready'
        label = 'PDF listo para el landing'
        badge = 'success'
    return {
        'state': state,
        'label': label,
        'badge': badge,
        'has_stored': has_stored,
        'file_ok': file_ok,
        'is_active': is_active,
        'ready': ready,
        'public_url': public_url,
        'view_url': public_url if ready else (stored if file_ok and has_stored else ''),
    }
