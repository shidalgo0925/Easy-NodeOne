"""StockService — saldos y movimientos de inventario (Etapa 7 slice 14)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from models.commercial_core import CoreCommercialOrder, CoreStockBalance, CoreStockMovement
from nodeone.core.commerce.constants import (
    STOCK_MOVEMENT_ADJUST,
    STOCK_MOVEMENT_DEDUCT,
    STOCK_MOVEMENT_RELEASE,
    STOCK_MOVEMENT_RESERVE,
    STOCK_MOVEMENT_RETURN,
    STOCK_MOVEMENT_TYPES,
)
from nodeone.core.master.constants import ORG_UNIT_TYPE_WAREHOUSE, PRODUCT_STATUS_ACTIVE


class StockValidationError(ValueError):
    pass


@dataclass(frozen=True)
class StockBalanceDTO:
    id: int
    organization_id: int
    warehouse_org_unit_id: int
    product_ref: str
    quantity_on_hand: float
    quantity_reserved: float
    quantity_available: float

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'warehouse_org_unit_id': self.warehouse_org_unit_id,
            'product_ref': self.product_ref,
            'quantity_on_hand': self.quantity_on_hand,
            'quantity_reserved': self.quantity_reserved,
            'quantity_available': self.quantity_available,
        }


@dataclass(frozen=True)
class StockMovementDTO:
    id: int
    organization_id: int
    warehouse_org_unit_id: int
    product_ref: str
    movement_type: str
    quantity: float
    order_ref: str | None
    notes: str | None
    created_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'warehouse_org_unit_id': self.warehouse_org_unit_id,
            'product_ref': self.product_ref,
            'movement_type': self.movement_type,
            'quantity': self.quantity,
            'order_ref': self.order_ref,
            'notes': self.notes,
            'created_at': self.created_at,
        }


def _balance_to_dto(row: CoreStockBalance) -> StockBalanceDTO:
    on_hand = float(row.quantity_on_hand or 0)
    reserved = float(row.quantity_reserved or 0)
    return StockBalanceDTO(
        id=int(row.id),
        organization_id=int(row.organization_id),
        warehouse_org_unit_id=int(row.warehouse_org_unit_id),
        product_ref=str(row.product_ref),
        quantity_on_hand=on_hand,
        quantity_reserved=reserved,
        quantity_available=round(on_hand - reserved, 4),
    )


def _movement_to_dto(row: CoreStockMovement) -> StockMovementDTO:
    created = getattr(row, 'created_at', None)
    return StockMovementDTO(
        id=int(row.id),
        organization_id=int(row.organization_id),
        warehouse_org_unit_id=int(row.warehouse_org_unit_id),
        product_ref=str(row.product_ref),
        movement_type=str(row.movement_type),
        quantity=float(row.quantity or 0),
        order_ref=str(row.order_ref) if row.order_ref else None,
        notes=str(row.notes) if row.notes else None,
        created_at=created.isoformat(sep=' ', timespec='seconds') if created else None,
    )


class StockService:
    """Ledger de stock por bodega y product_ref."""

    @staticmethod
    def list_balances(
        organization_id: int,
        *,
        warehouse_org_unit_id: int | None = None,
        product_ref: str | None = None,
        limit: int = 100,
    ) -> list[StockBalanceDTO]:
        q = CoreStockBalance.query.filter_by(organization_id=int(organization_id))
        if warehouse_org_unit_id is not None:
            q = q.filter_by(warehouse_org_unit_id=int(warehouse_org_unit_id))
        ref = (product_ref or '').strip()
        if ref:
            q = q.filter_by(product_ref=ref)
        rows = (
            q.order_by(CoreStockBalance.product_ref.asc(), CoreStockBalance.id.asc())
            .limit(max(1, min(int(limit), 500)))
            .all()
        )
        return [_balance_to_dto(row) for row in rows]

    @staticmethod
    def list_movements(
        organization_id: int,
        *,
        warehouse_org_unit_id: int | None = None,
        product_ref: str | None = None,
        movement_type: str | None = None,
        limit: int = 100,
    ) -> list[StockMovementDTO]:
        """Kardex: movimientos más recientes primero."""
        q = CoreStockMovement.query.filter_by(organization_id=int(organization_id))
        if warehouse_org_unit_id is not None:
            q = q.filter_by(warehouse_org_unit_id=int(warehouse_org_unit_id))
        ref = (product_ref or '').strip()
        if ref:
            q = q.filter_by(product_ref=ref)
        mtype = (movement_type or '').strip().lower()
        if mtype:
            q = q.filter_by(movement_type=mtype)
        rows = (
            q.order_by(CoreStockMovement.created_at.desc(), CoreStockMovement.id.desc())
            .limit(max(1, min(int(limit), 500)))
            .all()
        )
        return [_movement_to_dto(row) for row in rows]

    @staticmethod
    def resolve_warehouse_id(organization_id: int, branch_org_unit_id: int | None) -> int | None:
        from models.core_master import CoreOrgUnit

        oid = int(organization_id)
        if branch_org_unit_id is not None:
            row = CoreOrgUnit.query.filter_by(
                organization_id=oid,
                unit_type=ORG_UNIT_TYPE_WAREHOUSE,
                parent_id=int(branch_org_unit_id),
                status='active',
            ).first()
            if row is not None:
                return int(row.id)
        row = (
            CoreOrgUnit.query.filter_by(
                organization_id=oid,
                unit_type=ORG_UNIT_TYPE_WAREHOUSE,
                status='active',
            )
            .order_by(CoreOrgUnit.id.asc())
            .first()
        )
        return int(row.id) if row is not None else None

    @staticmethod
    def apply_order_movement(
        organization_id: int,
        order_ref: str,
        movement_type: str,
    ) -> dict[str, Any]:
        movement = (movement_type or '').strip().lower()
        if movement not in STOCK_MOVEMENT_TYPES:
            return {'status': 'skipped', 'reason': 'invalid_movement'}
        if movement == STOCK_MOVEMENT_ADJUST:
            return {'status': 'skipped', 'reason': 'manual_adjust_only'}

        oid = int(organization_id)
        ref = (order_ref or '').strip()
        if not ref:
            return {'status': 'skipped', 'reason': 'order_ref_required'}

        order = CoreCommercialOrder.query.filter_by(organization_id=oid, order_ref=ref).first()
        if order is None:
            return {'status': 'skipped', 'reason': 'order_not_found'}

        warehouse_id = StockService.resolve_warehouse_id(
            oid,
            int(order.branch_org_unit_id) if order.branch_org_unit_id else None,
        )
        if warehouse_id is None:
            return {'status': 'skipped', 'reason': 'no_warehouse'}

        applied = 0
        skipped = 0
        for line in list(order.lines or []):
            product_ref = (str(line.product_ref or '')).strip()
            if not product_ref:
                skipped += 1
                continue
            qty = float(line.quantity or 0)
            if qty <= 0:
                skipped += 1
                continue
            try:
                result = StockService.apply_movement(
                    oid,
                    warehouse_org_unit_id=warehouse_id,
                    product_ref=product_ref,
                    movement_type=movement,
                    quantity=qty,
                    order_ref=ref,
                    idempotency_key=f'{ref}:{movement}:{product_ref}',
                    allow_negative=True,
                )
                if result.get('status') == 'applied':
                    applied += 1
                else:
                    skipped += 1
            except StockValidationError:
                skipped += 1
        return {'status': 'ok', 'movement': movement, 'applied': applied, 'skipped': skipped}

    @staticmethod
    def apply_movement(
        organization_id: int,
        *,
        warehouse_org_unit_id: int,
        product_ref: str,
        movement_type: str,
        quantity: float,
        order_ref: str | None = None,
        idempotency_key: str | None = None,
        notes: str | None = None,
        allow_negative: bool = False,
    ) -> dict[str, Any]:
        from app import db
        from nodeone.core.services.product import ProductService

        oid = int(organization_id)
        movement = (movement_type or '').strip().lower()
        if movement not in STOCK_MOVEMENT_TYPES:
            raise StockValidationError('invalid_movement')
        ref = (product_ref or '').strip()
        if not ref:
            raise StockValidationError('product_ref_required')
        qty = float(quantity or 0)
        if movement == STOCK_MOVEMENT_ADJUST:
            if qty == 0:
                raise StockValidationError('quantity_required')
        elif qty <= 0:
            raise StockValidationError('quantity_required')

        product = ProductService.get_by_ref(oid, ref)
        if product is None or product.status != PRODUCT_STATUS_ACTIVE:
            return {'status': 'skipped', 'reason': 'invalid_product'}
        if not product.tracks_inventory and movement != STOCK_MOVEMENT_ADJUST:
            return {'status': 'skipped', 'reason': 'tracks_inventory_disabled'}

        idem = (idempotency_key or '').strip() or None
        if idem:
            existing = CoreStockMovement.query.filter_by(organization_id=oid, idempotency_key=idem).first()
            if existing is not None:
                return {'status': 'skipped', 'reason': 'already_applied'}

        balance = StockService._get_or_create_balance(oid, int(warehouse_org_unit_id), ref)
        StockService._mutate_balance(balance, movement, qty, allow_negative=allow_negative)

        row = CoreStockMovement(
            organization_id=oid,
            warehouse_org_unit_id=int(warehouse_org_unit_id),
            product_ref=ref,
            movement_type=movement,
            quantity=qty,
            order_ref=(order_ref or '').strip()[:50] or None,
            idempotency_key=idem,
            notes=(notes or '').strip()[:500] or None,
        )
        from nodeone.modules.eposone.ops_lifecycle import stamp_test_fields

        stamp_test_fields(row, oid)
        db.session.add(row)
        db.session.commit()
        return {'status': 'applied', 'movement': movement, 'product_ref': ref, 'quantity': qty}

    @staticmethod
    def _get_or_create_balance(organization_id: int, warehouse_org_unit_id: int, product_ref: str) -> CoreStockBalance:
        from app import db

        row = CoreStockBalance.query.filter_by(
            organization_id=int(organization_id),
            warehouse_org_unit_id=int(warehouse_org_unit_id),
            product_ref=(product_ref or '').strip(),
        ).first()
        if row is not None:
            return row
        row = CoreStockBalance(
            organization_id=int(organization_id),
            warehouse_org_unit_id=int(warehouse_org_unit_id),
            product_ref=(product_ref or '').strip(),
            quantity_on_hand=0.0,
            quantity_reserved=0.0,
        )
        db.session.add(row)
        db.session.flush()
        return row

    @staticmethod
    def _mutate_balance(
        balance: CoreStockBalance,
        movement_type: str,
        quantity: float,
        *,
        allow_negative: bool = False,
    ) -> None:
        qty = float(quantity or 0)
        on_hand = float(balance.quantity_on_hand or 0)
        reserved = float(balance.quantity_reserved or 0)

        if movement_type == STOCK_MOVEMENT_RESERVE:
            available = on_hand - reserved
            if qty > available and not allow_negative:
                raise StockValidationError('insufficient_stock')
            balance.quantity_reserved = round(reserved + qty, 4)
            return

        if movement_type == STOCK_MOVEMENT_RELEASE:
            balance.quantity_reserved = round(max(0.0, reserved - qty), 4)
            return

        if movement_type == STOCK_MOVEMENT_DEDUCT:
            release_qty = min(reserved, qty)
            balance.quantity_reserved = round(reserved - release_qty, 4)
            on_hand -= qty
            if on_hand < 0 and not allow_negative:
                raise StockValidationError('insufficient_stock')
            balance.quantity_on_hand = round(on_hand, 4)
            return

        if movement_type == STOCK_MOVEMENT_RETURN:
            balance.quantity_on_hand = round(on_hand + qty, 4)
            return

        if movement_type == STOCK_MOVEMENT_ADJUST:
            on_hand += qty
            if on_hand < 0 and not allow_negative:
                raise StockValidationError('insufficient_stock')
            balance.quantity_on_hand = round(on_hand, 4)
            return

        raise StockValidationError('invalid_movement')

    @staticmethod
    def _resolve_warehouse_org_unit_id(organization_id: int, data: dict[str, Any]) -> int:
        from models.core_master import CoreOrgUnit
        from nodeone.core.services.org_unit import OrgUnitService

        oid = int(organization_id)
        if data.get('warehouse_org_unit_id') is not None:
            wh_id = int(data['warehouse_org_unit_id'])
            row = CoreOrgUnit.query.filter_by(organization_id=oid, id=wh_id).first()
            if row is None or str(row.unit_type) != ORG_UNIT_TYPE_WAREHOUSE:
                raise StockValidationError('invalid_warehouse_org_unit_id')
            return wh_id

        warehouse_ref = (str(data.get('warehouse_ref') or '')).strip()
        if warehouse_ref:
            unit = OrgUnitService.get_by_ref(oid, warehouse_ref)
            if unit is None or unit.unit_type != ORG_UNIT_TYPE_WAREHOUSE:
                raise StockValidationError('invalid_warehouse_ref')
            return int(unit.id)

        raise StockValidationError('warehouse_required')

    @staticmethod
    def record_manual_adjust(
        organization_id: int,
        data: dict[str, Any],
        *,
        source_app_id: str = 'eposone',
    ) -> StockBalanceDTO:
        from nodeone.core.commerce.authorization import CommerceAuthorizationService

        oid = int(organization_id)
        CommerceAuthorizationService.assert_supervisor(
            oid,
            data,
            action='inventory.adjust',
            source_app_id=source_app_id,
        )
        warehouse_id = StockService._resolve_warehouse_org_unit_id(oid, data)
        product_ref = (str(data.get('product_ref') or '')).strip()
        if not product_ref:
            raise StockValidationError('product_ref_required')
        qty = float(data.get('quantity') if data.get('quantity') is not None else 0)
        if qty == 0:
            raise StockValidationError('quantity_required')

        result = StockService.apply_movement(
            oid,
            warehouse_org_unit_id=warehouse_id,
            product_ref=product_ref,
            movement_type=STOCK_MOVEMENT_ADJUST,
            quantity=qty,
            idempotency_key=(str(data.get('idempotency_key') or '')).strip() or None,
            notes=data.get('notes'),
            allow_negative=bool(data.get('allow_negative')),
        )
        if result.get('status') != 'applied':
            raise StockValidationError(str(result.get('reason') or 'adjust_failed'))

        balance = CoreStockBalance.query.filter_by(
            organization_id=oid,
            warehouse_org_unit_id=warehouse_id,
            product_ref=product_ref,
        ).first()
        if balance is None:
            raise StockValidationError('balance_not_found')
        return _balance_to_dto(balance)
