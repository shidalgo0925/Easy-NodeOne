"""Render CRM notification emails using EmailTemplate (admin /admin/email) with code fallbacks."""
import html as html_module


def _apply_curly_placeholders(template_str, ctx):
    out = str(template_str or '')
    for k, v in ctx.items():
        out = out.replace('{' + k + '}', '' if v is None else str(v))
    return out


def resolve_crm_email_template(org_id, template_key):
    from app import EmailTemplate, _enable_multi_tenant_catalog

    oid = int(org_id or 1)
    t = EmailTemplate.query.filter_by(organization_id=oid, template_key=template_key).first()
    if t is None and oid != 1 and _enable_multi_tenant_catalog():
        t = EmailTemplate.query.filter_by(organization_id=1, template_key=template_key).first()
    return t


def build_crm_activity_assigned_email(org_id, ctx_plain, ctx_esc, *, default_subject, default_html, default_text):
    """ctx_plain: subject; ctx_esc: HTML body placeholders (escaped)."""
    t = resolve_crm_email_template(org_id, 'crm_activity_assigned')
    subject = _apply_curly_placeholders(
        (t.subject if t else None) or default_subject, ctx_plain
    )
    if t and t.is_custom and (t.html_content or '').strip():
        html = _apply_curly_placeholders(t.html_content, ctx_esc)
    else:
        html = default_html
    if t and (t.text_content or '').strip():
        text = _apply_curly_placeholders(t.text_content, ctx_plain)
    else:
        text = default_text
    return subject, html, text


def build_crm_activity_reminder_email(org_id, ctx_plain, ctx_esc, *, default_subject, default_html, default_text):
    t = resolve_crm_email_template(org_id, 'crm_activity_reminder')
    subject = _apply_curly_placeholders(
        (t.subject if t else None) or default_subject, ctx_plain
    )
    if t and t.is_custom and (t.html_content or '').strip():
        html = _apply_curly_placeholders(t.html_content, ctx_esc)
    else:
        html = default_html
    if t and (t.text_content or '').strip():
        text = _apply_curly_placeholders(t.text_content, ctx_plain)
    else:
        text = default_text
    return subject, html, text


def crm_email_context_assigned_plain_esc(
    *,
    lead_name,
    activity_summary,
    activity_type,
    due_text,
    crm_url,
    assignee_name,
):
    plain = {
        'lead_name': lead_name or '',
        'activity_summary': activity_summary or '',
        'activity_type': activity_type or '',
        'due_text': due_text or '',
        'crm_url': crm_url or '',
        'assignee_name': assignee_name or '',
    }
    esc = {k: html_module.escape(str(v)) for k, v in plain.items()}
    return plain, esc


def crm_email_context_reminder_plain_esc(
    *,
    lead_name,
    activity_summary,
    activity_type,
    due_text,
    alert_label,
    alert_kind,
    crm_url,
    assignee_name,
):
    plain = {
        'lead_name': lead_name or '',
        'activity_summary': activity_summary or '',
        'activity_type': activity_type or '',
        'due_text': due_text or '',
        'alert_label': alert_label or '',
        'alert_kind': alert_kind or '',
        'crm_url': crm_url or '',
        'assignee_name': assignee_name or '',
    }
    esc = {k: html_module.escape(str(v)) for k, v in plain.items()}
    return plain, esc
