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
from nodeone.modules.efactura.services.mapper import build_test_invoice_payload
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


def document_to_dict(doc: ElectronicInvoiceDocument, *, include_payloads: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {
        'id': doc.id,
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
