"""Envío de cotizaciones por correo: modal de composición, PDF adjunto, delegación a capa notifications."""

from __future__ import annotations

import html as html_module
import logging
import re
from typing import Any

from flask import current_app

from models.saas import SaasOrganization
from nodeone.modules.notifications.email import send_quotation_email
from nodeone.modules.sales.quotation_pdf import render_quotation_pdf_bytes

logger = logging.getLogger(__name__)


def _escape_html(s: Any) -> str:
    return html_module.escape(str(s) if s is not None else '', quote=False)


def compose_plain_body_to_html(text: str) -> str:
    """Convierte texto plano del modal a HTML seguro (párrafos y saltos de línea)."""
    t = text if isinstance(text, str) else str(text or '')
    if not t.strip():
        return ''
    blocks = t.replace('\r\n', '\n').split('\n\n')
    out = []
    for block in blocks:
        lines = _escape_html(block).split('\n')
        out.append('<p>' + '<br/>'.join(lines) + '</p>')
    return ''.join(out)


def parse_recipient_emails(raw) -> list[str]:
    """Separa direcciones por coma o punto y coma; validación mínima formato email."""
    if raw is None:
        return []
    s = str(raw).strip()
    if not s:
        return []
    out = []
    for part in re.split(r'[,;]+', s):
        p = part.strip()
        if not p:
            continue
        if '@' in p and '.' in p.rsplit('@', 1)[-1]:
            out.append(p)
    return out


def perform_quotation_send(quotation, customer, organization_id: int, data: dict) -> tuple[bool, dict | None]:
    """
    Ejecuta el envío tras POST /quotations/<id>/send.

    ``data``: cuerpo JSON; dict vacío = envío legacy (asunto/cuerpo por defecto, solo cliente).

    Retorna ``(True, None)`` o ``(False, payload)`` donde ``payload`` es el dict de error para ``jsonify``.
    """
    if not data:
        ok, err = send_quotation_email(quotation, customer)
        if ok:
            return True, None
        return False, {'error': 'send_failed', 'detail': err}

    recipients = parse_recipient_emails(data.get('to'))
    if not recipients:
        return False, {
            'error': 'recipients_required',
            'user_message': 'Indique al menos un correo en «Para».',
        }

    subject = (data.get('subject') or '').strip() or None
    body_plain = data.get('body_text')
    html_body = None
    if body_plain is not None and str(body_plain).strip():
        html_body = compose_plain_body_to_html(str(body_plain))

    extra_att: list[dict] = []
    if bool(data.get('attach_pdf', True)):
        try:
            org_row = SaasOrganization.query.get(organization_id)
            org_profile = {
                'name': (org_row.name or '').strip() if org_row else '',
                'legal_name': (getattr(org_row, 'legal_name', '') or '').strip() if org_row else '',
                'tax_id': (getattr(org_row, 'tax_id', '') or '').strip() if org_row else '',
                'fiscal_address': (getattr(org_row, 'fiscal_address', '') or '').strip() if org_row else '',
                'fiscal_city': (getattr(org_row, 'fiscal_city', '') or '').strip() if org_row else '',
                'fiscal_state': (getattr(org_row, 'fiscal_state', '') or '').strip() if org_row else '',
                'fiscal_country': (getattr(org_row, 'fiscal_country', '') or '').strip() if org_row else '',
                'fiscal_phone': (getattr(org_row, 'fiscal_phone', '') or '').strip() if org_row else '',
                'fiscal_email': (getattr(org_row, 'fiscal_email', '') or '').strip() if org_row else '',
            }
            pdf_bytes = render_quotation_pdf_bytes(quotation, customer, org_profile)
            safe_num = re.sub(
                r'[^\w.\-]+', '_', str(quotation.number or 'cotizacion'), flags=re.UNICODE
            )
            extra_att.append(
                {
                    'filename': f'Cotizacion-{safe_num}.pdf',
                    'content_type': 'application/pdf',
                    'data': pdf_bytes,
                }
            )
        except Exception:
            log = getattr(current_app, 'logger', None) or logger
            log.warning('Adjunto PDF de cotización omitido', exc_info=True)

    ok, err = send_quotation_email(
        quotation,
        customer,
        html_body=html_body,
        subject=subject,
        recipients=recipients,
        extra_attachments=extra_att or None,
    )
    if ok:
        return True, None
    return False, {'error': 'send_failed', 'detail': err}
