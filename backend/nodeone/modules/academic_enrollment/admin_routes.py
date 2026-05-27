"""Admin: programas académicos de inscripción pública (CRUD + planes)."""
from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta

from flask import Blueprint, flash, make_response, redirect, render_template, request, url_for
from flask_login import login_required

from app import admin_required, admin_data_scope_organization_id, db, default_organization_id

academic_enrollment_admin_bp = Blueprint(
    'academic_enrollment_admin', __name__, url_prefix='/admin/academic-enrollment'
)

_SLUG_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
_PROGRAM_TYPES = ('curso', 'diplomado', 'taller', 'certificacion', 'servicio', 'programa')
_STATUSES = ('draft', 'published', 'archived')
_CTA_ACTIONS = ('scroll_pricing', 'plan_full')


def _scope_org_id() -> int:
    try:
        return int(admin_data_scope_organization_id())
    except Exception:
        return int(default_organization_id())


def _normalize_slug(raw: str) -> str | None:
    s = (raw or '').strip().lower()
    if not s or not _SLUG_RE.match(s):
        return None
    return s


def _parse_start_date(raw: str) -> datetime | None | str:
    """None si vacío; datetime si OK; str si mensaje de error."""
    s = (raw or '').strip()
    if not s:
        return None
    try:
        if 'T' in s:
            return datetime.fromisoformat(s[:16])
        return datetime.strptime(s[:10], '%Y-%m-%d')
    except ValueError:
        return 'Fecha de inicio no válida (use AAAA-MM-DD).'


def _parse_catalog_sort_order(raw: str) -> tuple[int | None, str | None]:
    s = (raw or '').strip()
    if not s:
        return 0, None
    try:
        return int(s), None
    except ValueError:
        return None, 'Orden en catálogo: número entero.'


def _program_for_scope(program_id: int):
    from models.academic_program import AcademicProgram

    oid = _scope_org_id()
    return AcademicProgram.query.filter_by(id=int(program_id), organization_id=oid).first_or_404()


def _program_form_context(program, organization_id: int, *, form=None, plans=None) -> dict:
    from nodeone.modules.academic_enrollment.catalog_public import adjacent_programs_by_id
    from nodeone.modules.academic_enrollment.wp_cursos_sync import wp_sync_target_for_slug as wp_curso_target
    from nodeone.modules.academic_enrollment.wp_diplomados_sync import is_wp_diplomado_slug
    from nodeone.modules.academic_enrollment.wp_talleres_catalog_sync import (
        wp_sync_target_for_slug as wp_talleres_target,
    )
    from nodeone.modules.academic_enrollment.wp_talleres_sync import wp_sync_target_for_slug as wp_arte_target

    nav_prev = nav_next = None
    if program is not None:
        nav_prev, nav_next = adjacent_programs_by_id(organization_id, int(program.id))
    if plans is None and program is not None:
        plans = program.pricing_plans.order_by('sort_order', 'id').all()
    wp_target = None
    if program is not None:
        if is_wp_diplomado_slug(program.slug):
            wp_target = 'diplomados'
        elif wp_talleres_target(program.slug):
            wp_target = 'talleres'
        elif wp_arte_target(program.slug):
            wp_target = 'arte'
        else:
            wp_target = wp_curso_target(program.slug)
    media_audit = None
    academic_program_pdf_public_url = None
    academic_program_pdf_status = None
    if program is not None:
        from nodeone.modules.academic_enrollment.program_display_media import audit_program_media_row
        from nodeone.modules.academic_enrollment.program_academic_pdf import (
            academic_program_pdf_admin_status,
            is_diplomado_program,
        )

        media_audit = audit_program_media_row(program)
        if is_diplomado_program(program):
            academic_program_pdf_status = academic_program_pdf_admin_status(program)
            academic_program_pdf_public_url = academic_program_pdf_status.get('public_url') or ''
    return dict(
        program=program,
        form=form,
        organization_id=organization_id,
        program_types=_PROGRAM_TYPES,
        statuses=_STATUSES,
        cta_actions=_CTA_ACTIONS,
        plans=plans or [],
        nav_prev=nav_prev,
        nav_next=nav_next,
        wp_sync_eligible=wp_target is not None,
        wp_sync_target=wp_target,
        media_audit=media_audit,
        academic_program_pdf_public_url=academic_program_pdf_public_url,
        academic_program_pdf_status=academic_program_pdf_status,
    )


