"""Formulario público de hoja de vida (CV) asociado a servicios catálogo service_type=CV_REGISTRATION."""

from __future__ import annotations

import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request

_MAX_UPLOAD_BYTES = 10 * 1024 * 1024
_PHOTO_EXT = frozenset({'jpg', 'jpeg', 'png', 'gif'})
_CV_EXT = frozenset({'pdf', 'doc', 'docx', 'rtf'})


def register_cv_application_routes(app):
    from datetime import datetime as dt_module

    from flask import abort, current_app, flash, redirect, render_template, request, send_file, url_for
    from sqlalchemy.orm import joinedload
    import app as M

    from utils.organization import get_admin_effective_organization_id, resolve_current_organization
    from utils.validators import VALID_COUNTRIES, validate_country

    from nodeone.modules.cv_applications.form_choices import (
        EDUCATION_LEVEL_CHOICES,
        NATIVE_LANGUAGE_CHOICES,
        PROFESSIONAL_STATUS_CHOICES,
        REFERRAL_CHOICES,
        SALARY_CHOICES,
        SECTOR_CHOICES,
        YEARS_EXPERIENCE_CHOICES,
    )

    def _choice_keys(choices):
        return {c[0] for c in choices if c[0]}

    def _normalize_choice(raw, choices):
        v = (raw or '').strip()
        if not v:
            return None
        if v not in _choice_keys(choices):
            return False
        return v

    def _verify_recaptcha_token(token: str) -> bool:
        secret = (os.environ.get('RECAPTCHA_SECRET_KEY') or '').strip()
        if not secret:
            return True
        if not token:
            return False
        try:
            data = urllib.parse.urlencode(
                {'secret': secret, 'response': token, 'remoteip': request.remote_addr or ''}
            ).encode()
            req = urllib.request.Request(
                'https://www.google.com/recaptcha/api/siteverify',
                data=data,
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                j = json.loads(resp.read().decode())
            return bool(j.get('success'))
        except (urllib.error.URLError, ValueError, json.JSONDecodeError):
            return False

    def _cv_upload_base_dir(org_id: int) -> str:
        return os.path.join(current_app.static_folder, 'uploads', 'cv', str(int(org_id)))

    def _save_upload(org_id: int, storage, allowed_ext: frozenset, required: bool) -> str | None:
        if storage is None or not getattr(storage, 'filename', None):
            if required:
                raise ValueError('Debes adjuntar tu curriculum en PDF, Word o RTF.')
            return None
        raw_name = storage.filename or ''
        ext = None
        if '.' in raw_name:
            ext = raw_name.rsplit('.', 1)[-1].lower()
        if not ext or ext not in allowed_ext:
            raise ValueError('Tipo de archivo no permitido para este campo.')
        storage.seek(0, os.SEEK_END)
        size = storage.tell()
        storage.seek(0)
        if size > _MAX_UPLOAD_BYTES:
            raise ValueError('El archivo supera el tamaño máximo permitido (10 MB).')
        if size == 0:
            raise ValueError('El archivo está vacío.')
        fname = f'{secrets.token_hex(16)}.{ext}'
        dest_dir = _cv_upload_base_dir(org_id)
        os.makedirs(dest_dir, exist_ok=True)
        abs_path = os.path.join(dest_dir, fname)
        storage.save(abs_path)
        return f'uploads/cv/{int(org_id)}/{fname}'

    def _unlink_upload(relative: str | None) -> None:
        if not relative:
            return
        full = os.path.join(current_app.static_folder, relative.replace('/', os.sep))
        try:
            if os.path.isfile(full):
                os.remove(full)
        except OSError:
            pass

    def _load_cv_service(service_id: int, organization_id: int) -> M.Service | None:
        svc = M.Service.query.filter_by(id=int(service_id), organization_id=int(organization_id)).first()
        if not svc or not svc.is_active:
            return None
        if (getattr(svc, 'service_type', None) or '').strip().upper() != 'CV_REGISTRATION':
            return None
        return svc

    def _form_template_kwargs(service, oid, form):
        return {
            'service': service,
            'organization_id': oid,
            'form': form,
            'valid_countries': VALID_COUNTRIES,
            'salary_choices': SALARY_CHOICES,
            'professional_status_choices': PROFESSIONAL_STATUS_CHOICES,
            'native_language_choices': NATIVE_LANGUAGE_CHOICES,
            'sector_choices': SECTOR_CHOICES,
            'years_experience_choices': YEARS_EXPERIENCE_CHOICES,
            'referral_choices': REFERRAL_CHOICES,
            'education_choices': EDUCATION_LEVEL_CHOICES,
            'recaptcha_site_key': (os.environ.get('RECAPTCHA_SITE_KEY') or '').strip(),
        }

    def _admin_label_maps():
        def d(ch):
            return {k: v for k, v in ch}

        return {
            'salary': d(SALARY_CHOICES),
            'professional': d(PROFESSIONAL_STATUS_CHOICES),
            'native_lang': d(NATIVE_LANGUAGE_CHOICES),
            'sector': d(SECTOR_CHOICES),
            'years': d(YEARS_EXPERIENCE_CHOICES),
            'referral': d(REFERRAL_CHOICES),
            'education': d(EDUCATION_LEVEL_CHOICES),
        }

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
            honeypot = (request.form.get('website') or '').strip()
            if honeypot:
                flash('No se pudo enviar el formulario.', 'error')
                return render_template('cv/register.html', **_form_template_kwargs(service, oid, request.form))

            if (os.environ.get('RECAPTCHA_SECRET_KEY') or '').strip():
                tok = (request.form.get('g-recaptcha-response') or '').strip()
                if not _verify_recaptcha_token(tok):
                    flash('Verifica el captcha e inténtalo de nuevo.', 'error')
                    return render_template('cv/register.html', **_form_template_kwargs(service, oid, request.form))

            legal = request.form.get('legal_accept')
            if legal not in ('1', 'on', 'yes', 'true'):
                flash('Debes aceptar las condiciones y la política de privacidad para continuar.', 'error')
                return render_template('cv/register.html', **_form_template_kwargs(service, oid, request.form))

            email = (request.form.get('email') or '').strip().lower()
            email_confirm = (request.form.get('email_confirm') or '').strip().lower()
            first_name = (request.form.get('first_name') or '').strip()
            last_name = (request.form.get('last_name') or '').strip()
            phone = (request.form.get('phone') or '').strip() or None
            salutation = (request.form.get('salutation') or '').strip() or None
            gender = (request.form.get('gender') or '').strip() or None
            country_residence = (request.form.get('country_residence') or '').strip() or None
            province = (request.form.get('province') or '').strip() or None
            other_languages = (request.form.get('other_languages') or '').strip() or None
            additional_comments = (request.form.get('additional_comments') or '').strip() or None

            ds = _normalize_choice(request.form.get('desired_salary'), SALARY_CHOICES)
            ps = _normalize_choice(request.form.get('professional_status'), PROFESSIONAL_STATUS_CHOICES)
            nl = _normalize_choice(request.form.get('native_language'), NATIVE_LANGUAGE_CHOICES)
            sec = _normalize_choice(request.form.get('preferred_sector'), SECTOR_CHOICES)
            yx = _normalize_choice(request.form.get('years_experience_sector'), YEARS_EXPERIENCE_CHOICES)
            ref = _normalize_choice(request.form.get('referral_source'), REFERRAL_CHOICES)
            edu = _normalize_choice(request.form.get('education_level'), EDUCATION_LEVEL_CHOICES)
            if False in (ds, ps, nl, sec, yx, ref, edu):
                flash('Hay valores no válidos en el formulario. Revisa las listas desplegables.', 'error')
                return render_template('cv/register.html', **_form_template_kwargs(service, oid, request.form))

            birth_date = None
            bd_raw = (request.form.get('birth_date') or '').strip()
            if bd_raw:
                try:
                    birth_date = dt_module.strptime(bd_raw, '%Y-%m-%d').date()
                except ValueError:
                    flash('Fecha de nacimiento inválida.', 'error')
                    return render_template('cv/register.html', **_form_template_kwargs(service, oid, request.form))

            if not first_name or not last_name or not email:
                flash('Nombre, apellidos y correo son obligatorios.', 'error')
                return render_template('cv/register.html', **_form_template_kwargs(service, oid, request.form))
            if email != email_confirm:
                flash('Los correos electrónicos no coinciden.', 'error')
                return render_template('cv/register.html', **_form_template_kwargs(service, oid, request.form))
            ok, err = M.validate_email_format(email)
            if not ok:
                flash(err or 'Correo inválido.', 'error')
                return render_template('cv/register.html', **_form_template_kwargs(service, oid, request.form))

            if not country_residence:
                flash('Selecciona tu país de residencia.', 'error')
                return render_template('cv/register.html', **_form_template_kwargs(service, oid, request.form))
            cok, cerr = validate_country(country_residence)
            if not cok:
                flash(cerr or 'País no válido.', 'error')
                return render_template('cv/register.html', **_form_template_kwargs(service, oid, request.form))

            photo_rel = None
            cv_rel = None
            try:
                photo_fs = request.files.get('photo')
                cv_fs = request.files.get('cv_document')
                photo_rel = _save_upload(int(oid), photo_fs, _PHOTO_EXT, required=False)
                cv_rel = _save_upload(int(oid), cv_fs, _CV_EXT, required=True)
            except ValueError as ve:
                flash(str(ve), 'error')
                return render_template('cv/register.html', **_form_template_kwargs(service, oid, request.form))

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
                education_level=edu,
                other_languages=other_languages,
                preferred_sector=sec,
                years_experience_sector=yx,
                referral_source=ref,
                additional_comments=additional_comments,
                desired_salary=ds,
                professional_status=ps,
                native_language=nl,
                photo_relative_path=photo_rel,
                cv_document_relative_path=cv_rel,
                legal_accepted=True,
                status='pending',
            )
            try:
                M.db.session.add(row)
                M.db.session.commit()
            except Exception:
                M.db.session.rollback()
                _unlink_upload(photo_rel)
                _unlink_upload(cv_rel)
                flash('No se pudo guardar la solicitud. Inténtalo de nuevo más tarde.', 'error')
                return render_template('cv/register.html', **_form_template_kwargs(service, oid, request.form))

            flash('Tu solicitud fue enviada correctamente. Nos pondremos en contacto si hay coincidencia.', 'success')
            return redirect(url_for('services.list'))

        return render_template('cv/register.html', **_form_template_kwargs(service, oid, None))

    @app.route('/admin/cv-applications/<int:application_id>/download/<kind>')
    @M.login_required
    @M.require_permission('services.view')
    def admin_cv_application_download(application_id, kind):
        if kind not in ('photo', 'cv'):
            abort(404)
        oid = int(get_admin_effective_organization_id())
        row = M.CvApplication.query.get_or_404(application_id)
        if int(row.organization_id) != oid:
            abort(404)
        rel = row.photo_relative_path if kind == 'photo' else row.cv_document_relative_path
        if not rel:
            abort(404)
        full = os.path.join(current_app.static_folder, rel.replace('/', os.sep))
        if not os.path.isfile(full):
            abort(404)
        dl = f'{"foto" if kind == "photo" else "cv"}_{application_id}_{os.path.basename(full)}'
        return send_file(full, as_attachment=True, download_name=dl)

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
        return render_template(
            'admin/cv_applications.html',
            applications=rows,
            organization_id=oid,
            cv_labels=_admin_label_maps(),
        )
