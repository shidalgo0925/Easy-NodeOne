"""Admin HTML: convocatorias (cohortes) para servicios tipo COURSE."""

from __future__ import annotations


def register_admin_course_cohort_routes(app):
    from datetime import date, datetime

    from flask import abort, flash, redirect, render_template, request, url_for

    import app as M

    from utils.organization import get_admin_effective_organization_id

    def _oid():
        return int(get_admin_effective_organization_id())

    def _load_course_service(service_id: int):
        s = M.Service.query.filter_by(id=int(service_id), organization_id=_oid()).first()
        if not s or (getattr(s, 'service_type', None) or '').strip().upper() != 'COURSE':
            return None
        return s

    @app.route('/admin/services/<int:service_id>/cohorts')
    @M.require_permission('services.view')
    def admin_course_cohort_list(service_id):
        svc = _load_course_service(service_id)
        if svc is None:
            flash('Servicio no encontrado o no es un programa (COURSE).', 'error')
            return redirect(url_for('admin_services_catalog.admin_services'))
        rows = (
            M.CourseCohort.query.filter_by(organization_id=_oid(), service_id=svc.id)
            .order_by(M.CourseCohort.display_order, M.CourseCohort.start_date, M.CourseCohort.id)
            .all()
        )
        slug = (getattr(svc, 'program_slug', None) or '').strip()
        api_hint = f'/api/public/programs/{slug}/cohorts' if slug else ''
        return render_template(
            'admin/course_cohorts/list.html',
            service=svc,
            cohorts=rows,
            public_api_path=api_hint,
        )

    @app.route('/admin/services/<int:service_id>/cohorts/new', methods=['GET', 'POST'])
    @M.require_permission('services.view')
    def admin_course_cohort_new(service_id):
        svc = _load_course_service(service_id)
        if svc is None:
            flash('Servicio no encontrado o no es un programa (COURSE).', 'error')
            return redirect(url_for('admin_services_catalog.admin_services'))
        if request.method == 'POST':
            return _cohort_save(M, svc, None)
        return render_template('admin/course_cohorts/form.html', service=svc, cohort=None)

    @app.route('/admin/course-cohorts/<int:cohort_id>/edit', methods=['GET', 'POST'])
    @M.require_permission('services.view')
    def admin_course_cohort_edit(cohort_id):
        ch = M.CourseCohort.query.filter_by(id=int(cohort_id), organization_id=_oid()).first()
        if ch is None:
            abort(404)
        svc = _load_course_service(ch.service_id)
        if svc is None:
            flash('Servicio asociado no válido.', 'error')
            return redirect(url_for('admin_services_catalog.admin_services'))
        if request.method == 'POST':
            return _cohort_save(M, svc, ch)
        return render_template('admin/course_cohorts/form.html', service=svc, cohort=ch)

    @app.route('/admin/course-cohorts/<int:cohort_id>/delete', methods=['POST'])
    @M.require_permission('services.view')
    def admin_course_cohort_delete(cohort_id):
        ch = M.CourseCohort.query.filter_by(id=int(cohort_id), organization_id=_oid()).first()
        if ch is None:
            abort(404)
        sid = int(ch.service_id)
        M.db.session.delete(ch)
        M.db.session.commit()
        flash('Convocatoria eliminada.', 'success')
        return redirect(url_for('admin_course_cohort_list', service_id=sid))

    def _parse_date(raw):
        raw = (raw or '').strip()
        if not raw:
            return None
        try:
            return datetime.strptime(raw, '%Y-%m-%d').date()
        except ValueError:
            return None

    def _cohort_save(M, svc, existing):
        label = (request.form.get('label') or '').strip() or None
        cslug = (request.form.get('slug') or '').strip() or None
        modality = (request.form.get('modality') or 'virtual').strip().lower()
        if modality not in ('virtual', 'hybrid', 'presential'):
            modality = 'virtual'
        start_d = _parse_date(request.form.get('start_date'))
        end_d = _parse_date(request.form.get('end_date'))
        try:
            weeks = int(request.form.get('weeks_duration') or 0)
        except ValueError:
            weeks = 0
        weeks = weeks if weeks > 0 else None
        try:
            cap = int(request.form.get('capacity_total') or 0)
        except ValueError:
            cap = 0
        cap = max(0, cap)
        try:
            reserved = int(request.form.get('capacity_reserved') or 0)
        except ValueError:
            reserved = 0
        reserved = max(0, reserved)
        if cap > 0 and reserved > cap:
            flash('Los cupos reservados no pueden superar el total.', 'error')
            return render_template(
                'admin/course_cohorts/form.html',
                service=svc,
                cohort=existing,
                form=request.form,
            )
        price_raw = (request.form.get('price_override') or '').strip()
        price_cents = None
        if price_raw:
            try:
                price_cents = int(round(float(price_raw.replace(',', '.')) * 100))
            except ValueError:
                flash('Precio override no válido.', 'error')
                return render_template(
                    'admin/course_cohorts/form.html',
                    service=svc,
                    cohort=existing,
                    form=request.form,
                )
        try:
            disp = int(request.form.get('display_order') or 0)
        except ValueError:
            disp = 0
        is_active = request.form.get('is_active') == '1'

        if existing is None:
            row = M.CourseCohort(
                organization_id=_oid(),
                service_id=int(svc.id),
                slug=cslug,
                label=label,
                start_date=start_d,
                end_date=end_d,
                weeks_duration=weeks,
                modality=modality,
                capacity_total=cap,
                capacity_reserved=reserved,
                price_override_cents=price_cents,
                is_active=is_active,
                display_order=disp,
            )
            M.db.session.add(row)
            flash('Convocatoria creada.', 'success')
        else:
            existing.slug = cslug
            existing.label = label
            existing.start_date = start_d
            existing.end_date = end_d
            existing.weeks_duration = weeks
            existing.modality = modality
            existing.capacity_total = cap
            existing.capacity_reserved = reserved
            existing.price_override_cents = price_cents
            existing.is_active = is_active
            existing.display_order = disp
            flash('Convocatoria actualizada.', 'success')
        try:
            M.db.session.commit()
        except Exception as e:
            M.db.session.rollback()
            flash(f'No se pudo guardar: {e}', 'error')
            return render_template(
                'admin/course_cohorts/form.html',
                service=svc,
                cohort=existing,
                form=request.form,
            )
        return redirect(url_for('admin_course_cohort_list', service_id=svc.id))