@academic_enrollment_admin_bp.route('/programs/sync-wp-pull', methods=['POST'])
@login_required
@admin_required
def sync_wp_pull():
    """Importa textos e imágenes de la página WP diplomados → AcademicProgram."""
    from nodeone.modules.academic_enrollment.wp_diplomados_sync import pull_diplomados_from_wp

    try:
        n, errs = pull_diplomados_from_wp(_scope_org_id(), db)
    except Exception as e:
        flash(f'Error al importar desde WordPress: {e}', 'error')
        return redirect(url_for('academic_enrollment_admin.list_programs'))
    msg = f'Importados {n} diplomados neuro desde WordPress (/diplomados/).'
    if errs:
        msg += ' ' + ' · '.join(errs[:5])
    flash(msg, 'success' if n else 'warning')
    return redirect(url_for('academic_enrollment_admin.list_programs'))


@academic_enrollment_admin_bp.route('/programs/sync-wp-cursos-pull', methods=['POST'])
@login_required
@admin_required
def sync_wp_cursos_pull():
    """Importa tarjetas de /cursos-detalle/ (WP pág. 2006) → AcademicProgram tipo curso."""
    from nodeone.modules.academic_enrollment.wp_cursos_sync import pull_cursos_from_wp

    try:
        n, errs = pull_cursos_from_wp(_scope_org_id(), db)
    except Exception as e:
        flash(f'Error al importar cursos desde WordPress: {e}', 'error')
        return redirect(url_for('academic_enrollment_admin.list_programs'))
    msg = f'Importados {n} cursos desde WordPress (/cursos-detalle/).'
    if errs:
        msg += ' ' + ' · '.join(errs[:5])
    flash(msg, 'success' if n else 'warning')
    return redirect(url_for('academic_enrollment_admin.list_programs'))


@academic_enrollment_admin_bp.route('/programs/sync-wp-talleres-pull', methods=['POST'])
@login_required
@admin_required
def sync_wp_talleres_pull():
    """Importa 4 talleres desde WP 2233 → AcademicProgram (borrador, campos seguros)."""
    from nodeone.modules.academic_enrollment.wp_talleres_catalog_sync import pull_talleres_from_wp

    try:
        n, errs = pull_talleres_from_wp(_scope_org_id(), db)
    except Exception as e:
        flash(f'Error al importar Talleres desde WordPress: {e}', 'error')
        return redirect(url_for('academic_enrollment_admin.list_programs'))
    msg = f'Importados {n} talleres desde WordPress (fuente pág. 2233).'
    if errs:
        msg += ' ' + ' · '.join(errs[:5])
    flash(msg, 'success' if n else 'warning')
    return redirect(url_for('academic_enrollment_admin.list_programs'))


@academic_enrollment_admin_bp.route('/programs/sync-wp-arte-pull', methods=['POST'])
@login_required
@admin_required
def sync_wp_arte_pull():
    """Importa tarjetas Cursos de Arte desde /cursos-detalle/ → AcademicProgram."""
    from nodeone.modules.academic_enrollment.wp_talleres_sync import pull_arte_from_wp

    try:
        n, errs = pull_arte_from_wp(_scope_org_id(), db)
    except Exception as e:
        flash(f'Error al importar Cursos de Arte desde WordPress: {e}', 'error')
        return redirect(url_for('academic_enrollment_admin.list_programs'))
    msg = f'Importados {n} programas de Cursos de Arte desde WordPress.'
    if errs:
        msg += ' ' + ' · '.join(errs[:5])
    flash(msg, 'success' if n else 'warning')
    return redirect(url_for('academic_enrollment_admin.list_programs'))


@academic_enrollment_admin_bp.route('/programs/migrate-media-to-apps', methods=['POST'])
@login_required
@admin_required
def migrate_media_to_apps():
    """Descarga medios WP de los 4 diplomados neuro → static/apps y publica en WP."""
    import os
    import subprocess

    org = _scope_org_id()
    script = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        'scripts',
        'migrate_iius_diplomados_media_to_apps.py',
    )
    if not os.path.isfile(script):
        flash('Script migrate_iius_diplomados_media_to_apps.py no encontrado.', 'error')
        return redirect(url_for('academic_enrollment_admin.list_programs'))
    proc = subprocess.run(
        [sys.executable, script, str(org)],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(script),
        env={**os.environ, 'NODEONE_PUBLIC_BASE_URL': os.environ.get('NODEONE_PUBLIC_BASE_URL', 'https://apps.internationalinstitute.us')},
    )
    if proc.returncode != 0:
        flash(f'Migración de imágenes falló: {(proc.stderr or proc.stdout)[-500:]}', 'error')
    else:
        flash('Imágenes de diplomados copiadas a apps y publicadas en WordPress.', 'success')
    return redirect(url_for('academic_enrollment_admin.list_programs'))


