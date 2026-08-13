"""ADR-039 F2–F4 — Inventory Core (EN1).

Reutiliza ``core_org_unit`` (warehouse), ``core_stock_balance``, ``core_stock_movement``
y ``StockService``. No crea un segundo ledger. UI = F3; transfers/mínimos = F4.
"""

from __future__ import annotations

import json
from typing import Any

from nodeone.core.commerce.constants import (
    STOCK_MOVEMENT_ADJUST,
    STOCK_MOVEMENT_DEDUCT,
    STOCK_MOVEMENT_RETURN,
)
from nodeone.core.commerce.stock import StockService, StockValidationError
from nodeone.core.master.constants import ORG_UNIT_TYPE_WAREHOUSE, MasterDataError
from nodeone.core.master.org_unit import OrgUnitService
from nodeone.core.platform.module_registry import is_module_enabled

# ADR-039 §14
MOVEMENT_KINDS = frozenset(
    {
        'OPENING',
        'RECEIPT',
        'SALE',
        'RETURN',
        'ADJUSTMENT_IN',
        'ADJUSTMENT_OUT',
        'TRANSFER_IN',
        'TRANSFER_OUT',
        'REVERSAL',
    }
)

ADJUSTMENT_REASONS = frozenset(
    {
        'damage',
        'loss',
        'physical_count',
        'error',
        'expiry',
        'other',
    }
)

STOCK_POLICY_ALLOW = 'ALLOW_NEGATIVE'
STOCK_POLICY_WARN = 'WARN_NEGATIVE'
STOCK_POLICY_BLOCK = 'BLOCK_NEGATIVE'
STOCK_POLICIES = frozenset({STOCK_POLICY_ALLOW, STOCK_POLICY_WARN, STOCK_POLICY_BLOCK})

DEFAULT_WAREHOUSE_REF = 'main'
DEFAULT_WAREHOUSE_NAME = 'Almacén principal'


class InventoryError(ValueError):
    pass


def _assert_inventory_module(organization_id: int) -> None:
    if not is_module_enabled(int(organization_id), 'inventory'):
        raise InventoryError('inventory_module_disabled')
    if not is_module_enabled(int(organization_id), 'products'):
        raise InventoryError('products_module_required')


def get_stock_policy(organization_id: int) -> str:
    from models.module_registry import OrganizationModule

    row = OrganizationModule.query.filter_by(
        organization_id=int(organization_id), module_key='inventory'
    ).first()
    if row is None or not row.config_json:
        return STOCK_POLICY_ALLOW
    try:
        data = json.loads(row.config_json)
    except (TypeError, ValueError, json.JSONDecodeError):
        return STOCK_POLICY_ALLOW
    pol = str(data.get('stock_policy') or STOCK_POLICY_ALLOW).strip().upper()
    return pol if pol in STOCK_POLICIES else STOCK_POLICY_ALLOW


def set_stock_policy(organization_id: int, policy: str) -> str:
    from models.module_registry import OrganizationModule
    from nodeone.core.db import db

    pol = (policy or '').strip().upper()
    if pol not in STOCK_POLICIES:
        raise InventoryError(f'invalid_stock_policy:{pol}')
    row = OrganizationModule.query.filter_by(
        organization_id=int(organization_id), module_key='inventory'
    ).first()
    if row is None:
        raise InventoryError('inventory_org_module_missing')
    cfg: dict[str, Any] = {}
    if row.config_json:
        try:
            cfg = json.loads(row.config_json) or {}
        except (TypeError, ValueError, json.JSONDecodeError):
            cfg = {}
    cfg['stock_policy'] = pol
    row.config_json = json.dumps(cfg, ensure_ascii=False)
    db.session.commit()
    return pol


