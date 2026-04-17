"""Formulario público de hoja de vida (CV) asociado a servicios catálogo service_type=CV_REGISTRATION."""

from __future__ import annotations


def register_cv_application_routes(app):
    from datetime import datetime as dt_module

    from flask import flash, redirect, render_template, request, url_for
    from sqlalchemy.orm import joinedload

    import app as M

    from utils.organization import get_admin_effective_organization_id, resolve_current_organization

    def _load_cv_service(service_id: int, organization_id: int) -> M.Service | None:
        svc = M.Service.query.filter_by(id=int(service_id), organization_id=int(organization_id)).first()
        if not svc or not svc.is_active:
            return None
        if (getattr(svc, 'service_type', None) or '').strip().upper() != 'CV_REGISTRATION':
            return None
        return svc

    @app.route('/cv/registro', methods=['GET', 'POST'])
    def cv_registro():
        oid = resolve_current_organization()
        if oid is None:
            flash('No se pudo determinar la organización.', 'error')
            return redirect(url_for('index'))

        sid_raw = (request.values.get('service') or '').strip()
        if not sid_raw.isdigit():
            flash('Enlace inválido: falta el servicio de registro.', 'error')
            return redirect(url_for('services.list'))

        service_id = int(sid_raw)
        service = _load_cv_service(service_id, oid)
        if service is None:
            flash('Este servicio no está disponible o no es un registro de CV.', 'error')
            return redirect(url_for('services.list'))

        if request.method == 'POST':
            email = (request.form.get('email') or '').strip().lower()
            email_confirm = (request.form.get('email_confirm') or '').strip().lower()
            first_name = (request.form.get('first_name') or '').strip()
            last_name = (request.form.get('last_name') or '').strip()
            phone = (request.form.get('phone') or '').strip() or None
            salutation = (request.form.get('salutation') or '').strip() or None
            gender = (request.form.get('gender') or '').strip() or None
            country_residence = (request.form.get('country_residence') or '').strip() or None
            province = (request.form.get('province') or '').strip() or None
            education_level = (request.form.get('education_level') or '').strip() or None
            other_languages = (request.form.get('other_languages') or '').strip() or None
            preferred_sector = (request.form.get('preferred_sector') or '').strip() or None
            years_experience_sector = (request.form.get('years_experience_sector') or '').strip() or None
            referral_source = (request.form.get('referral_source') or '').strip() or None
            additional_comments = (request.form.get('additional_comments') or '').strip() or None

            birth_date = None
            bd_raw = (request.form.get('birth_date') or '').strip()
            if bd_raw:
                try:
                    birth_date = dt_module.strptime(bd_raw, '%Y-%m-%d').date()
                except ValueError:
                    flash('Fecha de nacimiento inválida.', 'error')
                    return render_template(
                        'cv/register.html',
                        service=service,
                        organization_id=oid,
                        form=request.form,
                    )

            if not first_name or not last_name or not email:
                flash('Nombre, apellidos y correo son obligatorios.', 'error')
                return render_template(
                    'cv/register.html',
                    service=service,
                    organization_id=oid,
                    form=request.form,
                )
            if email != email_confirm:
                flash('Los correos electrónicos no coinciden.', 'error')
                return render_template(
                    'cv/register.html',
                    service=service,
                    organization_id=oid,
                    form=request.form,
                )
            ok, err = M.validate_email_format(email)
            if not ok:
                flash(err or 'Correo inválido.', 'error')
                return render_template(
                    'cv/register.html',
                    service=service,
                    organization_id=oid,
                    form=request.form,
                )

            row = M.CvApplication(
                organization_id=int(oid),
                service_id=int(service.id),
                salutation=salutation,
                first_name=first_name,
                last_name=last_name,
                birth_date=birth_date,
                gender=gender,
                phone=phone,
                email=email,
                country_residence=country_residence,
                province=province,
                education_level=education_level,
                other_languages=other_languages,
                preferred_sector=preferred_sector,
                years_experience_sector=years_experience_sector,
                referral_source=referral_source,
                additional_comments=additional_comments,
                status='pending',
            )
            M.db.session.add(row)
            M.db.session.commit()
            flash('Tu información fue enviada correctamente. Nos pondremos en contacto si hay coincidencia.', 'success')
            return redirect(url_for('services.list'))

        return render_template(
            'cv/register.html',
            service=service,
            organization_id=oid,
            form=None,
        )

    @app.route('/admin/cv-applications')
    @M.login_required
    @M.require_permission('services.view')
    def admin_cv_applications_list():
        oid = int(get_admin_effective_organization_id())
        rows = (
            M.CvApplication.query.options(joinedload(M.CvApplication.service))
            .filter_by(organization_id=oid)
            .order_by(M.CvApplication.created_at.desc())
            .limit(500)
            .all()
        )
        return render_template('admin/cv_applications.html', applications=rows, organization_id=oid)
