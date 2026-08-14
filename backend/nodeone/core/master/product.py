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


def _optional_float(value: Any) -> float | None:
    if value is None or str(value).strip() == '':
        return None
    return float(value)


def _optional_uom(value: Any, *, default: str | None = None, max_len: int = 16) -> str | None:
    raw = (str(value).strip()[:max_len] if value is not None and str(value).strip() else None)
    return raw if raw else default


def product_to_dto(row: CoreProduct) -> ProductDTO:
    pack = getattr(row, 'pack_factor', None)
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
        barcode=str(row.barcode) if getattr(row, 'barcode', None) else None,
        cost_price=(float(row.cost_price) if getattr(row, 'cost_price', None) is not None else None),
        min_stock=(float(row.min_stock) if getattr(row, 'min_stock', None) is not None else None),
        max_stock=(float(row.max_stock) if getattr(row, 'max_stock', None) is not None else None),
        category=str(row.category) if getattr(row, 'category', None) else None,
        fiscal_category=(
            str(row.fiscal_category) if getattr(row, 'fiscal_category', None) else None
        ),
        image_url=str(row.image_url) if getattr(row, 'image_url', None) else None,
        uom=(str(row.uom).strip() if getattr(row, 'uom', None) else 'und') or 'und',
        purchase_uom=(str(row.purchase_uom).strip() if getattr(row, 'purchase_uom', None) else None) or None,
        pack_factor=(float(pack) if pack is not None else 1.0),
    )