def ensure_default_warehouse(organization_id: int) -> dict[str, Any]:
    """P0: un almacén principal por org (multi-warehouse ready)."""
    oid = int(organization_id)
    existing = OrgUnitService.list_units(oid, unit_type=ORG_UNIT_TYPE_WAREHOUSE, status='active')
    if existing:
        unit = existing[0]
        return {'id': unit.id, 'unit_ref': unit.unit_ref, 'name': unit.name, 'created': False}
    try:
        unit = OrgUnitService.create(
            oid,
            unit_ref=DEFAULT_WAREHOUSE_REF,
            name=DEFAULT_WAREHOUSE_NAME,
            unit_type=ORG_UNIT_TYPE_WAREHOUSE,
            notes='ADR-039 F2 default warehouse',
        )
    except MasterDataError as e:
        # Race / already exists
        if 'unit_ref_exists' in str(e):
            existing = OrgUnitService.list_units(oid, unit_type=ORG_UNIT_TYPE_WAREHOUSE)
            if existing:
                unit = existing[0]
                return {'id': unit.id, 'unit_ref': unit.unit_ref, 'name': unit.name, 'created': False}
        raise InventoryError(str(e)) from e
    return {'id': unit.id, 'unit_ref': unit.unit_ref, 'name': unit.name, 'created': True}


def list_warehouses(organization_id: int) -> list[dict[str, Any]]:
    units = OrgUnitService.list_units(int(organization_id), unit_type=ORG_UNIT_TYPE_WAREHOUSE)
    return [
        {'id': u.id, 'unit_ref': u.unit_ref, 'name': u.name, 'status': u.status}
        for u in units
    ]


def _engine_for_kind(kind: str, quantity: float) -> tuple[str, float]:
    """Map ADR-039 kind → StockService movement_type + signed/abs qty."""
    k = kind.strip().upper()
    qty = abs(float(quantity or 0))
    if k in ('OPENING', 'RECEIPT', 'ADJUSTMENT_IN', 'TRANSFER_IN'):
        return STOCK_MOVEMENT_ADJUST, qty
    if k == 'RETURN':
        return STOCK_MOVEMENT_RETURN, qty
    if k in ('SALE', 'TRANSFER_OUT'):
        return STOCK_MOVEMENT_DEDUCT, qty
    if k == 'ADJUSTMENT_OUT':
        return STOCK_MOVEMENT_ADJUST, -qty
    if k == 'REVERSAL':
        # Caller passes signed quantity (counter-movement).
        return STOCK_MOVEMENT_ADJUST, float(quantity or 0)
    raise InventoryError(f'invalid_movement_kind:{k}')


def _notes_payload(
    *,
    kind: str,
    reason: str | None,
    source_system: str,
    extra: str | None = None,
) -> str:
    parts = [f'kind={kind}', f'source_system={source_system}']
    if reason:
        parts.append(f'reason={reason}')
    if extra:
        parts.append(extra.strip()[:200])
    return ';'.join(parts)[:500]