@academic_enrollment_admin_bp.route('/programs/sync-wp-push', methods=['POST'])
@login_required
@admin_required
def sync_wp_push():
    """Publica en WordPress (pág. diplomados) los campos de apps."""
    from nodeone.core.db import db
    from nodeone.modules.academic_enrollment.wp_diplomados_sync import push_diplomados_to_wp

    try:
        n, errs = push_diplomados_to_wp(_scope_org_id())
    except Exception as e:
        flash(f'Error al publicar en WordPress: {e}', 'error')
        return redirect(url_for('academic_enrollment_admin.list_programs'))
    msg = f'Actualizada página WP /diplomados/ ({n} de 4 diplomados neuro).'
    if errs:
        msg += ' ' + ' · '.join(errs[:5])
    flash(msg, 'success' if n else 'warning')
    return redirect(url_for('academic_enrollment_admin.list_programs'))


@academic_enrollment_admin_bp.route('/programs')
@login_required
@admin_required
def list_programs():
    from models.academic_program import AcademicProgram
    from nodeone.modules.academic_enrollment.catalog_public import (
        apply_program_list_filters,
        distinct_program_categories,
    )

    oid = _scope_org_id()
    q = (request.args.get('q') or '').strip()
    category = (request.args.get('category') or 'all').strip()
    program_type = (request.args.get('program_type') or 'all').strip()
    status = (request.args.get('status') or 'all').strip()

    query = AcademicProgram.query.filter_by(organization_id=oid)
    query = apply_program_list_filters(
        query, q=q, category=category, program_type=program_type, status=status
    )
    programs = query.order_by(
        AcademicProgram.category.asc(),
        AcademicProgram.catalog_sort_order.asc(),
        AcademicProgram.name.asc(),
    ).all()
    total_filtered = len(programs)
    total_all = AcademicProgram.query.filter_by(organization_id=oid).count()

    from app import Event
    from nodeone.modules.events.inscripcion_bridge import EVENT_INSCRIPCION_PREFIXES
    from nodeone.modules.academic_enrollment.wp_cursos_sync import CURSO_SLUGS
    from nodeone.modules.academic_enrollment.wp_diplomados_sync import DIPLOMADO_SLUGS
    from nodeone.modules.academic_enrollment.wp_talleres_catalog_sync import WP_TALLERES_PUSH_SLUGS
    from nodeone.modules.academic_enrollment.wp_talleres_sync import WP_ARTE_PUSH_SLUGS
    from sqlalchemy import or_

    slug_filters = [Event.slug.like(f'{p}%') for p in EVENT_INSCRIPCION_PREFIXES]
    events_draft_count = Event.query.filter(or_(*slug_filters), Event.publish_status == 'draft').count()
    events_total_count = Event.query.filter(or_(*slug_filters)).count()

    return render_template(
        'admin/academic_programs_list.html',
        programs=programs,
        organization_id=oid,
        wp_diplomado_slugs=set(DIPLOMADO_SLUGS),
        wp_curso_slugs=set(CURSO_SLUGS),
        wp_arte_slugs=set(WP_ARTE_PUSH_SLUGS),
        wp_talleres_slugs=set(WP_TALLERES_PUSH_SLUGS),
        filter_q=q,
        filter_category=category,
        filter_program_type=program_type,
        filter_status=status,
        filter_categories=distinct_program_categories(oid),
        program_types=_PROGRAM_TYPES,
        statuses=_STATUSES,
        total_filtered=total_filtered,
        total_all=total_all,
        events_draft_count=events_draft_count,
        events_total_count=events_total_count,
    )


_ENROLLMENT_STATUSES = ('pending_payment', 'paid', 'confirmed', 'draft', 'cancelled')


