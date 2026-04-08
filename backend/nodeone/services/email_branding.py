"""Helpers de branding/logo para correo (extraído de app.py)."""

import os


def resolve_email_logo_absolute_url(organization_id=None, allow_fallback_to_platform_logo=True):
    """
    URL absoluta del logo para plantillas HTML de correo (atributo src).
    Usa organization_settings.logo_url de la org indicada; si no hay y
    allow_fallback_to_platform_logo, usa get_system_logo().
    """
    from flask import has_request_context, request, url_for

    import app as M

    try:
        oid = int(organization_id) if organization_id is not None else int(M.default_organization_id())
    except (TypeError, ValueError):
        oid = int(M.default_organization_id())

    rel = None
    try:
        row = M.OrganizationSettings.query.filter_by(organization_id=oid).first()
        if row is None and int(oid) == int(M.default_organization_id()):
            row = M.OrganizationSettings.query.filter(
                M.OrganizationSettings.organization_id.is_(None)
            ).first()
        if row and (row.logo_url or '').strip():
            rel = (row.logo_url or '').strip().lstrip('/')
    except Exception:
        pass

    if not rel:
        if not allow_fallback_to_platform_logo:
            return ''
        rel = (M.get_system_logo() or '').strip().lstrip('/')

    if not rel:
        return ''

    try:
        relative_url = url_for('static', filename=rel, _external=False)
    except Exception:
        rel_fb = (M.get_system_logo() or '').strip().lstrip('/')
        if not rel_fb:
            return ''
        relative_url = url_for('static', filename=rel_fb, _external=False)

    base_url = None
    if has_request_context() and request:
        base_url = request.url_root.rstrip('/')
    if not base_url:
        base_url = (os.getenv('BASE_URL') or 'https://miembros.relatic.org').rstrip('/')

    return f"{base_url}{relative_url}"


def email_preview_base_url():
    from flask import has_request_context, request

    if has_request_context() and request:
        return request.url_root.rstrip('/')
    return (os.getenv('BASE_URL') or 'https://miembros.relatic.org').rstrip('/')


def email_branding_from_organization_id(organization_id):
    """kwargs organization_name, base_url, contact_email, org_tagline para email_templates."""
    from email_templates import _default_contact_email, _default_platform_display_name

    import app as M

    try:
        oid = int(organization_id)
    except (TypeError, ValueError):
        oid = int(M.default_organization_id())

    org_name = _default_platform_display_name()
    try:
        org = M.SaasOrganization.query.get(oid)
        if org and (org.name or '').strip():
            org_name = (org.name or '').strip()
    except Exception:
        pass

    base_url = email_preview_base_url()
    contact_email = _default_contact_email()
    try:
        ec = M.EmailConfig.get_active_config(
            organization_id=oid,
            allow_fallback_to_default_org=True,
        )
        if ec and (ec.mail_default_sender or '').strip():
            contact_email = (ec.mail_default_sender or '').strip()
    except Exception:
        pass
    org_tagline = (os.environ.get('PLATFORM_TAGLINE') or '').strip()

    return {
        'organization_name': org_name,
        'base_url': base_url,
        'contact_email': contact_email,
        'org_tagline': org_tagline,
    }


def inject_organization_email_context(ctx, organization_id):
    b = email_branding_from_organization_id(organization_id)
    for k, v in b.items():
        ctx.setdefault(k, v)

