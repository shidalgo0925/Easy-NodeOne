"""Emisión FE y prueba de conexión."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from nodeone.core.db import db
from models.efactura import (
    ElectronicInvoiceDocument,
    ElectronicInvoiceEventLog,
    ElectronicInvoiceProviderConfig,
)
from nodeone.modules.efactura.services import config_service as cfg_svc
from nodeone.modules.accounting.models import Invoice, InvoiceLine
from nodeone.modules.efactura.services.mapper import build_invoice_payload, build_test_invoice_payload
from models.contact import Contact
from nodeone.modules.contacts.invoice_integration import (
    fiscal_display_name,
    fiscal_email as contact_fiscal_email,
    get_invoice_fiscal_contact,
)
from nodeone.services.commercial_partner_service import display_name, fiscal_email, get_partner
from nodeone.services.efactura_module import is_efactura_enabled_for_org


def _json_dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def _json_load(text: str | None) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return text


def _adapter_for(config: ElectronicInvoiceProviderConfig):
    if config.provider != cfg_svc.PROVIDER_EFACTURAPTY:
        raise ValueError(f'Proveedor no soportado: {config.provider}')
    from nodeone.modules.efactura.adapters.efacturapty import EFacturaPTYAdapter

    return EFacturaPTYAdapter(config)


def _log_event(
    organization_id: int,
    event_type: str,
    *,
    document_id: int | None = None,
    message: str | None = None,
    http_status: int | None = None,
    request_payload: Any = None,
    response_payload: Any = None,
) -> ElectronicInvoiceEventLog:
    row = ElectronicInvoiceEventLog(
        organization_id=int(organization_id),
        document_id=document_id,
        event_type=event_type,
        message=message,
        http_status=http_status,
        request_payload=_json_dump(request_payload) if request_payload is not None else None,
        response_payload=_json_dump(response_payload) if response_payload is not None else None,
    )
    db.session.add(row)
    return row


def test_connection(organization_id: int) -> dict[str, Any]:
    if not is_efactura_enabled_for_org(organization_id):
        return {'ok': False, 'message': 'Módulo efactura no habilitado para esta organización.'}
    config = cfg_svc.get_or_create_provider_config(organization_id)
    if not cfg_svc.resolve_api_token(config):
        return {'ok': False, 'message': 'Configure el token de API antes de probar.'}
    adapter = _adapter_for(config)
    result = adapter.test_connection()
    config.last_test_status = 'ok' if result.get('ok') else 'error'
    config.last_test_message = result.get('message')
    _log_event(
        organization_id,
        'test_connection',
        message=result.get('message'),
        http_status=result.get('http_status'),
        response_payload=result,
    )
    db.session.commit()
    return result


def issue_test_invoice(
    organization_id: int,
    *,
    amount: Decimal,
    description: str,
    customer_email: str,
    customer_name: str = 'CONSUMIDOR FINAL',
    internal_reference: str | None = None,
) -> ElectronicInvoiceDocument:
    if not is_efactura_enabled_for_org(organization_id):
        raise ValueError('Módulo efactura no habilitado para esta organización.')
    config = cfg_svc.get_or_create_provider_config(organization_id)
    if not cfg_svc.config_ready(config):
        raise ValueError('Configure y active el proveedor antes de emitir.')
    if amount <= 0:
        raise ValueError('El monto debe ser mayor que cero.')
    if not (customer_email or '').strip():
        raise ValueError('El correo del receptor es obligatorio.')

    pac_payload = build_test_invoice_payload(
        config,
        amount=amount,
        description=description,
        customer_email=customer_email.strip(),
        customer_name=customer_name,
    )
    en1_request = {
        'document_type': 'invoice',
        'customer': {
            'name': customer_name,
            'email': customer_email.strip(),
            'is_final_consumer': True,
        },
        'lines': [
            {
                'description': description,
                'quantity': 1,
                'unit_price': float(amount),
                'tax_code': '00',
            }
        ],
        'pac_payload_preview': pac_payload,
    }

    doc = ElectronicInvoiceDocument(
        organization_id=int(organization_id),
        provider=config.provider,
        environment=config.environment,
        document_type='invoice',
        internal_reference=internal_reference or f'TEST-{datetime.utcnow().strftime("%Y%m%d%H%M%S")}',
        source_model='efactura_test',
        customer_name=customer_name,
        customer_email=customer_email.strip(),
        subtotal=amount,
        tax_total=Decimal('0'),
        discount_total=Decimal('0'),
        total=amount,
        currency=config.default_currency or 'USD',
        status='pending',
        request_payload=_json_dump(en1_request),
    )
    db.session.add(doc)
    db.session.flush()

    adapter = _adapter_for(config)
    _log_event(
        organization_id,
        'emit_invoice',
        document_id=doc.id,
        message='Enviando factura de prueba',
        request_payload=pac_payload,
    )
    try:
        result = adapter.emit_invoice(doc, pac_payload)
    except Exception as exc:
        doc.status = 'error'
        doc.error_message = str(exc)
        _log_event(
            organization_id,
            'error',
            document_id=doc.id,
            message=str(exc),
        )
        db.session.commit()
        raise

    doc.response_payload = _json_dump(result.get('raw_response'))
    doc.pac_reference = result.get('protocolo')
    doc.authorization_message = result.get('authorization_message')
    doc.issued_at = datetime.utcnow()

    if result.get('autorizada'):
        doc.status = 'accepted'
        doc.cufe = result.get('cufe')
        doc.accepted_at = datetime.utcnow()
    elif result.get('http_status') and result.get('http_status') >= 400:
        doc.status = 'error'
        doc.error_message = result.get('authorization_message') or 'Error HTTP del PAC'
    else:
        doc.status = 'rejected'
        doc.rejected_at = datetime.utcnow()
        doc.error_message = result.get('authorization_message') or 'Rechazada por el PAC'

    _log_event(
        organization_id,
        'emit_invoice',
        document_id=doc.id,
        message=doc.authorization_message,
        http_status=result.get('http_status'),
        response_payload=result.get('raw_response'),
    )
    db.session.commit()
    return doc


_ACTIVE_FE_STATUSES = ('pending', 'sent', 'accepted')


def find_active_fe_for_invoice(invoice_id: int, organization_id: int) -> ElectronicInvoiceDocument | None:
    return (
        ElectronicInvoiceDocument.query.filter(
            ElectronicInvoiceDocument.organization_id == int(organization_id),
            ElectronicInvoiceDocument.invoice_id == int(invoice_id),
            ElectronicInvoiceDocument.status.in_(_ACTIVE_FE_STATUSES),
        )
        .order_by(ElectronicInvoiceDocument.id.desc())
        .first()
    )


def _apply_pac_result(doc: ElectronicInvoiceDocument, result: dict[str, Any]) -> None:
    doc.response_payload = _json_dump(result.get('raw_response'))
    doc.pac_reference = result.get('protocolo')
    doc.authorization_message = result.get('authorization_message')
    doc.issued_at = datetime.utcnow()
    if result.get('autorizada'):
        doc.status = 'accepted'
        doc.cufe = result.get('cufe')
        doc.accepted_at = datetime.utcnow()
    elif result.get('http_status') and result.get('http_status') >= 400:
        doc.status = 'error'
        doc.error_message = result.get('authorization_message') or 'Error HTTP del PAC'
    else:
        doc.status = 'rejected'
        doc.rejected_at = datetime.utcnow()
        doc.error_message = result.get('authorization_message') or 'Rechazada por el PAC'


def maybe_auto_emit_for_invoice(invoice_id: int, organization_id: int, *, trigger: str) -> ElectronicInvoiceDocument | None:
    """`trigger`: `invoice_confirm` | `payment_confirmed`. No lanza si falla (solo log)."""
    if not is_efactura_enabled_for_org(organization_id):
        return None
    config = cfg_svc.get_or_create_provider_config(organization_id)
    if not cfg_svc.config_ready(config):
        return None
    if (config.emission_mode or 'manual') != 'automatic':
        return None
    if trigger == 'invoice_confirm' and not config.emit_on_invoice_confirm:
        return None
    if trigger == 'payment_confirmed' and not config.emit_on_payment_confirmed:
        return None
    if find_active_fe_for_invoice(invoice_id, organization_id):
        return None
    try:
        return issue_from_commercial_invoice(invoice_id, organization_id)
    except Exception as exc:
        _log_event(
            organization_id,
            'error',
            message=f'Auto FE ({trigger}): {exc}',
            document_id=None,
        )
        db.session.commit()
        return None


def issue_from_commercial_invoice(invoice_id: int, organization_id: int) -> ElectronicInvoiceDocument:
    """Emite FE desde factura comercial EN1 (Fase 8)."""
    if not is_efactura_enabled_for_org(organization_id):
        raise ValueError('Módulo efactura no habilitado para esta organización.')
    inv = Invoice.query.filter_by(id=int(invoice_id), organization_id=int(organization_id)).first()
    if not inv:
        raise ValueError('Factura no encontrada.')
    if inv.status in ('draft', 'cancelled'):
        raise ValueError('La factura debe estar contabilizada o pagada antes de emitir FE.')
    existing = find_active_fe_for_invoice(inv.id, organization_id)
    if existing:
        raise ValueError(f'Ya existe una FE activa para esta factura (documento #{existing.id}).')
    cid = getattr(inv, 'contact_id', None) or getattr(inv, 'customer_contact_id', None)
    if not cid:
        raise ValueError('La factura no tiene contacto fiscal (contact_id).')
    contact = get_invoice_fiscal_contact(inv)
    if not contact:
        contact = get_partner(organization_id, int(cid))
    if not contact:
        raise ValueError('Contacto fiscal no encontrado.')
    fe_email = contact_fiscal_email(contact) if isinstance(contact, Contact) else fiscal_email(contact)
    if not fe_email:
        raise ValueError('El contacto debe tener correo fiscal para efacturapty.')
    lines = InvoiceLine.query.filter_by(invoice_id=inv.id).order_by(InvoiceLine.id).all()
    config = cfg_svc.get_or_create_provider_config(organization_id)
    if not cfg_svc.config_ready(config):
        raise ValueError('Configure y active el proveedor FE antes de emitir.')
    pac_payload = build_invoice_payload(config, inv, lines, contact)
    en1_request = {
        'document_type': 'invoice',
        'invoice_id': inv.id,
        'invoice_number': inv.number,
        'contact_id': contact.id,
        'lines_count': len(lines),
    }
    doc = ElectronicInvoiceDocument(
        organization_id=int(organization_id),
        invoice_id=int(inv.id),
        provider=config.provider,
        environment=config.environment,
        document_type='invoice',
        internal_reference=inv.number,
        source_model='invoice',
        source_id=int(inv.id),
        customer_name=fiscal_display_name(contact) if isinstance(contact, Contact) else display_name(contact),
        customer_tax_id=(getattr(contact, 'tax_id', None) or '').strip() or None,
        customer_email=fe_email,
        subtotal=Decimal(str(inv.total or 0)),
        tax_total=Decimal(str(inv.tax_total or 0)),
        discount_total=Decimal('0'),
        total=Decimal(str(inv.grand_total or 0)),
        currency=getattr(inv, 'currency', None) or config.default_currency or 'USD',
        status='pending',
        request_payload=_json_dump(en1_request),
    )
    db.session.add(doc)
    db.session.flush()
    adapter = _adapter_for(config)
    _log_event(
        organization_id,
        'emit_invoice',
        document_id=doc.id,
        message=f'Emisión FE factura {inv.number}',
        request_payload=pac_payload,
    )
    try:
        result = adapter.emit_invoice(doc, pac_payload)
    except Exception as exc:
        doc.status = 'error'
        doc.error_message = str(exc)
        _log_event(organization_id, 'error', document_id=doc.id, message=str(exc))
        db.session.commit()
        raise
    _apply_pac_result(doc, result)
    _log_event(
        organization_id,
        'emit_invoice',
        document_id=doc.id,
        message=doc.authorization_message,
        http_status=result.get('http_status'),
        response_payload=result.get('raw_response'),
    )
    db.session.commit()
    return doc


def document_to_dict(doc: ElectronicInvoiceDocument, *, include_payloads: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {
        'id': doc.id,
        'invoice_id': getattr(doc, 'invoice_id', None),
        'organization_id': doc.organization_id,
        'provider': doc.provider,
        'environment': doc.environment,
        'document_type': doc.document_type,
        'internal_reference': doc.internal_reference,
        'source_model': doc.source_model,
        'source_id': doc.source_id,
        'customer_name': doc.customer_name,
        'customer_tax_id': doc.customer_tax_id,
        'customer_email': doc.customer_email,
        'subtotal': float(doc.subtotal or 0),
        'tax_total': float(doc.tax_total or 0),
        'total': float(doc.total or 0),
        'currency': doc.currency,
        'status': doc.status,
        'cufe': doc.cufe,
        'pac_reference': doc.pac_reference,
        'authorization_message': doc.authorization_message,
        'error_message': doc.error_message,
        'retry_count': doc.retry_count,
        'created_at': doc.created_at.isoformat() if doc.created_at else None,
        'accepted_at': doc.accepted_at.isoformat() if doc.accepted_at else None,
    }
    if include_payloads:
        out['request_payload'] = _json_load(doc.request_payload)
        out['response_payload'] = _json_load(doc.response_payload)
    return out