def record_movement(
    organization_id: int,
    *,
    product_ref: str,
    kind: str,
    quantity: float,
    warehouse_org_unit_id: int | None = None,
    reason: str | None = None,
    source_system: str = 'EN1',
    source_event_id: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Registra movimiento; stock = consecuencia. Idempotente si source_event_id."""
    _assert_inventory_module(organization_id)
    oid = int(organization_id)
    k = (kind or '').strip().upper()
    if k not in MOVEMENT_KINDS:
        raise InventoryError(f'invalid_movement_kind:{k}')
    if reason and reason.strip().lower() not in ADJUSTMENT_REASONS:
        raise InventoryError(f'invalid_adjustment_reason:{reason}')
    if k in ('ADJUSTMENT_IN', 'ADJUSTMENT_OUT') and not (reason or '').strip():
        raise InventoryError('adjustment_reason_required')

    wh = warehouse_org_unit_id
    if wh is None:
        wh = int(ensure_default_warehouse(oid)['id'])

    engine_type, engine_qty = _engine_for_kind(k, quantity)
    if engine_qty == 0:
        raise InventoryError('quantity_required')

    policy = get_stock_policy(oid)
    allow_negative = policy != STOCK_POLICY_BLOCK

    src = (source_system or 'EN1').strip()[:32] or 'EN1'
    idem = None
    if source_event_id:
        idem = f'{src}:{(source_event_id or "").strip()}'[:128]

    note = _notes_payload(
        kind=k,
        reason=(reason or '').strip().lower() or None,
        source_system=src,
        extra=notes,
    )

    try:
        result = StockService.apply_movement(
            oid,
            warehouse_org_unit_id=int(wh),
            product_ref=product_ref,
            movement_type=engine_type,
            quantity=engine_qty,
            idempotency_key=idem,
            notes=note,
            allow_negative=allow_negative,
        )
    except StockValidationError as e:
        raise InventoryError(str(e)) from e

    if result.get('status') == 'skipped' and result.get('reason') == 'already_applied':
        return {'status': 'already_processed', 'kind': k, 'product_ref': product_ref}

    if result.get('status') != 'applied':
        raise InventoryError(str(result.get('reason') or 'movement_failed'))

    bal = StockService.list_balances(oid, warehouse_org_unit_id=int(wh), product_ref=product_ref, limit=1)
    on_hand = bal[0].quantity_on_hand if bal else None
    return {
        'status': 'applied',
        'kind': k,
        'product_ref': product_ref,
        'quantity': float(quantity),
        'engine_movement': engine_type,
        'warehouse_org_unit_id': int(wh),
        'quantity_on_hand': on_hand,
        'stock_policy': policy,
        'source_system': src,
        'source_event_id': source_event_id,
    }


def _delta_for_engine(movement_type: str, quantity: float) -> float:
    mt = (movement_type or '').strip().lower()
    q = float(quantity or 0)
    if mt in (STOCK_MOVEMENT_RETURN,):
        return abs(q)
    if mt == STOCK_MOVEMENT_DEDUCT:
        return -abs(q)
    if mt == STOCK_MOVEMENT_ADJUST:
        return q  # signed
    return 0.0


def kardex(
    organization_id: int,
    product_ref: str,
    *,
    warehouse_org_unit_id: int | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Kardex cronológico con saldo corrido (coherente con ledger)."""
    oid = int(organization_id)
    wh = warehouse_org_unit_id
    if wh is None:
        wh = int(ensure_default_warehouse(oid)['id'])
    # list_movements is newest-first
    moves = StockService.list_movements(
        oid,
        warehouse_org_unit_id=int(wh),
        product_ref=product_ref,
        limit=max(1, min(int(limit), 500)),
    )
    chrono = list(reversed(moves))
    saldo = 0.0
    rows: list[dict[str, Any]] = []
    for m in chrono:
        delta = _delta_for_engine(m.movement_type, m.quantity)
        entrada = delta if delta > 0 else 0.0
        salida = -delta if delta < 0 else 0.0
        saldo = round(saldo + delta, 4)
        kind = None
        if m.notes and 'kind=' in m.notes:
            for part in m.notes.split(';'):
                if part.startswith('kind='):
                    kind = part.split('=', 1)[1]
        rows.append(
            {
                'id': m.id,
                'created_at': m.created_at,
                'movement_type': m.movement_type,
                'kind': kind,
                'entrada': entrada,
                'salida': salida,
                'saldo': saldo,
                'notes': m.notes,
                'order_ref': m.order_ref,
            }
        )
    return rows


def get_on_hand(
    organization_id: int,
    product_ref: str,
    *,
    warehouse_org_unit_id: int | None = None,
) -> float:
    oid = int(organization_id)
    wh = warehouse_org_unit_id
    if wh is None:
        wh = int(ensure_default_warehouse(oid)['id'])
    bals = StockService.list_balances(oid, warehouse_org_unit_id=int(wh), product_ref=product_ref, limit=1)
    return float(bals[0].quantity_on_hand) if bals else 0.0


def create_warehouse(
    organization_id: int,
    *,
    unit_ref: str,
    name: str,
) -> dict[str, Any]:
    """Crea almacén adicional (F4 transfers)."""
    _assert_inventory_module(organization_id)
    oid = int(organization_id)
    ref = (unit_ref or '').strip()
    label = (name or '').strip()
    if not ref or not label:
        raise InventoryError('warehouse_ref_and_name_required')
    try:
        unit = OrgUnitService.create(
            oid,
            unit_ref=ref,
            name=label,
            unit_type=ORG_UNIT_TYPE_WAREHOUSE,
            notes='ADR-039 F4 warehouse',
        )
    except MasterDataError as e:
        raise InventoryError(str(e)) from e
    return {'id': unit.id, 'unit_ref': unit.unit_ref, 'name': unit.name, 'status': unit.status}


def transfer(
    organization_id: int,
    *,
    product_ref: str,
    quantity: float,
    from_warehouse_org_unit_id: int,
    to_warehouse_org_unit_id: int,
    notes: str | None = None,
    source_system: str = 'EN1',
    source_event_id: str | None = None,
) -> dict[str, Any]:
    """TRANSFER_OUT + TRANSFER_IN con compensación si falla el ingreso."""
    import uuid

    _assert_inventory_module(organization_id)
    oid = int(organization_id)
    src = int(from_warehouse_org_unit_id)
    dst = int(to_warehouse_org_unit_id)
    if src == dst:
        raise InventoryError('transfer_same_warehouse')
    qty = abs(float(quantity or 0))
    if qty <= 0:
        raise InventoryError('quantity_required')

    warehouses = {int(w['id']) for w in list_warehouses(oid)}
    if src not in warehouses or dst not in warehouses:
        raise InventoryError('invalid_warehouse')

    transfer_id = (source_event_id or '').strip() or f'txfer-{uuid.uuid4().hex[:16]}'
    out_event = f'{transfer_id}:out'
    in_event = f'{transfer_id}:in'
    src_sys = (source_system or 'EN1').strip()[:32] or 'EN1'
    note = (notes or '').strip() or None

    out_res = record_movement(
        oid,
        product_ref=product_ref,
        kind='TRANSFER_OUT',
        quantity=qty,
        warehouse_org_unit_id=src,
        notes=note,
        source_system=src_sys,
        source_event_id=out_event,
    )
    try:
        in_res = record_movement(
            oid,
            product_ref=product_ref,
            kind='TRANSFER_IN',
            quantity=qty,
            warehouse_org_unit_id=dst,
            notes=note,
            source_system=src_sys,
            source_event_id=in_event,
        )
    except InventoryError:
        if out_res.get('status') == 'applied':
            record_movement(
                oid,
                product_ref=product_ref,
                kind='REVERSAL',
                quantity=qty,
                warehouse_org_unit_id=src,
                notes=f'transfer_compensate:{transfer_id}',
                source_system=src_sys,
                source_event_id=f'{transfer_id}:compensate',
            )
        raise

    return {
        'status': 'applied'
        if out_res.get('status') == 'applied' or in_res.get('status') == 'applied'
        else 'already_processed',
        'transfer_id': transfer_id,
        'product_ref': product_ref,
        'quantity': qty,
        'from_warehouse_org_unit_id': src,
        'to_warehouse_org_unit_id': dst,
        'out': out_res,
        'in': in_res,
        'on_hand_from': get_on_hand(oid, product_ref, warehouse_org_unit_id=src),
        'on_hand_to': get_on_hand(oid, product_ref, warehouse_org_unit_id=dst),
    }


def list_below_minimum(
    organization_id: int,
    *,
    warehouse_org_unit_id: int | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Productos STOCKABLE con min_stock definido y on_hand < mínimo (almacén)."""
    from models.core_master import CoreProduct

    _assert_inventory_module(organization_id)
    oid = int(organization_id)
    wh = warehouse_org_unit_id
    if wh is None:
        wh = int(ensure_default_warehouse(oid)['id'])

    rows = (
        CoreProduct.query.filter_by(organization_id=oid, status='active')
        .filter(CoreProduct.tracks_inventory.is_(True))
        .filter(CoreProduct.min_stock.isnot(None))
        .order_by(CoreProduct.product_ref.asc())
        .limit(max(1, min(int(limit), 500)))
        .all()
    )
    out: list[dict[str, Any]] = []
    for p in rows:
        min_q = float(p.min_stock or 0)
        if min_q < 0:
            continue
        on_hand = get_on_hand(oid, p.product_ref, warehouse_org_unit_id=int(wh))
        if on_hand < min_q:
            out.append(
                {
                    'product_ref': p.product_ref,
                    'name': p.name,
                    'min_stock': min_q,
                    'quantity_on_hand': on_hand,
                    'deficit': round(min_q - on_hand, 4),
                    'warehouse_org_unit_id': int(wh),
                }
            )
    return out
