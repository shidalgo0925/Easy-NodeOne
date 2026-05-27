"""Confirmación por correo antes de entregar el PDF del programa académico."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta

CONFIRMATION_TOKEN_TTL = timedelta(hours=48)


def generate_confirmation_token() -> str:
    return secrets.token_urlsafe(32)


def confirmation_url_for_lead(*, base_url: str, program_slug: str, token: str) -> str:
    slug = (program_slug or '').strip().lower()
    tok = (token or '').strip()
    return f"{base_url.rstrip('/')}/programa-academico/{slug}/confirmar-pdf?token={tok}"


def resource_lead_confirmation_url(*, base_url: str, resource_id: int, token: str) -> str:
    tok = (token or '').strip()
    return f"{base_url.rstrip('/')}/program-resources/{int(resource_id)}/confirmar?token={tok}"


def resource_download_url_with_token(*, base_url: str, resource_id: int, token: str) -> str:
    tok = (token or '').strip()
    return f"{base_url.rstrip('/')}/program-resources/{int(resource_id)}/download?token={tok}"


def pdf_download_url(*, base_url: str, program_slug: str) -> str:
    slug = (program_slug or '').strip().lower()
    return f"{base_url.rstrip('/')}/programa-academico/{slug}/pdf"


def _email_html(*, recipient_name: str, program_name: str, confirm_url: str) -> str:
    name = (recipient_name or '').strip() or 'Hola'
    prog = (program_name or '').strip() or 'programa académico'
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f5f7fb;font-family:Inter,Arial,sans-serif;color:#1e293b;">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;margin:24px auto;background:#fff;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0;">
    <tr>
      <td style="padding:24px 28px;background:linear-gradient(135deg,#1e293b,#5b21b6);color:#fff;">
        <p style="margin:0;font-size:18px;font-weight:700;">International Institute</p>
        <p style="margin:8px 0 0;font-size:14px;opacity:0.92;">Confirmá tu correo para descargar el programa</p>
      </td>
    </tr>
    <tr>
      <td style="padding:28px;">
        <p style="margin:0 0 12px;">Hola <strong>{name}</strong>,</p>
        <p style="margin:0 0 16px;line-height:1.5;">
          Recibimos tu solicitud del programa <strong>{prog}</strong>.
          Para verificar tu correo y acceder al PDF, hacé clic en el botón:
        </p>
        <p style="margin:0 0 20px;text-align:center;">
          <a href="{confirm_url}" style="display:inline-block;padding:12px 24px;background:#c9a227;color:#1e293b;text-decoration:none;font-weight:700;border-radius:8px;">
            Confirmar correo y descargar PDF
          </a>
        </p>
        <p style="margin:0 0 8px;font-size:13px;color:#64748b;line-height:1.5;">
          Si el botón no funciona, copiá este enlace en el navegador:<br>
          <a href="{confirm_url}" style="color:#5b21b6;word-break:break-all;">{confirm_url}</a>
        </p>
        <p style="margin:16px 0 0;font-size:12px;color:#94a3b8;">
          El enlace vence en 48 horas. Revisá también la carpeta de spam.
          Si no solicitaste este correo, podés ignorarlo.
        </p>
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_confirmation_email(lead, program, *, base_url: str, resource=None) -> tuple[bool, str | None]:
    """Envía correo de confirmación. Retorna (ok, mensaje_error)."""
    try:
        import app as ap
    except ImportError:
        return False, 'email_service_unavailable'

    oid = getattr(lead, 'organization_id', None)
    if oid is not None:
        apply_fn = getattr(ap, 'apply_transactional_smtp_for_organization', None)
        if callable(apply_fn):
            ok_smtp, _cfg_id = apply_fn(int(oid))
            if not ok_smtp:
                return False, 'smtp_not_configured'

    if not getattr(ap, 'email_service', None):
        return False, 'email_service_unavailable'

    mail_user = ''
    try:
        mail_user = (ap.app.config.get('MAIL_USERNAME') or '').strip()
        mail_pass = (ap.app.config.get('MAIL_PASSWORD') or '').strip()
    except Exception:
        mail_pass = ''
    if not mail_user or not mail_pass:
        return False, 'smtp_credentials_missing'

    program_name = getattr(program, 'name', None) or lead.program_slug or 'Programa'
    resource_title = (getattr(resource, 'title', None) or '').strip() if resource else ''
    if resource is not None and getattr(lead, 'resource_id', None):
        confirm_url = resource_lead_confirmation_url(
            base_url=base_url,
            resource_id=int(lead.resource_id),
            token=lead.confirmation_token or '',
        )
        subject_label = resource_title or program_name
    else:
        confirm_url = confirmation_url_for_lead(
            base_url=base_url,
            program_slug=lead.program_slug or '',
            token=lead.confirmation_token or '',
        )
        subject_label = program_name
    html = _email_html(
        recipient_name=lead.name,
        program_name=subject_label,
        confirm_url=confirm_url,
    )
    subject = f'Confirmá tu correo — {subject_label}'
    text = (
        f'Hola {lead.name},\n\n'
        f'Confirmá tu correo para acceder al material ({subject_label}):\n'
        f'{confirm_url}\n\n'
        'El enlace vence en 48 horas.\n'
    )
    ok = ap.email_service.send_email(
        subject=subject,
        recipients=[lead.email],
        html_content=html,
        text_content=text,
        email_type='academic_program_pdf_lead',
        related_entity_type='academic_program_pdf_lead',
        related_entity_id=lead.id,
        recipient_name=lead.name,
    )
    if not ok:
        return False, 'email_send_failed'
    return True, None


def assign_confirmation_token(lead) -> None:
    lead.confirmation_token = generate_confirmation_token()
    lead.confirmation_token_expires = datetime.utcnow() + CONFIRMATION_TOKEN_TTL
    lead.confirmation_sent_at = datetime.utcnow()
    lead.status = 'pending'


def confirm_lead_by_token(*, program_slug: str, token: str, resource_id: int | None = None):
    """Marca lead como confirmado. Retorna (lead, program, error_code)."""
    from models.academic_program import AcademicProgram
    from models.academic_program_pdf_lead import AcademicProgramPdfLead
    from nodeone.core.db import db

    slug = (program_slug or '').strip().lower()
    tok = (token or '').strip()
    if not tok:
        return None, None, 'invalid_request'

    lead = (
        AcademicProgramPdfLead.query.filter_by(
            confirmation_token=tok,
        )
        .order_by(AcademicProgramPdfLead.id.desc())
        .first()
    )
    if lead is None:
        return None, None, 'token_not_found'

    if resource_id is not None and int(getattr(lead, 'resource_id', 0) or 0) != int(resource_id):
        return lead, None, 'program_mismatch'

    if slug and (lead.program_slug or '').strip().lower() != slug:
        return lead, None, 'program_mismatch'

    expires = lead.confirmation_token_expires
    if expires and expires < datetime.utcnow():
        return lead, None, 'token_expired'

    program = AcademicProgram.query.get(lead.program_id) if lead.program_id else None
    if program is None and slug:
        program = AcademicProgram.query.filter_by(slug=slug).first()
    if program is not None and slug and (program.slug or '').strip().lower() != slug:
        return lead, None, 'program_mismatch'

    if (lead.status or '').lower() == 'confirmed' and lead.email_confirmed_at:
        return lead, program, None

    if (lead.status or '').lower() not in ('pending', 'new'):
        return lead, None, 'invalid_status'

    lead.status = 'confirmed'
    lead.email_confirmed_at = datetime.utcnow()
    db.session.commit()

    try:
        from nodeone.modules.academic_enrollment.pdf_lead_crm_sync import sync_confirmed_pdf_lead_to_crm

        sync_confirmed_pdf_lead_to_crm(lead, program)
    except Exception as exc:
        from flask import current_app

        try:
            current_app.logger.exception('[pdf_lead] CRM sync failed lead_id=%s: %s', lead.id, exc)
        except Exception:
            pass

    return lead, program, None