@academic_enrollment_admin_bp.route('/enrollments')
@login_required
@admin_required
def list_enrollments():
    from models.academic_program import AcademicProgram, AcademicProgramEnrollment
    from sqlalchemy import or_
    from app import User

    oid = _scope_org_id()
    q = (request.args.get('q') or '').strip()
    status = (request.args.get('status') or 'all').strip()
    program_id = request.args.get('program_id', type=int)

    query = (
        AcademicProgramEnrollment.query.filter_by(organization_id=oid)
        .join(AcademicProgram, AcademicProgramEnrollment.program_id == AcademicProgram.id)
        .join(User, AcademicProgramEnrollment.user_id == User.id)
    )
    if status and status != 'all':
        query = query.filter(AcademicProgramEnrollment.status == status)
    if program_id:
        query = query.filter(AcademicProgramEnrollment.program_id == int(program_id))
    if q:
        like = f'%{q}%'
        query = query.filter(
            or_(
                User.email.ilike(like),
                User.first_name.ilike(like),
                User.last_name.ilike(like),
                AcademicProgram.name.ilike(like),
                AcademicProgram.slug.ilike(like),
            )
        )

    enrollments = query.order_by(AcademicProgramEnrollment.id.desc()).limit(500).all()
    programs_for_filter = (
        AcademicProgram.query.filter_by(organization_id=oid)
        .order_by(AcademicProgram.name.asc())
        .all()
    )
    total_all = AcademicProgramEnrollment.query.filter_by(organization_id=oid).count()

    from app import Event
    from nodeone.modules.events.inscripcion_bridge import EVENT_INSCRIPCION_PREFIXES, is_event_inscripcion_slug

    view = (request.args.get('view') or 'programas').strip().lower()
    if view not in ('programas', 'eventos'):
        view = 'programas'
    event_q = (request.args.get('event_q') or '').strip()
    if not event_q and view == 'eventos':
        event_q = q
    event_status = (request.args.get('event_status') or 'all').strip()

    slug_filters = [Event.slug.like(f'{p}%') for p in EVENT_INSCRIPCION_PREFIXES]
    events_query = Event.query.filter(or_(*slug_filters))
    if event_status and event_status != 'all':
        events_query = events_query.filter(Event.publish_status == event_status)
    if event_q:
        like = f'%{event_q}%'
        events_query = events_query.filter(
            or_(Event.title.ilike(like), Event.slug.ilike(like), Event.category.ilike(like))
        )
    events_for_inscripcion = events_query.order_by(Event.category.asc(), Event.title.asc()).all()

    return render_template(
        'admin/academic_program_enrollments_list.html',
        enrollments=enrollments,
        organization_id=oid,
        programs_for_filter=programs_for_filter,
        filter_q=q,
        filter_status=status,
        filter_program_id=program_id,
        enrollment_statuses=_ENROLLMENT_STATUSES,
        total_filtered=len(enrollments),
        total_all=total_all,
        events_for_inscripcion=events_for_inscripcion,
        filter_event_q=event_q,
        filter_event_status=event_status,
        event_statuses=('draft', 'published', 'archived'),
        view=view,
        is_event_inscripcion_slug=is_event_inscripcion_slug,
    )


@academic_enrollment_admin_bp.route('/programs/new', methods=['GET', 'POST'])
@login_required
@admin_required
def program_new():
    from models.academic_program import AcademicProgram

    oid = _scope_org_id()
    if request.method == 'POST':
        err, pdf_msg = _save_program_from_form(None, oid)
        if err:
            flash(err, 'error')
            return render_template(
                'admin/academic_program_form.html',
                program=None,
                form=request.form,
                organization_id=oid,
                program_types=_PROGRAM_TYPES,
                statuses=_STATUSES,
                cta_actions=_CTA_ACTIONS,
            )
        flash('Programa creado.', 'success')
        if pdf_msg:
            flash(pdf_msg, 'success')
        return redirect(url_for('academic_enrollment_admin.list_programs'))
    return render_template(
        'admin/academic_program_form.html',
        program=None,
        form=None,
        organization_id=oid,
        program_types=_PROGRAM_TYPES,
        statuses=_STATUSES,
        cta_actions=_CTA_ACTIONS,
    )


@academic_enrollment_admin_bp.route('/programs/<int:program_id>/push-wp', methods=['POST'])
@login_required
@admin_required
def program_push_wp(program_id):
    """Publica este slug en WordPress (no se hace al guardar el formulario)."""
    from nodeone.modules.academic_enrollment.wp_cursos_sync import push_curso_slug_to_wp
    from nodeone.modules.academic_enrollment.wp_diplomados_sync import (
        is_wp_diplomado_slug,
        push_program_slug_to_wp,
    )
    from nodeone.modules.academic_enrollment.wp_talleres_catalog_sync import (
        is_wp_talleres_push_slug,
        push_talleres_slug_to_wp,
    )
    from nodeone.modules.academic_enrollment.wp_talleres_sync import is_wp_arte_push_slug, push_arte_slug_to_wp

    program = _program_for_scope(program_id)
    from nodeone.core.db import db

    db.session.refresh(program)
    try:
        if is_wp_diplomado_slug(program.slug):
            ok, err = push_program_slug_to_wp(_scope_org_id(), program.slug)
            wp_page = '/diplomados/'
        elif is_wp_talleres_push_slug(program.slug):
            ok, err = push_talleres_slug_to_wp(_scope_org_id(), program.slug)
            wp_page = '/cursos-detalle/ (Talleres)'
        elif is_wp_arte_push_slug(program.slug):
            ok, err = push_arte_slug_to_wp(_scope_org_id(), program.slug)
            wp_page = '/cursos-detalle/ (Cursos de Arte)'
        else:
            ok, err = push_curso_slug_to_wp(_scope_org_id(), program.slug)
            wp_page = '/cursos-detalle/'
    except Exception as e:
        flash(f'Error al publicar en WordPress: {e}', 'error')
        return redirect(url_for('academic_enrollment_admin.program_edit', program_id=program.id))
    if ok:
        flash(
            f'WordPress {wp_page}: actualizada solo la tarjeta de «{program.slug}» '
            f'(los demás cursos de arte no se modifican). Ctrl+F5 en el sitio.',
            'success',
        )
    else:
        flash(err or 'No se pudo actualizar WordPress.', 'error')
    return redirect(url_for('academic_enrollment_admin.program_edit', program_id=program.id))


