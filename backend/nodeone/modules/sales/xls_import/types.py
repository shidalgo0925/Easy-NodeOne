"""Estructuras normalizadas del importador XLS de Ventas (no FE)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SalesImportLine:
    description: str
    quantity: float = 1.0
    unit_price: float = 0.0
    discount: float = 0.0
    tax_rate: float | None = None
    declared_total: float | None = None
    product_id: int | None = None
    tax_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> SalesImportLine:
        data = data or {}
        return cls(
            description=str(data.get('description') or '').strip() or 'Item',
            quantity=float(data.get('quantity') or 1),
            unit_price=float(data.get('unit_price') or 0),
            discount=float(data.get('discount') or 0),
            tax_rate=(None if data.get('tax_rate') in (None, '') else float(data.get('tax_rate'))),
            declared_total=(
                None if data.get('declared_total') in (None, '') else float(data.get('declared_total'))
            ),
            product_id=(int(data['product_id']) if data.get('product_id') else None),
            tax_id=(int(data['tax_id']) if data.get('tax_id') else None),
        )


@dataclass
class SalesImportData:
    external_number: str | None = None
    date: str | None = None
    customer: str | None = None
    tax_id: str | None = None
    dv: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    currency: str = 'USD'
    lines: list[SalesImportLine] = field(default_factory=list)
    declared_subtotal: float | None = None
    declared_tax: float | None = None
    declared_total: float | None = None
    profile: str = ''
    profile_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d['lines'] = [ln.to_dict() if hasattr(ln, 'to_dict') else ln for ln in self.lines]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> SalesImportData:
        data = data or {}
        lines = [SalesImportLine.from_dict(x) for x in (data.get('lines') or [])]
        return cls(
            external_number=(str(data['external_number']).strip() if data.get('external_number') else None),
            date=(str(data['date']).strip() if data.get('date') else None),
            customer=(str(data['customer']).strip() if data.get('customer') else None),
            tax_id=(str(data['tax_id']).strip() if data.get('tax_id') else None),
            dv=(str(data['dv']).strip() if data.get('dv') else None),
            address=(str(data['address']).strip() if data.get('address') else None),
            phone=(str(data['phone']).strip() if data.get('phone') else None),
            email=(str(data['email']).strip() if data.get('email') else None),
            currency=str(data.get('currency') or 'USD').strip() or 'USD',
            lines=lines,
            declared_subtotal=(
                None if data.get('declared_subtotal') in (None, '') else float(data.get('declared_subtotal'))
            ),
            declared_tax=(None if data.get('declared_tax') in (None, '') else float(data.get('declared_tax'))),
            declared_total=(
                None if data.get('declared_total') in (None, '') else float(data.get('declared_total'))
            ),
            profile=str(data.get('profile') or ''),
            profile_version=int(data.get('profile_version') or 1),
        )
