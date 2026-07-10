"""DTOs del dominio comercial — Etapa 12."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class OrderLineDTO:
    description: str
    quantity: float
    unit_price: float
    line_total: float
    product_ref: str | None = None
    line_status: str = 'pending'

    def to_dict(self) -> dict[str, Any]:
        return {
            'description': self.description,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'line_total': self.line_total,
            'product_ref': self.product_ref,
            'line_status': self.line_status,
        }


@dataclass(frozen=True)
class OrderDTO:
    id: int
    organization_id: int
    order_ref: str
    status: str
    payment_status: str
    fiscal_status: str
    contact_id: int | None
    currency: str
    subtotal: float
    tax_total: float
    grand_total: float
    amount_paid: float
    lines: tuple[OrderLineDTO, ...]
    source_app_id: str
    discount_total: float = 0.0
    promotion_ref: str | None = None
    branch_org_unit_id: int | None = None
    parent_order_id: int | None = None
    pos_terminal_id: int | None = None
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'order_ref': self.order_ref,
            'status': self.status,
            'operational_status': self.status,
            'payment_status': self.payment_status,
            'fiscal_status': self.fiscal_status,
            'contact_id': self.contact_id,
            'branch_org_unit_id': self.branch_org_unit_id,
            'parent_order_id': self.parent_order_id,
            'terminal_id': self.pos_terminal_id,
            'pos_terminal_id': self.pos_terminal_id,
            'currency': self.currency,
            'subtotal': self.subtotal,
            'tax_total': self.tax_total,
            'discount_total': self.discount_total,
            'promotion_ref': self.promotion_ref,
            'grand_total': self.grand_total,
            'amount_paid': self.amount_paid,
            'lines': [line.to_dict() for line in self.lines],
            'source_app_id': self.source_app_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


@dataclass(frozen=True)
class PaymentDTO:
    id: int
    organization_id: int
    payment_ref: str
    status: str
    payment_type: str
    amount: float
    currency: str
    order_ref: str | None = None
    refunded_amount: float = 0.0
    captured_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'payment_ref': self.payment_ref,
            'status': self.status,
            'payment_type': self.payment_type,
            'amount': self.amount,
            'refunded_amount': self.refunded_amount,
            'currency': self.currency,
            'order_ref': self.order_ref,
            'captured_at': self.captured_at.isoformat() if self.captured_at else None,
        }


@dataclass(frozen=True)
class InvoiceLineDTO:
    description: str
    quantity: float
    unit_price: float
    line_total: float
    product_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'description': self.description,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'line_total': self.line_total,
            'product_id': self.product_id,
        }


@dataclass(frozen=True)
class InvoiceDTO:
    id: int
    organization_id: int
    number: str
    status: str
    kind: str
    contact_id: int | None
    currency: str
    grand_total: float
    amount_paid: float
    lines: tuple[InvoiceLineDTO, ...]
    date: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'number': self.number,
            'status': self.status,
            'kind': self.kind,
            'contact_id': self.contact_id,
            'currency': self.currency,
            'grand_total': self.grand_total,
            'amount_paid': self.amount_paid,
            'lines': [line.to_dict() for line in self.lines],
            'date': self.date.isoformat() if self.date else None,
        }


@dataclass(frozen=True)
class DeliveryDTO:
    id: int
    organization_id: int
    order_ref: str
    status: str
    delivered_qty: float
    total_qty: float

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'order_ref': self.order_ref,
            'status': self.status,
            'delivered_qty': self.delivered_qty,
            'total_qty': self.total_qty,
        }


@dataclass(frozen=True)
class CashShiftDTO:
    id: int
    organization_id: int
    register_ref: str
    status: str
    opened_at: datetime | None
    closed_at: datetime | None
    opening_balance: float
    closing_balance: float | None
    counted_amount: float | None = None
    expected_balance: float | None = None
    cash_variance: float | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            'id': self.id,
            'organization_id': self.organization_id,
            'register_ref': self.register_ref,
            'status': self.status,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'opening_balance': self.opening_balance,
            'closing_balance': self.closing_balance,
        }
        if self.counted_amount is not None:
            data['counted_amount'] = self.counted_amount
        if self.expected_balance is not None:
            data['expected_balance'] = self.expected_balance
        if self.cash_variance is not None:
            data['cash_variance'] = self.cash_variance
        return data


@dataclass(frozen=True)
class PosTerminalDTO:
    id: int
    organization_id: int
    terminal_ref: str
    register_ref: str | None
    status: str
    device_label: str | None
    profile: str = 'fixed'
    platform: str | None = None
    device_model: str | None = None
    app_version: str | None = None
    android_version: str | None = None
    branch_ref: str | None = None
    pos_ref: str | None = None
    sync_enabled: bool = True
    last_seen_at: datetime | None = None
    created_at: datetime | None = None
    config_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'terminal_ref': self.terminal_ref,
            'device_id': self.terminal_ref,
            'register_ref': self.register_ref,
            'status': self.status,
            'device_label': self.device_label,
            'profile': self.profile,
            'platform': self.platform,
            'device_model': self.device_model,
            'app_version': self.app_version,
            'android_version': self.android_version,
            'branch_ref': self.branch_ref,
            'pos_ref': self.pos_ref,
            'assigned_pos_id': self.pos_ref,
            'sync_enabled': self.sync_enabled,
            'last_seen_at': self.last_seen_at.isoformat() if self.last_seen_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'config_version': self.config_version,
        }
