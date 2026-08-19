"""Extrae y persiste artefactos FE del contrato real de efacturapty (CreateInvoiceResponse)."""

from __future__ import annotations

import base64
import binascii
from datetime import datetime
from typing import Any

from models.efactura import ElectronicInvoiceDocument

# Swagger CreateInvoiceResponse (POST /api/v1/Invoices?qr=true&xml=true)
_QR_IMAGE_KEYS = (
    'qrContentImageBase64',
    'qr_content_image_base64',
    'qrImageBase64',
)
_QR_CONTENT_KEYS = (
    'qrContent',
    'qr_content',
    'qr',
    'qrUrl',
    'qr_url',
)
_XML_KEYS = ('xml', 'xml_base64', 'xmlBase64')
_PDF_KEYS = ('pdf', 'pdf_base64', 'pdfBase64', 'cafe', 'cafePdf')
_URL_KEYS = ('urlConsulta', 'url_consulta', 'consultaUrl', 'dgiUrl', 'consultationUrl')


def _first_str(data: dict, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        val = data.get(key)
        if val is None:
            continue
        text = str(val).strip()
        if text:
            return text
    return None


def extract_pac_artifacts(raw: Any) -> dict[str, Any]:
    """Lee nombres reales del PAC; no inventa campos. Solo primer nivel del JSON de emisión."""
    data = raw if isinstance(raw, dict) else {}
    qr_image = _first_str(data, _QR_IMAGE_KEYS)
    qr_content = _first_str(data, _QR_CONTENT_KEYS)
    xml = _first_str(data, _XML_KEYS)
    pdf = _first_str(data, _PDF_KEYS)
    consulta = _first_str(data, _URL_KEYS)
    fecha = data.get('fechaAutorizacion') or data.get('fecha_autorizacion')
    protocolo = data.get('protocoloAutorizacion') or data.get('protocolo')
    cufe = data.get('cufe')
    pac_id = data.get('id')
    source = None
    if qr_image:
        source = 'pac_image'
    elif qr_content and (qr_content.startswith('http://') or qr_content.startswith('https://')):
        source = 'pac_url'
    elif qr_content:
        source = 'pac_content'
    return {
        'qr_image_base64': qr_image,
        'qr_content': qr_content,
        'xml_content': xml,
        'pdf_base64': pdf,
        'consultation_url': consulta,
        'fecha_autorizacion': fecha,
        'protocolo': str(protocolo).strip() if protocolo else None,
        'cufe': str(cufe).strip() if cufe else None,
        'pac_document_id': str(pac_id).strip() if pac_id else None,
        'qr_source': source,
    }


def _parse_dt(value: Any) -> datetime | None:
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        return value
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace('Z', '+00:00')).replace(tzinfo=None)
    except ValueError:
        return None


def _clip(text: str | None, n: int) -> str | None:
    if not text:
        return None
    t = text.strip()
    return t[:n] if t else None


def apply_extracted_artifacts(doc: ElectronicInvoiceDocument, extracted: dict[str, Any]) -> None:
    if extracted.get('protocolo'):
        doc.pac_reference = extracted['protocolo']
    if extracted.get('cufe') and not (doc.cufe or '').strip():
        doc.cufe = extracted['cufe']
    qr_img = extracted.get('qr_image_base64')
    if qr_img:
        doc.qr_image_base64 = qr_img
    qr_content = extracted.get('qr_content')
    if qr_content:
        doc.qr_content = qr_content
        if qr_content.startswith('http://') or qr_content.startswith('https://'):
            doc.qr_url = _clip(qr_content, 500)
    xml = extracted.get('xml_content')
    if xml:
        doc.xml_content = xml
        if xml.startswith('http://') or xml.startswith('https://'):
            doc.xml_url = _clip(xml, 500)
    pdf_b64 = extracted.get('pdf_base64')
    if pdf_b64:
        doc.pdf_content = pdf_b64
    consulta = extracted.get('consultation_url')
    if consulta:
        doc.consultation_url = _clip(consulta, 500)
    fecha = _parse_dt(extracted.get('fecha_autorizacion'))
    if fecha:
        doc.authorized_at = fecha
    if extracted.get('pac_document_id'):
        doc.pac_document_id = _clip(extracted['pac_document_id'], 80)
    if extracted.get('qr_source'):
        doc.qr_source = extracted['qr_source']


def persist_emit_artifacts(doc: ElectronicInvoiceDocument, result: dict[str, Any]) -> None:
    merged: dict[str, Any] = {}
    raw = result.get('raw_response') if isinstance(result, dict) else None
    if isinstance(raw, dict):
        merged.update(extract_pac_artifacts(raw))
    merged.update({k: v for k, v in extract_pac_artifacts(result).items() if v})
    if result.get('qr_image_base64'):
        merged['qr_image_base64'] = result.get('qr_image_base64')
        merged['qr_source'] = merged.get('qr_source') or 'pac_image'
    if result.get('qr_content'):
        merged['qr_content'] = result.get('qr_content')
        merged['qr_source'] = merged.get('qr_source') or 'pac_content'
    if result.get('xml_base64'):
        merged['xml_content'] = result.get('xml_base64')
    if result.get('fecha_autorizacion'):
        merged['fecha_autorizacion'] = result.get('fecha_autorizacion')
    if result.get('protocolo'):
        merged['protocolo'] = result.get('protocolo')
    if result.get('cufe'):
        merged['cufe'] = result.get('cufe')
    if result.get('pac_document_id'):
        merged['pac_document_id'] = result.get('pac_document_id')
    apply_extracted_artifacts(doc, merged)


def decode_base64_bytes(raw: str | None) -> bytes | None:
    if not raw:
        return None
    text = raw.strip()
    if text.startswith('data:') and ',' in text:
        text = text.split(',', 1)[1]
    try:
        return base64.b64decode(text, validate=False)
    except (binascii.Error, ValueError):
        return None


def enrich_fe_artifacts_from_pac(adapter, doc: ElectronicInvoiceDocument) -> None:
    """Solo en emisión: completa QR/PDF PAC si el POST no los trajo. No usar al regenerar PDF."""
    if (doc.status or '') != 'accepted':
        return
    cufe = (doc.cufe or '').strip()
    if not cufe:
        return
    if not (doc.qr_image_base64 or '').strip():
        try:
            img = adapter.fetch_qr_image_base64(cufe)
        except Exception:
            img = None
        if img:
            doc.qr_image_base64 = img
            doc.qr_source = 'pac_image'
    if not (doc.pdf_content or '').strip():
        key = (doc.pac_document_id or cufe).strip()
        try:
            pdf_bytes = adapter.fetch_cafe_pdf(key)
        except Exception:
            pdf_bytes = None
        if pdf_bytes:
            doc.pdf_content = base64.b64encode(pdf_bytes).decode('ascii')
            doc.pdf_url = _clip(f'en1://fe-pac/{doc.id or 0}', 500)
