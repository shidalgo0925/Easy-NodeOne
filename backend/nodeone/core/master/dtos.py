"""DTOs modelo maestro Core — Etapa 10b."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class OrgUnitDTO:
    id: int
    organization_id: int
    unit_ref: str
    name: str
    unit_type: str
    status: str
    parent_id: int | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'unit_ref': self.unit_ref,
            'name': self.name,
            'unit_type': self.unit_type,
            'status': self.status,
            'parent_id': self.parent_id,
            'notes': self.notes,
        }


@dataclass
class ProductDTO:
    id: int
    organization_id: int
    product_ref: str
    name: str
    product_type: str
    status: str
    tracks_inventory: bool = False
    unit_price: float = 0.0
    currency: str = 'USD'
    description: str | None = None
    source_app_id: str | None = None
    barcode: str | None = None
    cost_price: float | None = None
    min_stock: float | None = None
    max_stock: float | None = None
    category: str | None = None
    image_url: str | None = None
    uom: str | None = 'und'
    purchase_uom: str | None = None
    pack_factor: float | None = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'product_ref': self.product_ref,
            'name': self.name,
            'product_type': self.product_type,
            'status': self.status,
            'tracks_inventory': self.tracks_inventory,
            'unit_price': self.unit_price,
            'currency': self.currency,
            'description': self.description,
            'source_app_id': self.source_app_id,
            'barcode': self.barcode,
            'cost_price': self.cost_price,
            'min_stock': self.min_stock,
            'max_stock': self.max_stock,
            'category': self.category,
            'image_url': self.image_url,
            'uom': self.uom,
            'purchase_uom': self.purchase_uom,
            'pack_factor': self.pack_factor,
        }