class CoreProductService:
    @staticmethod
    def search(
        organization_id: int,
        *,
        query: str | None = None,
        product_type: str | None = None,
        status: str | None = None,
        tracks_inventory: bool | None = None,
        limit: int = 50,
    ) -> list[ProductDTO]:
        from sqlalchemy import or_

        q = CoreProduct.query.filter_by(organization_id=int(organization_id))
        if product_type:
            q = q.filter_by(product_type=(product_type or '').strip().lower())
        if status:
            q = q.filter_by(status=(status or '').strip().lower())
        if tracks_inventory is not None:
            q = q.filter_by(tracks_inventory=bool(tracks_inventory))
        needle = (query or '').strip()
        if needle:
            like = f'%{needle}%'
            q = q.filter(
                or_(
                    CoreProduct.name.ilike(like),
                    CoreProduct.product_ref.ilike(like),
                    CoreProduct.barcode.ilike(like),
                )
            )
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

        from nodeone.modules.eposone.fiscal_categories import (
            FISCAL_CATEGORY_DEFAULT,
            normalize_fiscal_category,
        )

        fiscal_raw = data.get('fiscal_category')
        fiscal_cat = normalize_fiscal_category(
            str(fiscal_raw) if fiscal_raw is not None else None
        )
        if fiscal_raw is not None and str(fiscal_raw).strip() and fiscal_cat is None:
            raise MasterDataError('invalid_fiscal_category')
        if fiscal_cat is None:
            fiscal_cat = FISCAL_CATEGORY_DEFAULT

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
            barcode=(str(data.get('barcode')).strip()[:64] if data.get('barcode') else None),
            cost_price=_optional_float(data.get('cost_price')),
            min_stock=_optional_float(data.get('min_stock')),
            max_stock=_optional_float(data.get('max_stock')),
            category=(str(data.get('category')).strip()[:120] if data.get('category') else None),
            fiscal_category=fiscal_cat,
            image_url=(str(data.get('image_url')).strip()[:500] if data.get('image_url') else None),
            uom=_optional_uom(data.get('uom'), default='und') or 'und',
            purchase_uom=_optional_uom(data.get('purchase_uom')),
            pack_factor=(
                float(data['pack_factor'])
                if data.get('pack_factor') is not None and str(data.get('pack_factor')).strip() != ''
                else 1.0
            ),
        )
        db.session.add(row)
        db.session.commit()
        return product_to_dto(row)

    @staticmethod
    def has_operational_usage(organization_id: int, product_ref: str) -> bool:
        """True si hay stock, movimientos o líneas de pedido con este product_ref."""
        from models.commercial_core import (
            CoreCommercialOrder,
            CoreCommercialOrderLine,
            CoreStockBalance,
            CoreStockMovement,
        )

        oid = int(organization_id)
        ref = (product_ref or '').strip()
        if not ref:
            return False
        if CoreStockMovement.query.filter_by(organization_id=oid, product_ref=ref).first() is not None:
            return True
        if CoreStockBalance.query.filter_by(organization_id=oid, product_ref=ref).first() is not None:
            return True
        line = (
            CoreCommercialOrderLine.query.join(
                CoreCommercialOrder,
                CoreCommercialOrderLine.order_id == CoreCommercialOrder.id,
            )
            .filter(
                CoreCommercialOrder.organization_id == oid,
                CoreCommercialOrderLine.product_ref == ref,
            )
            .first()
        )
        return line is not None

    @staticmethod
    def update(organization_id: int, product_ref: str, data: dict[str, Any]) -> ProductDTO:
        from app import db

        oid = int(organization_id)
        ref = (product_ref or '').strip()
        row = CoreProduct.query.filter_by(organization_id=oid, product_ref=ref).first()
        if row is None:
            raise MasterDataError('product_not_found')

        if 'name' in data and data.get('name') is not None:
            name = (str(data.get('name') or '')).strip()
            if not name:
                raise MasterDataError('name_required')
            row.name = name
        if 'description' in data:
            desc = data.get('description')
            row.description = (str(desc).strip()[:5000] if desc else None)
        if 'product_type' in data and data.get('product_type') is not None:
            ptype = (str(data.get('product_type') or '')).strip().lower()
            if ptype not in PRODUCT_TYPES:
                raise MasterDataError(f'invalid_product_type:{ptype}')
            row.product_type = ptype
        if 'status' in data and data.get('status') is not None:
            status = (str(data.get('status') or '')).strip().lower()
            if status not in PRODUCT_STATUSES:
                raise MasterDataError(f'invalid_status:{status}')
            row.status = status
        if 'unit_price' in data and data.get('unit_price') is not None:
            row.unit_price = float(data.get('unit_price') or 0)
        if 'currency' in data and data.get('currency') is not None:
            row.currency = str(data.get('currency') or 'USD')[:8]
        if 'tracks_inventory' in data:
            row.tracks_inventory = bool(data.get('tracks_inventory'))
        if 'barcode' in data:
            raw = data.get('barcode')
            row.barcode = (str(raw).strip()[:64] if raw else None)
        if 'cost_price' in data:
            row.cost_price = _optional_float(data.get('cost_price'))
        if 'min_stock' in data:
            row.min_stock = _optional_float(data.get('min_stock'))
        if 'max_stock' in data:
            row.max_stock = _optional_float(data.get('max_stock'))
        if 'category' in data:
            raw = data.get('category')
            row.category = (str(raw).strip()[:120] if raw else None)
        if 'fiscal_category' in data:
            from nodeone.modules.eposone.fiscal_categories import normalize_fiscal_category

            raw = data.get('fiscal_category')
            if raw is None or str(raw).strip() == '':
                row.fiscal_category = None
            else:
                fiscal_cat = normalize_fiscal_category(str(raw))
                if fiscal_cat is None:
                    raise MasterDataError('invalid_fiscal_category')
                row.fiscal_category = fiscal_cat
        if 'image_url' in data:
            raw = data.get('image_url')
            row.image_url = (str(raw).strip()[:500] if raw else None)
        if 'uom' in data:
            row.uom = _optional_uom(data.get('uom'), default='und') or 'und'
        if 'purchase_uom' in data:
            row.purchase_uom = _optional_uom(data.get('purchase_uom'))
        if 'pack_factor' in data:
            raw = data.get('pack_factor')
            row.pack_factor = (
                float(raw) if raw is not None and str(raw).strip() != '' else 1.0
            )

        db.session.commit()
        return product_to_dto(row)

    @staticmethod
    def deactivate(organization_id: int, product_ref: str) -> ProductDTO:
        return CoreProductService.update(
            int(organization_id),
            product_ref,
            {'status': 'inactive'},
        )

    @staticmethod
    def delete(organization_id: int, product_ref: str) -> None:
        from app import db

        oid = int(organization_id)
        ref = (product_ref or '').strip()
        row = CoreProduct.query.filter_by(organization_id=oid, product_ref=ref).first()
        if row is None:
            raise MasterDataError('product_not_found')
        if CoreProductService.has_operational_usage(oid, ref):
            raise MasterDataError('product_has_movements')
        db.session.delete(row)
        db.session.commit()

