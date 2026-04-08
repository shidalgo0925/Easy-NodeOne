"""Renderizado de correos por organización (extraído de app.py)."""


def render_welcome_email_for_org(user, organization_id, strict_tenant_logo=False):
    import app as M

    miss = M._empty_email_if_no_templates()
    if miss is not None:
        return miss
    oid = int(organization_id)
    br = M._email_branding_from_organization_id(oid)
    default_html = M.get_welcome_email(user, **br)
    default_subj = f"Bienvenido a {br['organization_name']}"
    ctx = dict(user=user, **br)
    ctx['logo_url'] = M.resolve_email_logo_absolute_url(
        organization_id=oid, allow_fallback_to_platform_logo=not strict_tenant_logo
    )
    return M.render_email_from_db_template('welcome', oid, ctx, default_html, default_subj, strict_tenant_logo)


def render_membership_payment_email_for_org(
    user, payment, subscription, organization_id, strict_tenant_logo=False
):
    import app as M

    miss = M._empty_email_if_no_templates()
    if miss is not None:
        return miss
    oid = int(organization_id)
    br = M._email_branding_from_organization_id(oid)
    default_html = M.get_membership_payment_confirmation_email(user, payment, subscription, **br)
    default_subj = f'Confirmación de Pago - {br["organization_name"]}'
    ctx = dict(user=user, payment=payment, subscription=subscription, **br)
    ctx['logo_url'] = M.resolve_email_logo_absolute_url(
        organization_id=oid, allow_fallback_to_platform_logo=not strict_tenant_logo
    )
    return M.render_email_from_db_template(
        'membership_payment', oid, ctx, default_html, default_subj, strict_tenant_logo
    )


def render_membership_expiring_email_for_org(
    user, subscription, days_left, organization_id, strict_tenant_logo=False
):
    import app as M

    miss = M._empty_email_if_no_templates()
    if miss is not None:
        return miss
    oid = int(organization_id)
    br = M._email_branding_from_organization_id(oid)
    default_html = M.get_membership_expiring_email(user, subscription, days_left, **br)
    default_subj = f'Tu Membresía Expira en {days_left} Días - {br["organization_name"]}'
    ctx = dict(user=user, subscription=subscription, days_left=days_left, **br)
    ctx['logo_url'] = M.resolve_email_logo_absolute_url(
        organization_id=oid, allow_fallback_to_platform_logo=not strict_tenant_logo
    )
    return M.render_email_from_db_template(
        'membership_expiring', oid, ctx, default_html, default_subj, strict_tenant_logo
    )


def render_membership_expired_email_for_org(user, subscription, organization_id, strict_tenant_logo=False):
    import app as M

    miss = M._empty_email_if_no_templates()
    if miss is not None:
        return miss
    oid = int(organization_id)
    br = M._email_branding_from_organization_id(oid)
    default_html = M.get_membership_expired_email(user, subscription, **br)
    default_subj = f'Membresía Expirada - {br["organization_name"]}'
    ctx = dict(user=user, subscription=subscription, **br)
    ctx['logo_url'] = M.resolve_email_logo_absolute_url(
        organization_id=oid, allow_fallback_to_platform_logo=not strict_tenant_logo
    )
    return M.render_email_from_db_template(
        'membership_expired', oid, ctx, default_html, default_subj, strict_tenant_logo
    )


def render_membership_renewed_email_for_org(user, subscription, organization_id, strict_tenant_logo=False):
    import app as M

    miss = M._empty_email_if_no_templates()
    if miss is not None:
        return miss
    oid = int(organization_id)
    br = M._email_branding_from_organization_id(oid)
    default_html = M.get_membership_renewed_email(user, subscription, **br)
    default_subj = f'Membresía Renovada - {br["organization_name"]}'
    ctx = dict(user=user, subscription=subscription, **br)
    ctx['logo_url'] = M.resolve_email_logo_absolute_url(
        organization_id=oid, allow_fallback_to_platform_logo=not strict_tenant_logo
    )
    return M.render_email_from_db_template(
        'membership_renewed', oid, ctx, default_html, default_subj, strict_tenant_logo
    )


def render_event_cancellation_email_for_org(event, user, organization_id, strict_tenant_logo=False):
    import app as M

    miss = M._empty_email_if_no_templates()
    if miss is not None:
        return miss
    oid = int(organization_id)
    br = M._email_branding_from_organization_id(oid)
    default_html = M.get_event_cancellation_email(event, user, **br)
    default_subj = f'Cancelación de Registro: {getattr(event, "title", "Evento")}'
    ctx = dict(event=event, user=user, **br)
    ctx['logo_url'] = M.resolve_email_logo_absolute_url(
        organization_id=oid, allow_fallback_to_platform_logo=not strict_tenant_logo
    )
    return M.render_email_from_db_template(
        'event_cancellation', oid, ctx, default_html, default_subj, strict_tenant_logo
    )


def render_event_update_email_for_org(event, user, changes, organization_id, strict_tenant_logo=False):
    import app as M

    miss = M._empty_email_if_no_templates()
    if miss is not None:
        return miss
    oid = int(organization_id)
    br = M._email_branding_from_organization_id(oid)
    default_html = M.get_event_update_email(event, user, changes=changes, **br)
    default_subj = f'Actualización: {getattr(event, "title", "Evento")}'
    ctx = dict(event=event, user=user, changes=changes, **br)
    ctx['logo_url'] = M.resolve_email_logo_absolute_url(
        organization_id=oid, allow_fallback_to_platform_logo=not strict_tenant_logo
    )
    return M.render_email_from_db_template(
        'event_update', oid, ctx, default_html, default_subj, strict_tenant_logo
    )


def render_password_reset_email_for_org(
    user, reset_token, reset_url, organization_id, strict_tenant_logo=False
):
    import app as M

    miss = M._empty_email_if_no_templates()
    if miss is not None:
        return miss
    oid = int(organization_id)
    br = M._email_branding_from_organization_id(oid)
    default_html = M.get_password_reset_email(user, reset_token, reset_url, **br)
    default_subj = f'Restablecer Contraseña - {br["organization_name"]}'
    ctx = dict(user=user, reset_token=reset_token, reset_url=reset_url, **br)
    ctx['logo_url'] = M.resolve_email_logo_absolute_url(
        organization_id=oid, allow_fallback_to_platform_logo=not strict_tenant_logo
    )
    return M.render_email_from_db_template('password_reset', oid, ctx, default_html, default_subj, strict_tenant_logo)


def render_office365_request_email_for_org(
    user_name,
    email,
    purpose,
    description,
    request_id,
    organization_id,
    strict_tenant_logo=False,
):
    import app as M

    miss = M._empty_email_if_no_templates()
    if miss is not None:
        return miss
    oid = int(organization_id)
    br = M._email_branding_from_organization_id(oid)
    default_html = M.get_office365_request_email(
        user_name, email, purpose, description, request_id, **br
    )
    default_subj = f'Nueva solicitud Office 365 - {email}'
    ctx = dict(
        user_name=user_name,
        email=email,
        purpose=purpose,
        description=description,
        request_id=request_id,
        **br,
    )
    ctx['logo_url'] = M.resolve_email_logo_absolute_url(
        organization_id=oid, allow_fallback_to_platform_logo=not strict_tenant_logo
    )
    return M.render_email_from_db_template('office365_request', oid, ctx, default_html, default_subj, strict_tenant_logo)

