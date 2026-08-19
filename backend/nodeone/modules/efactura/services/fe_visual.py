"""Reglas de representación visual FE (QR solo si accepted + CUFE)."""

from __future__ import annotations

from typing import Any

from models.efactura import ElectronicInvoiceDocument
from nodeone.modules.efactura.services.pac_artifacts import decode_base64_bytes


def find_latest_fe_for_invoice(invoice_id: int, organization_id: int) -> ElectronicInvoiceDocument | None:
    return (
        ElectronicInvoiceDocument.query.filter(
            ElectronicInvoiceDocument.organization_id == int(organization_id),
            ElectronicInvoiceDocument.invoice_id == int(invoice_id),
        )
        .order_by(ElectronicInvoiceDocument.id.desc())
        .first()
    )


def fe_is_accepted(fe: Any | None) -> bool:
    if fe is None:
        return False
    status = (getattr(fe, 'status', None) or '').strip().lower()
    cufe = (getattr(fe, 'cufe', None) or '').strip()
    return status == 'accepted' and bool(cufe)


def should_show_fiscal_qr(fe: Any | None) -> bool:
    return fe_is_accepted(fe)


def fiscal_banner_text(fe: Any | None) -> str:
    if fe is None:
        return 'Documento interno EN1 — Factura Electrónica no autorizada.'
    status = (getattr(fe, 'status', None) or '').strip().lower()
    if status in ('pending', 'sent', 'draft'):
        return 'Factura Electrónica pendiente de autorización.'
    if status in ('rejected', 'error'):
        return 'Factura Electrónica rechazada — revisar estado fiscal.'
    if status == 'accepted' and not (getattr(fe, 'cufe', None) or '').strip():
        return 'Factura Electrónica pendiente de autorización.'
    if status == 'accepted':
        return ''
    return 'Documento interno EN1 — Factura Electrónica no autorizada.'


def resolve_qr_payload(fe: Any | None) -> tuple[bytes | None, str | None, str | None]:
    """
    Retorna (imagen_png_o_jpeg, texto_codificado, fuente).
    Prioridad: imagen PAC → URL PAC → qrContent PAC → CUFE (solo accepted).
    """
    if not should_show_fiscal_qr(fe):
        return None, None, None
    img = decode_base64_bytes(getattr(fe, 'qr_image_base64', None))
    if img and len(img) > 32:
        payload = (getattr(fe, 'qr_content', None) or getattr(fe, 'cufe', None) or '').strip() or None
        return img, payload, 'pac_image'
    content = (getattr(fe, 'qr_content', None) or '').strip()
    url = (getattr(fe, 'qr_url', None) or getattr(fe, 'consultation_url', None) or '').strip()
    if content.startswith('http://') or content.startswith('https://'):
        return None, content, 'pac_url'
    if url.startswith('http://') or url.startswith('https://'):
        return None, url, 'pac_url'
    if content:
        return None, content, 'pac_content'
    cufe = (getattr(fe, 'cufe', None) or '').strip()
    return None, cufe, 'cufe'


def serialize_fe_for_invoice(fe: ElectronicInvoiceDocument | None) -> dict[str, Any] | None:
    if fe is None:
        return None
    has_pdf = bool((getattr(fe, 'pdf_content', None) or '').strip())
    has_xml = bool((getattr(fe, 'xml_content', None) or '').strip())
    return {
        'id': fe.id,
        'status': fe.status,
        'cufe': fe.cufe,
        'authorization_message': fe.authorization_message,
        'protocolo': fe.pac_reference,
        'authorized_at': fe.authorized_at.isoformat() if getattr(fe, 'authorized_at', None) else None,
        'accepted_at': fe.accepted_at.isoformat() if fe.accepted_at else None,
        'has_qr': should_show_fiscal_qr(fe),
        'has_pac_document': has_pdf or has_xml,
        'pac_kind': 'pdf' if has_pdf else ('xml' if has_xml else None),
        'qr_source': getattr(fe, 'qr_source', None),
        'consultation_url': getattr(fe, 'consultation_url', None),
    }
