"""CoreProductService — catálogo maestro (Etapa 10d)."""

from __future__ import annotations

from typing import Any

from models.core_master import CoreProduct
from nodeone.core.master.constants import (
    PRODUCT_STATUS_ACTIVE,
    PRODUCT_STATUSES,
    PRODUCT_TYPES,
    MasterDataError,
)
from nodeone.core.master.dtos import ProductDTO


def product_to_dto(row: CoreProduct) -> ProductDTO:
    return ProductDTO(
        id=int(row.id),
        organization_id=int(row.organization_id),
        product_ref=str(row.product_ref),
        name=str(row.name),
        product_type=str(row.product_type),
        status=str(row.status),
        tracks_inventory=bool(row.tracks_inventory),
        unit_price=float(row.unit_price or 0),
        currency=str(row.currency or 'USD'),
        description=str(row.description) if row.description else None,
        source_app_id=str(row.source_app_id) if row.source_app_id else None,
    )


class CoreProductService:
    @staticmethod
    def search(
        organization_id: int,
        *,
        query: str | None = None,
        product_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[ProductDTO]:
        from sqlalchemy import or_

        q = CoreProduct.query.filter_by(organization_id=int(organization_id))
        if product_type:
            q = q.filter_by(product_type=(product_type or '').strip().lower())
        if status:
            q = q.filter_by(status=(status or '').strip().lower())
        needle = (query or '').strip()
        if needle:
            like = f'%{needle}%'
            q = q.filter(or_(CoreProduct.name.ilike(like), CoreProduct.product_ref.ilike(like)))
        rows = q.order_by(CoreProduct.name.asc(), CoreProduct.id.asc()).limit(max(1, int(limit))).all()
        return [product_to_dto(row) for row in rows]

    @staticmethod
    def get_by_ref(organization_id: int, product_ref: str) -> ProductDTO | None:
        ref = (product_ref or '').strip()
        if not ref:
            return None
        row = CoreProduct.query.filter_by(organization_id=int(organization_id), product_ref=ref).first()
        return product_to_dto(row) if row is not None else None

    @staticmethod
    def create(organization_id: int, data: dict[str, Any]) -> ProductDTO:
        from app import db

        ref = (str(data.get('product_ref') or '')).strip()
        name = (str(data.get('name') or '')).strip()
        ptype = (str(data.get('product_type') or 'good')).strip().lower()
        status = (str(data.get('status') or PRODUCT_STATUS_ACTIVE)).strip().lower()
        if not ref:
            raise MasterDataError('product_ref_required')
        if not name:
            raise MasterDataError('name_required')
        if ptype not in PRODUCT_TYPES:
            raise MasterDataError(f'invalid_product_type:{ptype}')
        if status not in PRODUCT_STATUSES:
            raise MasterDataError(f'invalid_status:{status}')

        if CoreProduct.query.filter_by(organization_id=int(organization_id), product_ref=ref).first():
            raise MasterDataError('product_ref_exists')

        row = CoreProduct(
            organization_id=int(organization_id),
            product_ref=ref,
            name=name,
            description=(str(data.get('description')).strip()[:5000] if data.get('description') else None),
            product_type=ptype,
            tracks_inventory=bool(data.get('tracks_inventory')),
            status=status,
            unit_price=float(data.get('unit_price') or 0),
            currency=str(data.get('currency') or 'USD')[:8],
            source_app_id=(str(data.get('source_app_id') or '').strip().lower() or None),
        )
        db.session.add(row)
        db.session.commit()
        return product_to_dto(row)
