"""ADR-039 F6 — bridge Connected / EPosOne stock → inventory_service.

Cuando la org tiene módulos ``products``+``inventory``, los ajustes Connected y
las deducciones/devoluciones de pedido pasan por ``inventory_service`` (kinds
ADR-039 + ``source_system`` / ``source_event_id``). Si no, se conserva
``StockService`` (comportamiento previo).

No toca Flutter/EP1 ni bootstrap. Sin STG/PRD.
"""

from __future__ import annotations

from typing import Any

from nodeone.core.commerce.constants import (
    STOCK_MOVEMENT_DEDUCT,
    STOCK_MOVEMENT_RETURN,
)
from nodeone.core.commerce.stock import StockBalanceDTO, StockService, StockValidationError
from nodeone.core.platform.module_registry import is_module_enabled


def _inventory_path_enabled(organization_id: int) -> bool:
    oid = int(organization_id)
    return is_module_enabled(oid, 'inventory') and is_module_enabled(oid, 'products')


def record_connected_adjust(
    organization_id: int,
    data: dict[str, Any],
    *,
    source_app_id: str = 'eposone',
    source_system: str = 'EP1',
) -> StockBalanceDTO:
    """Ajuste manual Connected/BO: inventory_service si módulo ON; si no StockService."""
    from nodeone.core.commerce.authorization import CommerceAuthorizationService
    from nodeone.core.platform import inventory_service as inv
    from nodeone.core.platform.inventory_service import InventoryError

    oid = int(organization_id)
    CommerceAuthorizationService.assert_supervisor(
        oid,
        data,
        action='inventory.adjust',
        source_app_id=source_app_id,
    )

    if not _inventory_path_enabled(oid):
        return StockService.record_manual_adjust(
            oid, data, source_app_id=source_app_id
        )

    warehouse_id = StockService._resolve_warehouse_org_unit_id(oid, data)
    product_ref = (str(data.get('product_ref') or '')).strip()
    if not product_ref:
        raise StockValidationError('product_ref_required')
    qty = float(data.get('quantity') if data.get('quantity') is not None else 0)
    if qty == 0:
        raise StockValidationError('quantity_required')

    kind = 'ADJUSTMENT_IN' if qty > 0 else 'ADJUSTMENT_OUT'
    reason = (str(data.get('reason') or 'other')).strip().lower() or 'other'
    event_id = (
        (str(data.get('source_event_id') or '')).strip()
        or (str(data.get('idempotency_key') or '')).strip()
        or None
    )
    src = (source_system or 'EP1').strip()[:32] or 'EP1'

    try:
        result = inv.record_movement(
            oid,
            product_ref=product_ref,
            kind=kind,
            quantity=abs(qty),
            warehouse_org_unit_id=int(warehouse_id),
            reason=reason,
            notes=data.get('notes'),
            source_system=src,
            source_event_id=event_id,
        )
    except InventoryError as e:
        raise StockValidationError(str(e)) from e

    if result.get('status') not in ('applied', 'already_processed'):
        raise StockValidationError(str(result.get('status') or 'adjust_failed'))

    bals = StockService.list_balances(
        oid, warehouse_org_unit_id=int(warehouse_id), product_ref=product_ref, limit=1
    )
    if not bals:
        raise StockValidationError('balance_not_found')
    return bals[0]


def apply_connected_order_movement(
    organization_id: int,
    order_ref: str,
    movement_type: str,
    *,
    source_system: str = 'EP1',
) -> dict[str, Any]:
    """deduct/return vía inventory_service si módulo ON; resto / fallback StockService."""
    from models.commercial_core import CoreCommercialOrder
    from nodeone.core.platform import inventory_service as inv
    from nodeone.core.platform.inventory_service import InventoryError

    movement = (movement_type or '').strip().lower()
    oid = int(organization_id)
    ref = (order_ref or '').strip()

    if movement not in (STOCK_MOVEMENT_DEDUCT, STOCK_MOVEMENT_RETURN) or not _inventory_path_enabled(
        oid
    ):
        return StockService.apply_order_movement(oid, ref, movement)

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

    kind = 'SALE' if movement == STOCK_MOVEMENT_DEDUCT else 'RETURN'
    src = (source_system or 'EP1').strip()[:32] or 'EP1'
    applied = 0
    skipped = 0
    for line in list(order.lines or []):
        product_ref = (str(line.product_ref or '')).strip()
        qty = float(line.quantity or 0)
        if not product_ref or qty <= 0:
            skipped += 1
            continue
        event_id = f'{ref}:{movement}:{product_ref}'
        try:
            result = inv.record_movement(
                oid,
                product_ref=product_ref,
                kind=kind,
                quantity=qty,
                warehouse_org_unit_id=int(warehouse_id),
                notes=f'order_ref={ref}',
                source_system=src,
                source_event_id=event_id,
            )
            if result.get('status') in ('applied', 'already_processed'):
                applied += 1
            else:
                skipped += 1
        except (InventoryError, StockValidationError):
            skipped += 1
    return {
        'status': 'ok',
        'movement': movement,
        'kind': kind,
        'bridge': 'inventory_service',
        'applied': applied,
        'skipped': skipped,
    }