@academic_enrollment_admin_bp.route('/programs/<int:program_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def program_edit(program_id):
    program = _program_for_scope(program_id)
    oid = _scope_org_id()
    if request.method == 'POST':
        action = (request.form.get('action') or 'save_program').strip()
        if action == 'add_plan':
            err = _add_plan_from_form(program)
            if err:
                flash(err, 'error')
            else:
                flash('Plan añadido.', 'success')
            return redirect(url_for('academic_enrollment_admin.program_edit', program_id=program.id))
        if action == 'update_plan':
            err = _update_plan_from_form(program, request.form.get('plan_id', type=int))
            flash(err or 'Plan actualizado.', 'error' if err else 'success')
            return redirect(url_for('academic_enrollment_admin.program_edit', program_id=program.id))
        if action == 'toggle_plan':
            err = _toggle_plan_active(program, request.form.get('plan_id', type=int))
            flash(err or 'Estado del plan actualizado.', 'error' if err else 'success')
            return redirect(url_for('academic_enrollment_admin.program_edit', program_id=program.id))
        if action == 'delete_plan':
            err = _delete_plan(program, request.form.get('plan_id', type=int))
            flash(err or 'Plan eliminado.', 'error' if err else 'success')
            return redirect(url_for('academic_enrollment_admin.program_edit', program_id=program.id))
        if action == 'archive_program':
            err = _archive_program(program)
            flash(err or 'Programa archivado.', 'error' if err else 'success')
            return redirect(url_for('academic_enrollment_admin.list_programs'))
        if action == 'delete_program':
            err = _delete_program(program)
            if err:
                flash(err, 'error')
                return redirect(url_for('academic_enrollment_admin.program_edit', program_id=program.id))
            flash('Programa eliminado.', 'success')
            return redirect(url_for('academic_enrollment_admin.list_programs'))
        err, pdf_msg = _save_program_from_form(program, oid)
        if err:
            flash(err, 'error')
            return render_template(
                'admin/academic_program_form.html',
                **_program_form_context(program, oid, form=request.form),
            )
        flash('Programa actualizado en apps.', 'success')
        if pdf_msg:
            flash(pdf_msg, 'success')
        return redirect(url_for('academic_enrollment_admin.program_edit', program_id=program.id))
    return render_template(
        'admin/academic_program_form.html',
        **_program_form_context(program, oid),
    )


def _save_program_from_form(existing, organization_id: int) -> tuple[str | None, str | None]:
    """Devuelve (error, mensaje_opcional_pdf)."""
    from models.academic_program import AcademicProgram

    pdf_uploaded = False
    pdf_cleared = False
    name = (request.form.get('name') or '').strip()
    slug = _normalize_slug(request.form.get('slug') or '')
    program_type = (request.form.get('program_type') or 'diplomado').strip().lower()
    status = (request.form.get('status') or 'draft').strip().lower()

    if not name:
        return 'El nombre es obligatorio.', None
    if not slug:
        return 'Slug inválido: solo minúsculas, números y guiones (ej. neuro-liderazgo).', None
    if program_type not in _PROGRAM_TYPES:
        return 'Tipo de programa no válido.', None
    if status not in _STATUSES:
        return 'Estado no válido.', None

    cta_action = (request.form.get('cta_action') or 'scroll_pricing').strip().lower()
    if cta_action not in _CTA_ACTIONS:
        return 'Acción del botón no válida.', None

    sort_order, sort_err = _parse_catalog_sort_order(request.form.get('catalog_sort_order') or '')
    if sort_err:
        return sort_err, None

    start_parsed = _parse_start_date(request.form.get('start_date') or '')
    if isinstance(start_parsed, str):
        return start_parsed, None

    media_position = (request.form.get('media_position') or 'left').strip().lower()
    if media_position not in ('left', 'right'):
        return 'Posición de imagen: use «left» o «right».', None

    other = AcademicProgram.query.filter_by(organization_id=organization_id, slug=slug).first()
    if other is not None and (existing is None or other.id != existing.id):
        return f'Ya existe un programa con slug «{slug}» en esta organización.', None

    price_from = None
    pf_raw = (request.form.get('price_from') or '').strip()
    if pf_raw:
        try:
            price_from = float(pf_raw.replace(',', '.'))
        except ValueError:
            return 'Precio «desde» no válido.', None

    image_url = (request.form.get('image_url') or '').strip() or None
    flyer_url = (request.form.get('flyer_url') or '').strip() or None
    image_wp_landing = (request.form.get('image_wp_landing') or '').strip() or None
    academic_program_pdf_url = (request.form.get('academic_program_pdf_url') or '').strip() or None
    show_academic_program_pdf = request.form.get('show_academic_program_pdf') == '1'
    academic_program_pdf_title = (request.form.get('academic_program_pdf_title') or '').strip() or None
    if existing is not None:
        if not image_url:
            image_url = existing.image_url
        if not flyer_url:
            flyer_url = existing.flyer_url
        if not image_wp_landing:
            image_wp_landing = existing.image_wp_landing
        if not academic_program_pdf_url:
            academic_program_pdf_url = existing.academic_program_pdf_url

    fields = dict(
        name=name,
        slug=slug,
        program_type=program_type,
        status=status,
        category=(request.form.get('category') or '').strip() or None,
        catalog_sort_order=sort_order,
        marketing_tag=(request.form.get('marketing_tag') or '').strip() or None,
        key_focuses=(request.form.get('key_focuses') or '').strip() or None,
        ideal_for=(request.form.get('ideal_for') or '').strip() or None,
        cta_label=(request.form.get('cta_label') or '').strip() or None,
        cta_action=cta_action,
        start_date=start_parsed,
        modality=(request.form.get('modality') or '').strip() or None,
        duration_text=(request.form.get('duration_text') or '').strip() or None,
        hours=(request.form.get('hours') or '').strip() or None,
        language=(request.form.get('language') or '').strip() or None,
        currency=(request.form.get('currency') or 'USD').strip().upper()[:8] or 'USD',
        price_from=price_from,
        short_description=(request.form.get('short_description') or '').strip() or None,
        long_description=(request.form.get('long_description') or '').strip() or None,
        image_url=image_url,
        flyer_url=flyer_url,
        image_wp_landing=image_wp_landing,
        academic_program_pdf_url=academic_program_pdf_url,
        academic_program_pdf_title=academic_program_pdf_title,
        show_academic_program_pdf=show_academic_program_pdf,
        media_position=media_position,
    )

    if existing is None:
        row = AcademicProgram(organization_id=organization_id, **fields)
        db.session.add(row)
    else:
        row = existing
        for k, v in fields.items():
            setattr(row, k, v)
    db.session.flush()

    from nodeone.modules.academic_enrollment.uploads import (
        _remove_stored_if_local,
        save_program_media_upload,
    )

    if request.form.get('clear_image') == '1':
        _remove_stored_if_local(row.image_url)
        row.image_url = None
    if request.form.get('clear_flyer') == '1':
        _remove_stored_if_local(row.flyer_url)
        row.flyer_url = None
    if request.form.get('clear_wp_landing') == '1':
        _remove_stored_if_local(row.image_wp_landing)
        row.image_wp_landing = None
    if request.form.get('clear_academic_program_pdf') == '1':
        _remove_stored_if_local(row.academic_program_pdf_url)
        row.academic_program_pdf_url = None
        row.academic_program_pdf_filename = None
        row.academic_program_pdf_uploaded_at = None
        row.show_academic_program_pdf = False
        pdf_cleared = True

    img_file = request.files.get('image_file')
    path, err = save_program_media_upload(organization_id, img_file, kind='image', slug=slug)
    if err:
        db.session.rollback()
        return err, None
    if path:
        _remove_stored_if_local(row.image_url)
        row.image_url = path

    flyer_file = request.files.get('flyer_file')
    path, err = save_program_media_upload(organization_id, flyer_file, kind='flyer', slug=slug)
    if err:
        db.session.rollback()
        return err, None
    if path:
        _remove_stored_if_local(row.flyer_url)
        row.flyer_url = path

    wp_file = request.files.get('wp_landing_file')
    path, err = save_program_media_upload(organization_id, wp_file, kind='wp_landing', slug=slug)
    if err:
        db.session.rollback()
        return err, None
    if path:
        _remove_stored_if_local(row.image_wp_landing)
        row.image_wp_landing = path

    from nodeone.modules.academic_enrollment.program_academic_pdf import touch_academic_pdf_upload_metadata
    from werkzeug.utils import secure_filename

    pdf_file = request.files.get('academic_program_pdf_file')
    pdf_orig = (pdf_file.filename or '').strip() if pdf_file else ''
    path, err = save_program_media_upload(organization_id, pdf_file, kind='academic_pdf', slug=slug)
    if err:
        db.session.rollback()
        return err, None
    if path:
        _remove_stored_if_local(row.academic_program_pdf_url)
        row.academic_program_pdf_url = path
        touch_academic_pdf_upload_metadata(
            row,
            original_filename=secure_filename(pdf_orig) or None,
        )
        row.show_academic_program_pdf = True
        pdf_uploaded = True

    from nodeone.modules.academic_enrollment.program_display_media import validate_published_program_media

    media_err = validate_published_program_media(row)
    if media_err:
        db.session.rollback()
        return media_err, None

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return str(e), None

    pdf_msg = None
    if pdf_uploaded:
        pdf_msg = (
            'PDF del programa académico guardado. «PDF activo» quedó marcado. '
            'Copiá la URL de esta sección para el landing.'
        )
    elif pdf_cleared:
        pdf_msg = 'PDF del programa académico eliminado.'
    return None, pdf_msg


def _add_plan_from_form(program) -> str | None:
    from models.academic_program import AcademicProgramPricingPlan

    name = (request.form.get('plan_name') or '').strip()
    code = (request.form.get('plan_code') or '').strip().lower()
    if not name or not code:
        return 'Nombre y código del plan son obligatorios.'
    if not re.match(r'^[a-z0-9_]+$', code):
        return 'Código de plan: solo minúsculas, números y guión bajo.'

    dup = AcademicProgramPricingPlan.query.filter_by(program_id=program.id, code=code).first()
    if dup:
        return f'Ya existe el plan con código «{code}».'

    usd_raw = (request.form.get('plan_total_usd') or '').strip()
    try:
        total_cents = int(round(float(usd_raw.replace(',', '.')) * 100))
    except ValueError:
        return 'Total USD del plan no válido.'
    if total_cents <= 0:
        return 'El total del plan debe ser mayor que cero.'

    inst = None
    inst_raw = (request.form.get('plan_installment_count') or '').strip()
    if inst_raw:
        try:
            inst = int(inst_raw)
        except ValueError:
            return 'Número de cuotas no válido.'

    try:
        sort_order = int(request.form.get('plan_sort_order') or 0)
    except ValueError:
        sort_order = 0

    row = AcademicProgramPricingPlan(
        program_id=program.id,
        name=name,
        code=code,
        currency=(request.form.get('plan_currency') or program.currency or 'USD').strip().upper()[:8],
        total_amount_cents=total_cents,
        installment_count=inst,
        discount_label=(request.form.get('plan_discount_label') or '').strip() or None,
        description=(request.form.get('plan_description') or '').strip() or None,
        is_active=request.form.get('plan_is_active') == '1',
        sort_order=sort_order,
    )
    db.session.add(row)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return str(e)
    return None


def _plan_for_program(program, plan_id: int | None):
    from models.academic_program import AcademicProgramPricingPlan

    if not plan_id:
        return None, 'Plan no indicado.'
    row = AcademicProgramPricingPlan.query.filter_by(id=int(plan_id), program_id=program.id).first()
    if row is None:
        return None, 'Plan no encontrado.'
    return row, None


def _update_plan_from_form(program, plan_id: int | None) -> str | None:
    row, err = _plan_for_program(program, plan_id)
    if err:
        return err

    name = (request.form.get('plan_name') or '').strip()
    if name:
        row.name = name
    usd_raw = (request.form.get('plan_total_usd') or '').strip()
    if usd_raw:
        try:
            row.total_amount_cents = int(round(float(usd_raw.replace(',', '.')) * 100))
        except ValueError:
            return 'Total USD no válido.'
    inst_raw = (request.form.get('plan_installment_count') or '').strip()
    if inst_raw == '':
        row.installment_count = None
    elif inst_raw:
        try:
            row.installment_count = int(inst_raw)
        except ValueError:
            return 'Cuotas no válidas.'
    row.discount_label = (request.form.get('plan_discount_label') or '').strip() or None
    row.description = (request.form.get('plan_description') or '').strip() or None
    if request.form.get('plan_is_active') is not None:
        row.is_active = request.form.get('plan_is_active') == '1'
    try:
        row.sort_order = int(request.form.get('plan_sort_order') or row.sort_order or 0)
    except ValueError:
        pass
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return str(e)
    return None


def _toggle_plan_active(program, plan_id: int | None) -> str | None:
    row, err = _plan_for_program(program, plan_id)
    if err:
        return err
    row.is_active = not bool(row.is_active)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return str(e)
    return None


def _delete_plan(program, plan_id: int | None) -> str | None:
    from models.academic_program import AcademicProgramEnrollment

    row, err = _plan_for_program(program, plan_id)
    if err:
        return err
    used = AcademicProgramEnrollment.query.filter_by(pricing_plan_id=row.id).count()
    if used:
        return f'No se puede eliminar: {used} inscripción(es) usan este plan. Desactívelo en su lugar.'
    db.session.delete(row)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return str(e)
    return None


def _archive_program(program) -> str | None:
    program.status = 'archived'
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return str(e)
    return None


def _delete_program(program) -> str | None:
    from models.academic_program import AcademicProgramEnrollment

    if AcademicProgramEnrollment.query.filter_by(program_id=program.id).count():
        return 'Hay inscripciones vinculadas. Archívelo en lugar de eliminarlo.'
    from nodeone.modules.academic_enrollment.uploads import _remove_stored_if_local

    _remove_stored_if_local(program.image_url)
    _remove_stored_if_local(program.flyer_url)
    db.session.delete(program)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return str(e)
    return None


@academic_enrollment_admin_bp.route('/pdf-leads', methods=['GET'])
@login_required
@admin_required
def academic_program_pdf_leads():
    """Lista leads capturados vía landing para descargar PDF del programa (diplomados)."""
    from models.academic_program import AcademicProgram
    from models.academic_program_pdf_lead import AcademicProgramPdfLead

    oid = _scope_org_id()
    from nodeone.services.academic_program_pdf_lead_schema import ensure_academic_program_pdf_lead_schema

    ensure_academic_program_pdf_lead_schema(db, db.engine)

    program_slug = (request.args.get('program_slug') or '').strip().lower() or None
    status = (request.args.get('status') or '').strip().lower() or None
    source = (request.args.get('source') or '').strip().lower() or None
    from_date = (request.args.get('from_date') or '').strip() or None
    to_date = (request.args.get('to_date') or '').strip() or None
    fmt = (request.args.get('format') or '').strip().lower()

    def _parse_date(raw: str | None):
        if not raw:
            return None
        try:
            return datetime.strptime(raw[:10], '%Y-%m-%d')
        except ValueError:
            return None

    dt_from = _parse_date(from_date)
    dt_to = _parse_date(to_date)

    q = (
        db.session.query(AcademicProgramPdfLead, AcademicProgram)
        .join(AcademicProgram, AcademicProgramPdfLead.program_id == AcademicProgram.id)
        .filter(AcademicProgram.organization_id == oid)
    )
    if program_slug:
        q = q.filter(AcademicProgramPdfLead.program_slug == program_slug)
    if status:
        q = q.filter(AcademicProgramPdfLead.status == status)
    if source:
        q = q.filter(AcademicProgramPdfLead.source == source)
    if dt_from:
        q = q.filter(AcademicProgramPdfLead.created_at >= dt_from)
    if dt_to:
        # inclusive hasta fin de día
        q = q.filter(AcademicProgramPdfLead.created_at < (dt_to + timedelta(days=1)))

    q = q.order_by(AcademicProgramPdfLead.created_at.desc()).limit(2000)
    rows = q.all()

    if fmt == 'csv':
        import csv
        import io

        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(
            [
                'created_at_utc',
                'program_slug',
                'program_name',
                'name',
                'email',
                'phone',
                'country',
                'source',
                'status',
                'email_confirmed_at_utc',
            ]
        )
        for lead, program in rows:
            created = lead.created_at.strftime('%Y-%m-%d %H:%M') if lead.created_at else ''
            confirmed = (
                lead.email_confirmed_at.strftime('%Y-%m-%d %H:%M')
                if getattr(lead, 'email_confirmed_at', None)
                else ''
            )
            w.writerow(
                [
                    created,
                    lead.program_slug or '',
                    program.name if program else '',
                    lead.name or '',
                    lead.email or '',
                    lead.phone or '',
                    lead.country or '',
                    lead.source or '',
                    lead.status or '',
                    confirmed,
                ]
            )

        resp = make_response(buf.getvalue())
        resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
        resp.headers['Content-Disposition'] = 'attachment; filename=academic_program_pdf_leads.csv'
        return resp

    return render_template(
        'admin/academic_program_pdf_leads.html',
        rows=rows,
        program_slug=program_slug,
        status=status,
        source=source,
        from_date=from_date,
        to_date=to_date,
    )
