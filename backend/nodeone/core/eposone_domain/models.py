"""Modelos de contrato portable EPosOne V4 (Sprint 2 → tipados Python).

IDs opacos ``str``; sin ``organization_id``, ORM ni paths.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _clean(d: dict[str, Any]) -> dict[str, Any]:
    """Omit None for JSON-friendly dumps."""
    out: dict[str, Any] = {}
    for k, v in d.items():
        if v is None:
            continue
        if isinstance(v, list):
            out[k] = [
                _clean(asdict(i)) if hasattr(i, '__dataclass_fields__') else i for i in v
            ]
        elif hasattr(v, '__dataclass_fields__'):
            out[k] = _clean(asdict(v))
        else:
            out[k] = v
    return out


@dataclass(frozen=True)
class Address:
    line1: str | None = None
    city: str | None = None
    region: str | None = None
    postal_code: str | None = None


@dataclass(frozen=True)
class TaxRate:
    id: str
    name: str
    rate: float
    inclusive: bool = False


@dataclass(frozen=True)
class Branch:
    id: str
    business_id: str
    name: str
    is_default: bool = False
    address: Address | None = None


@dataclass(frozen=True)
class Register:
    id: str
    branch_id: str
    name: str
    is_default: bool = False


@dataclass(frozen=True)
class BusinessConfig:
    id: str
    name: str
    currency: str
    created_at: str
    legal_name: str | None = None
    tax_id: str | None = None
    country_code: str | None = None
    timezone: str | None = None
    address: Address | None = None
    tax_rates: tuple[TaxRate, ...] = ()
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _clean(asdict(self))


@dataclass(frozen=True)
class KitLine:
    component_product_id: str
    quantity: float


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    unit_price: float
    currency: str
    product_type: str  # simple | kit | service
    active: bool
    track_stock: bool
    created_at: str
    sku: str | None = None
    description: str | None = None
    tax_rate_id: str | None = None
    kit_lines: tuple[KitLine, ...] = ()
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _clean(asdict(self))


@dataclass(frozen=True)
class Customer:
    id: str
    display_name: str
    active: bool
    created_at: str
    email: str | None = None
    phone: str | None = None
    document_id: str | None = None
    tax_id: str | None = None
    notes: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _clean(asdict(self))


@dataclass(frozen=True)
class Employee:
    id: str
    display_name: str
    has_pin: bool
    operational_roles: tuple[str, ...]
    active: bool
    created_at: str
    email: str | None = None
    pin_hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _clean(asdict(self))


@dataclass(frozen=True)
class OrderLine:
    id: str
    description: str
    quantity: float
    unit_price: float
    line_total: float
    line_status: str
    product_id: str | None = None
    tax_rate_id: str | None = None


@dataclass(frozen=True)
class Payment:
    id: str
    order_id: str
    payment_ref: str
    status: str
    payment_type: str
    amount: float
    currency: str
    refunded_amount: float = 0.0
    captured_at: str | None = None
    idempotency_key: str | None = None


@dataclass(frozen=True)
class Order:
    id: str
    order_ref: str
    business_id: str
    branch_id: str
    operational_status: str
    payment_status: str
    fiscal_status: str
    currency: str
    subtotal: float
    tax_total: float
    discount_total: float
    grand_total: float
    amount_paid: float
    version: int
    lines: tuple[OrderLine, ...]
    created_at: str
    register_id: str | None = None
    terminal_id: str | None = None
    customer_id: str | None = None
    created_by_employee_id: str | None = None
    cashier_employee_id: str | None = None
    promotion_id: str | None = None
    parent_order_id: str | None = None
    payments: tuple[Payment, ...] = ()
    updated_at: str | None = None
    idempotency_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _clean(asdict(self))


@dataclass(frozen=True)
class CashShift:
    id: str
    register_id: str
    branch_id: str
    opened_by_employee_id: str
    status: str  # open | closed
    opening_float: float
    currency: str
    opened_at: str
    closed_by_employee_id: str | None = None
    closing_counted: float | None = None
    expected_cash: float | None = None
    closed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _clean(asdict(self))


@dataclass(frozen=True)
class InventoryBalance:
    id: str
    product_id: str
    branch_id: str
    quantity_on_hand: float
    quantity_reserved: float
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return _clean(asdict(self))


@dataclass(frozen=True)
class Promotion:
    id: str
    name: str
    active: bool
    rules: dict[str, Any] = field(default_factory=dict)
    valid_from: str | None = None
    valid_to: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _clean(asdict(self))


@dataclass(frozen=True)
class Device:
    """Terminal POS — Sprint 2 contrato + Sprint 6 (vinculo empresa/caja/sync)."""

    id: str  # UUID estable del dispositivo
    profile: str  # fixed | handheld
    name: str | None = None
    business_id: str | None = None
    branch_id: str | None = None
    register_id: str | None = None
    app_version: str | None = None
    platform: str | None = None  # android | web | ios
    device_model: str | None = None  # hardware / modelo comercial
    status: str = 'active'  # active | inactive
    sync_enabled: bool = True  # Modo Plataforma: participa en sync (§ 6.9)
    last_seen_at: str | None = None
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _clean(asdict(self))
