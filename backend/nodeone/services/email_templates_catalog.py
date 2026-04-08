"""Render/copia de EmailTemplate por tenant (extraído de app.py)."""

from datetime import datetime


def _finalize_email_subject_from_row(row_subject, default_subject, ctx):
    from flask import render_template_string

    subj = (row_subject or '').strip()
    if not subj:
        subj = default_subject or ''
    try:
        out = render_template_string(subj, **ctx).strip()
        return out or (default_subject or '')
    except Exception:
        return default_subject or ''


def _empty_email_if_no_templates():
    """Evita NameError si email_templates no cargó en runtime."""
    import app as M

    if M.EMAIL_TEMPLATES_AVAILABLE:
        return None
    return '', 'Plantillas de correo no disponibles'


def render_email_from_db_template(
    template_key, organization_id, ctx, default_html, default_subject, strict_tenant_logo=False
):
    """Logo/tenant estricto ya vienen en ctx; strict_tenant_logo se conserva por compat."""
    from flask import render_template_string

    import app as M

    _ = strict_tenant_logo
    try:
        oid = int(organization_id)
    except (TypeError, ValueError):
        oid = int(M.default_organization_id())

    row = M.EmailTemplate.query.filter_by(organization_id=oid, template_key=template_key).first()
    if row is None and oid != 1 and M._enable_multi_tenant_catalog():
        row = M.EmailTemplate.query.filter_by(organization_id=1, template_key=template_key).first()

    if row and row.is_custom and (row.html_content or '').strip():
        subj = _finalize_email_subject_from_row(row.subject, default_subject, ctx)
        try:
            html = render_template_string(row.html_content, **ctx).strip()
        except Exception:
            html = (default_html or '').strip()
        return html, subj

    subj = _finalize_email_subject_from_row((row.subject if row else None), default_subject, ctx)
    return (default_html or '').strip(), subj


def clone_email_templates_from_org(source_organization_id, dest_organization_id, overwrite=False):
    """Copia filas EmailTemplate entre organizaciones. Retorna (created, updated, skipped)."""
    import app as M

    source = int(source_organization_id)
    dest = int(dest_organization_id)
    created = updated = skipped = 0
    rows = M.EmailTemplate.query.filter_by(organization_id=source).all()
    for src in rows:
        existing = M.EmailTemplate.query.filter_by(
            organization_id=dest, template_key=src.template_key
        ).first()
        if existing:
            if overwrite:
                existing.name = src.name
                existing.subject = src.subject
                existing.html_content = src.html_content
                existing.text_content = src.text_content
                existing.category = src.category
                existing.is_custom = src.is_custom
                existing.variables = src.variables
                existing.updated_at = datetime.utcnow()
                updated += 1
            else:
                skipped += 1
        else:
            M.db.session.add(
                M.EmailTemplate(
                    organization_id=dest,
                    template_key=src.template_key,
                    name=src.name,
                    subject=src.subject,
                    html_content=src.html_content,
                    text_content=src.text_content,
                    category=src.category,
                    is_custom=src.is_custom,
                    variables=src.variables,
                )
            )
            created += 1
    M.db.session.commit()
    return created, updated, skipped

