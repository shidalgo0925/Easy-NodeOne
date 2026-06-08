from __future__ import annotations

"""Helpers para métodos de pago con validación manual (wire, Yappy, Banco General)."""

from models.payments import PaymentConfig
from nodeone.services.organization_payment_methods import (
    MANUAL_VALIDATION_METHOD_KEYS,
    METHOD_CATALOG,
    get_method_row,
)
from nodeone.services.yappy_manual_status import is_pending_receipt


def is_manual_validation_method(payment_method: str | None) -> bool:
    return (payment_method or '').strip() in MANUAL_VALIDATION_METHOD_KEYS


def method_display_label(payment_method: str | None) -> str:
    key = (payment_method or '').strip()
    meta = METHOD_CATALOG.get(key) or {}
    return meta.get('label') or key.replace('_', ' ').title() or 'Pago manual'


def method_requires_receipt(organization_id: int, payment_method: str | None) -> bool:
    key = (payment_method or '').strip()
    if not is_manual_validation_method(key):
        return False
    if key == 'yappy_manual':
        pcfg = PaymentConfig.get_active_config(organization_id=int(organization_id))
        if pcfg is None:
            return True
        return bool(getattr(pcfg, 'yappy_requires_receipt', True))
    row = get_method_row(int(organization_id), key)
    if row is not None:
        return bool(row.requires_receipt)
    meta = METHOD_CATALOG.get(key) or {}
    return bool(meta.get('requires_receipt', True))


def is_awaiting_receipt_upload(status: str | None) -> bool:
    """True si el usuario aún puede (o debe) adjuntar comprobante."""
    s = (status or '').strip()
    if is_pending_receipt(s):
        return True
    # Legacy: checkout wire/manual usaba status «pending» antes de pending_receipt.
    return s == 'pending'
