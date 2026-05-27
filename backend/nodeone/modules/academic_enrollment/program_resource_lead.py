"""Lead Capture V2 por recurso de programa (email confirmado → descarga)."""

from __future__ import annotations

import re

from flask import current_app, request

from nodeone.modules.academic_enrollment.pdf_lead_confirmation import (
    assign_confirmation_token,
    resource_lead_confirmation_url,
    send_confirmation_email,
)


def _strip_nohtml(s: str | None, *, max_len: int | None = None) -> str:
    out = re.sub(r'<[^>]*?>', '', (s or '').strip())
    if re.search(r'(?i)script', out):
        out = ''
    if max_len is not None:
        out = out[:max_len]
    return out


def find_resource_for_lead(resource_id: int):
    from models.academic_program import AcademicProgram, AcademicProgramResource

    resource = AcademicProgramResource.query.get(int(resource_id))
    if resource is None or not resource.is_active:
        return None, None
    if not getattr(resource, 'requires_lead_capture', False):
        return None, None
    program = AcademicProgram.query.get(int(resource.program_id))
    if program is None or (program.status or '').strip().lower() != 'published':
        return None, None
    return resource, program


def lead_token_grants_resource_access(resource, token: str | None) -> bool:
    """Token de confirmación válido para este recurso."""
    from datetime import datetime

    from models.academic_program_pdf_lead import AcademicProgramPdfLead

    tok = (token or '').strip()
    if not tok or resource is None:
        return False
    lead = (
        AcademicProgramPdfLead.query.filter_by(
            resource_id=int(resource.id),
            confirmation_token=tok,
            status='confirmed',
        )
        .order_by(AcademicProgramPdfLead.id.desc())
        .first()
    )
    if lead is None or not lead.email_confirmed_at:
        return False
    expires = lead.confirmation_token_expires
    if expires and expires < datetime.utcnow():
        return False
    return True


def submit_resource_lead(resource, program, payload: dict, *, organization_id: int) -> tuple[dict, int]:
    """Procesa POST lead. Devuelve (body_json, status_code)."""
    from nodeone.core.db import db
    from models.academic_program_pdf_lead import AcademicProgramPdfLead
    from nodeone.services.academic_program_pdf_lead_schema import ensure_academic_program_pdf_lead_schema

    hp = (
        payload.get('hp')
        or payload.get('honeypot')
        or payload.get('website')
        or payload.get('leave_blank')
        or ''
    )
    if isinstance(hp, str) and hp.strip():
        return {'success': False, 'message': 'spam_detected'}, 400

    name = _strip_nohtml(payload.get('name'), max_len=200)
    email = (payload.get('email') or '').strip().lower()
    phone = (payload.get('phone') or '').strip()
    program_slug_body = (payload.get('program_slug') or '').strip().lower()
    slug_norm = (program.slug or '').strip().lower()
    source = _strip_nohtml(payload.get('source'), max_len=120) or 'resource_lead_v2'

    country = _strip_nohtml(payload.get('country'), max_len=120) or None
    company = _strip_nohtml(payload.get('company'), max_len=255) or None
    message = _strip_nohtml(payload.get('message'), max_len=2000) or None

    utm_source = _strip_nohtml(payload.get('utm_source'), max_len=120) or None
    utm_medium = _strip_nohtml(payload.get('utm_medium'), max_len=120) or None
    utm_campaign = _strip_nohtml(payload.get('utm_campaign'), max_len=120) or None

    if not name:
        return {'success': False, 'message': 'Nombre es requerido.'}, 400
    if program_slug_body and program_slug_body != slug_norm:
        return {'success': False, 'message': 'program_slug inválido para este programa.'}, 400
    if not email or '@' not in email or len(email) > 255 or re.search(r'\s', email):
        return {'success': False, 'message': 'Email es requerido y debe ser válido.'}, 400
    if not phone or len(phone) < 6 or len(re.sub(r'\D+', '', phone)) < 6:
        return {'success': False, 'message': 'Teléfono es requerido.'}, 400

    ensure_academic_program_pdf_lead_schema(db, db.engine)
    base_url = request.host_url.rstrip('/')

    existing = (
        AcademicProgramPdfLead.query.filter_by(
            organization_id=int(organization_id),
            resource_id=int(resource.id),
            email=email,
        )
        .filter(AcademicProgramPdfLead.status.in_(('pending', 'new')))
        .order_by(AcademicProgramPdfLead.id.desc())
        .first()
    )

    if existing is not None:
        lead = existing
        lead.name = name
        lead.phone = phone
        lead.country = country
        lead.company = company
        lead.message = message
        lead.source = source[:120]
        lead.utm_source = utm_source
        lead.utm_medium = utm_medium
        lead.utm_campaign = utm_campaign
        lead.program_id = program.id
        lead.program_slug = slug_norm
        lead.ip_address = (request.headers.get('X-Forwarded-For') or request.remote_addr or '')[:64]
        lead.user_agent = (request.headers.get('User-Agent') or '')[:500]
    else:
        lead = AcademicProgramPdfLead(
            organization_id=int(organization_id),
            program_id=program.id,
            program_slug=slug_norm,
            resource_id=int(resource.id),
            name=name,
            email=email,
            phone=phone,
            country=country,
            company=company,
            message=message,
            source=source[:120],
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            ip_address=(request.headers.get('X-Forwarded-For') or request.remote_addr or '')[:64],
            user_agent=(request.headers.get('User-Agent') or '')[:500],
            status='pending',
        )
        db.session.add(lead)

    assign_confirmation_token(lead)
    db.session.commit()

    sent_ok, send_err = send_confirmation_email(
        lead,
        program,
        base_url=base_url,
        resource=resource,
    )
    if not sent_ok:
        current_app.logger.warning(
            '[resource_lead] email no enviado lead_id=%s err=%s', lead.id, send_err
        )
        if send_err in ('smtp_not_configured', 'smtp_credentials_missing', 'email_service_unavailable'):
            user_msg = (
                'El servidor de correo no está configurado. '
                'Contactá al administrador (Configuración → Email / SMTP).'
            )
        else:
            user_msg = (
                'No pudimos enviar el correo de confirmación. '
                'Revisá que el email sea correcto e intentá de nuevo en unos minutos.'
            )
        return {'success': False, 'message': user_msg}, 503

    return {
        'success': True,
        'requires_email_confirmation': True,
        'message': (
            'Te enviamos un correo de confirmación. '
            'Abrí el enlace del mensaje para descargar el material. '
            'Revisá también la carpeta de spam.'
        ),
    }, 200
