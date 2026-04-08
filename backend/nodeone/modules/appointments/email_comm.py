"""Correos y fechas de citas; import diferido de `app` para evitar ciclos."""
import os
from datetime import datetime


def appointment_start_datetime_as_utc_naive(appointment):
    """
    start_datetime almacenado como naive: interpretar como UTC (defecto) o hora local del tenant.
    Env: APPOINTMENT_NAIVE_DATETIME_AS = utc | local ; APPOINTMENT_LOCAL_TIMEZONE (ej. America/Panama).
    """
    st = getattr(appointment, 'start_datetime', None)
    if st is None:
        return None
    mode = (os.environ.get('APPOINTMENT_NAIVE_DATETIME_AS') or 'utc').strip().lower()
    try:
        from zoneinfo import ZoneInfo

        utc = ZoneInfo('UTC')
        if mode == 'local':
            tzname = (os.environ.get('APPOINTMENT_LOCAL_TIMEZONE') or 'America/Panama').strip()
            loc = ZoneInfo(tzname)
            if getattr(st, 'tzinfo', None) is not None:
                return st.astimezone(utc).replace(tzinfo=None)
            return st.replace(tzinfo=loc).astimezone(utc).replace(tzinfo=None)
        if getattr(st, 'tzinfo', None) is not None:
            return st.astimezone(utc).replace(tzinfo=None)
        return st
    except Exception:
        return st.replace(tzinfo=None) if getattr(st, 'tzinfo', None) else st


def render_appointment_communication_email(
    template_key,
    appointment,
    user,
    extra_context,
    build_default_html,
    default_subject,
    strict_tenant_logo=False,
):
    """
    1) appointment_email_template (org + tipo de cita + key) si is_custom.
    2) email_template global (render_email_from_db_template).
    3) HTML por defecto (build_default_html).
    """
    from flask import current_app, render_template_string

    from app import (
        _email_preview_base_url,
        _finalize_email_subject_from_row,
        _inject_organization_email_context,
        _infra_org_id_for_runtime,
        render_email_from_db_template,
        resolve_email_logo_absolute_url,
    )
    from app import AppointmentEmailTemplate

    log = current_app.logger
    oid = int(
        getattr(appointment, 'organization_id', None)
        or getattr(user, 'organization_id', None)
        or _infra_org_id_for_runtime()
    )
    ctx = dict(extra_context or {})
    _inject_organization_email_context(ctx, oid)
    ctx.setdefault('appointment', appointment)
    ctx.setdefault('user', user)
    ctx.setdefault('base_url', _email_preview_base_url())
    if 'logo_url' not in ctx:
        ctx['logo_url'] = resolve_email_logo_absolute_url(
            organization_id=oid,
            allow_fallback_to_platform_logo=not strict_tenant_logo,
        )
    ctx.setdefault('year', datetime.now().year)
    atid = getattr(appointment, 'appointment_type_id', None)
    if atid:
        arow = AppointmentEmailTemplate.query.filter_by(
            organization_id=oid,
            appointment_type_id=int(atid),
            template_key=template_key,
        ).first()
        if arow and arow.is_custom and (arow.html_content or '').strip():
            subj = _finalize_email_subject_from_row(arow.subject, default_subject, ctx)
            try:
                html = render_template_string(arow.html_content, **ctx).strip()
                return html, subj
            except Exception as e:
                log.warning('render_appointment_communication_email override %s: %s', template_key, e)
    default_html = build_default_html()
    return render_email_from_db_template(
        template_key, oid, ctx, default_html, default_subject, strict_tenant_logo
    )
