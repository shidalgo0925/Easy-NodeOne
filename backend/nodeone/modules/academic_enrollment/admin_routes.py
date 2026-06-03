"""Admin: programas académicos de inscripción pública (CRUD + planes)."""
from __future__ import annotations

import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app import admin_required, admin_data_scope_organization_id, db, default_organization_id

academic_enrollment_admin_bp = Blueprint(
    'academic_enrollment_admin', __name__, url_prefix='/admin/academic-enrollment'
)

_SLUG_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
_PROGRAM_TYPES = ('curso', 'diplomado', 'taller', 'certificacion', 'servicio', 'programa')
_STATUSES = ('draft', 'published', 'archived')


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


def _program_for_scope(program_id: int):
    from models.academic_program import AcademicProgram

    oid = _scope_org_id()
    return AcademicProgram.query.filter_by(id=int(program_id), organization_id=oid).first_or_404()


@academic_enrollment_admin_bp.route('/programs')
@login_required
@admin_required
def list_programs():
    from models.academic_program import AcademicProgram

    oid = _scope_org_id()
    programs = (
        AcademicProgram.query.filter_by(organization_id=oid)
        .order_by(AcademicProgram.name)
        .all()
    )
    return render_template('admin/academic_programs_list.html', programs=programs, organization_id=oid)


@academic_enrollment_admin_bp.route('/programs/new', methods=['GET', 'POST'])
@login_required
@admin_required
def program_new():
    from models.academic_program import AcademicProgram

    oid = _scope_org_id()
    if request.method == 'POST':
        err = _save_program_from_form(None, oid)
        if err:
            flash(err, 'error')
            return render_template(
                'admin/academic_program_form.html',
                program=None,
                form=request.form,
                organization_id=oid,
                program_types=_PROGRAM_TYPES,
                statuses=_STATUSES,
            )
        flash('Programa creado.', 'success')
        return redirect(url_for('academic_enrollment_admin.list_programs'))
    return render_template(
        'admin/academic_program_form.html',
        program=None,
        form=None,
        organization_id=oid,
        program_types=_PROGRAM_TYPES,
        statuses=_STATUSES,
    )


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
        err = _save_program_from_form(program, oid)
        if err:
            flash(err, 'error')
            return render_template(
                'admin/academic_program_form.html',
                program=program,
                form=request.form,
                organization_id=oid,
                program_types=_PROGRAM_TYPES,
                statuses=_STATUSES,
                plans=program.pricing_plans.order_by('sort_order', 'id').all(),
            )
        flash('Programa actualizado.', 'success')
        return redirect(url_for('academic_enrollment_admin.program_edit', program_id=program.id))
    plans = program.pricing_plans.order_by('sort_order', 'id').all()
    return render_template(
        'admin/academic_program_form.html',
        program=program,
        form=None,
        organization_id=oid,
        program_types=_PROGRAM_TYPES,
        statuses=_STATUSES,
        plans=plans,
    )


def _save_program_from_form(existing, organization_id: int) -> str | None:
    from models.academic_program import AcademicProgram

    name = (request.form.get('name') or '').strip()
    slug = _normalize_slug(request.form.get('slug') or '')
    program_type = (request.form.get('program_type') or 'diplomado').strip().lower()
    status = (request.form.get('status') or 'draft').strip().lower()

    if not name:
        return 'El nombre es obligatorio.'
    if not slug:
        return 'Slug inválido: solo minúsculas, números y guiones (ej. neuro-liderazgo).'
    if program_type not in _PROGRAM_TYPES:
        return 'Tipo de programa no válido.'
    if status not in _STATUSES:
        return 'Estado no válido.'

    other = AcademicProgram.query.filter_by(organization_id=organization_id, slug=slug).first()
    if other is not None and (existing is None or other.id != existing.id):
        return f'Ya existe un programa con slug «{slug}» en esta organización.'

    price_from = None
    pf_raw = (request.form.get('price_from') or '').strip()
    if pf_raw:
        try:
            price_from = float(pf_raw.replace(',', '.'))
        except ValueError:
            return 'Precio «desde» no válido.'

    fields = dict(
        name=name,
        slug=slug,
        program_type=program_type,
        status=status,
        category=(request.form.get('category') or '').strip() or None,
        modality=(request.form.get('modality') or '').strip() or None,
        duration_text=(request.form.get('duration_text') or '').strip() or None,
        hours=(request.form.get('hours') or '').strip() or None,
        language=(request.form.get('language') or '').strip() or None,
        currency=(request.form.get('currency') or 'USD').strip().upper()[:8] or 'USD',
        price_from=price_from,
        short_description=(request.form.get('short_description') or '').strip() or None,
        long_description=(request.form.get('long_description') or '').strip() or None,
    )

    if existing is None:
        row = AcademicProgram(organization_id=organization_id, **fields)
        db.session.add(row)
    else:
        for k, v in fields.items():
            setattr(existing, k, v)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return str(e)
    return None


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
