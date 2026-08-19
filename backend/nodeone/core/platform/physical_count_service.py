"""Toma física Connected: sesión + corte temporal + aprobación → ADJUSTMENT_*.

Algoritmo de corte (ventas no se bloquean):

1. Al iniciar se guarda ``started_at`` y ``snapshot_qty`` = on_hand en ese instante.
2. Cada línea con cantidad física guarda ``counted_at`` (captura, no el complete).
3. ``expected = snapshot_qty + Σ(movimientos con started_at < created_at ≤ counted_at)``.
4. ``difference = physical_qty - expected``.
5. COMPLETED congela expected/difference. COMPLETED no mueve stock.
6. APPROVED emite ADJUSTMENT_IN/OUT por diferencia ≠ 0, idempotente por
   ``source_event_id = physcount:{id}:{product_ref}:{IN|OUT}``.

Permisos conceptuales (no necesariamente filas RBAC aún):

* inventory.view — consultar
* inventory.count — iniciar / guardar líneas
* inventory.count.complete — completar
* inventory.count.approve — aprobar (no el mismo usuario que contó, salvo admin)
* inventory.adjust — ajustes manuales (fuera de esta sesión)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from models.core_master import CoreProduct
from models.physical_inventory import (
    COUNT_MODE_BLIND,
    COUNT_MODES,
    COUNT_STATUS_APPROVED,
    COUNT_STATUS_CANCELLED,
    COUNT_STATUS_COMPLETED,
    COUNT_STATUS_COUNTING,
    COUNT_STATUS_DRAFT,
    PhysicalInventoryCount,
    PhysicalInventoryCountLine,
)
from nodeone.core.platform.inventory_service import (
    InventoryError,
    _assert_inventory_module,
    _delta_for_engine,
    get_on_hand,
    list_warehouses,
    record_movement,
)


PERM_VIEW = 'inventory.view'
PERM_COUNT = 'inventory.count'
PERM_COMPLETE = 'inventory.count.complete'
PERM_APPROVE = 'inventory.count.approve'
PERM_ADJUST = 'inventory.adjust'


class PhysicalCountError(InventoryError):
    pass


def _utcnow() -> datetime:
    return datetime.utcnow()


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat(sep=' ', timespec='seconds')


def _stockable_products(organization_id: int) -> list[CoreProduct]:
    return (
        CoreProduct.query.filter_by(organization_id=int(organization_id), status='active')
        .filter(CoreProduct.tracks_inventory.is_(True))
        .order_by(CoreProduct.product_ref.asc())
        .all()
    )


def _assert_warehouse(organization_id: int, warehouse_org_unit_id: int) -> int:
    oid = int(organization_id)
    wh = int(warehouse_org_unit_id)
    ids = {int(w['id']) for w in list_warehouses(oid)}
    if wh not in ids:
        raise PhysicalCountError('invalid_warehouse')
    return wh


def _get_count(organization_id: int, count_id: int) -> PhysicalInventoryCount:
    row = PhysicalInventoryCount.query.filter_by(
        id=int(count_id), organization_id=int(organization_id)
    ).first()
    if row is None:
        raise PhysicalCountError('count_not_found')
    return row


def _movement_delta_between(
    organization_id: int,
    product_ref: str,
    warehouse_org_unit_id: int,
    started_at: datetime,
    counted_at: datetime,
) -> float:
    from models.commercial_core import CoreStockMovement

    rows = (
        CoreStockMovement.query.filter_by(
            organization_id=int(organization_id),
            warehouse_org_unit_id=int(warehouse_org_unit_id),
            product_ref=product_ref,
        )
        .filter(CoreStockMovement.created_at > started_at)
        .filter(CoreStockMovement.created_at <= counted_at)
        .all()
    )
    total = 0.0
    for m in rows:
        total += _delta_for_engine(m.movement_type, float(m.quantity or 0))
    return round(total, 4)


def expected_qty_for_line(count: PhysicalInventoryCount, line: PhysicalInventoryCountLine) -> float:
    counted_at = line.counted_at or count.completed_at or _utcnow()
    delta = _movement_delta_between(
        int(count.organization_id),
        str(line.product_ref),
        int(count.warehouse_org_unit_id),
        count.started_at,
        counted_at,
    )
    return round(float(line.snapshot_qty or 0) + delta, 4)


def _line_dict(line: PhysicalInventoryCountLine, *, include_theoretical: bool) -> dict[str, Any]:
    data: dict[str, Any] = {
        'id': int(line.id),
        'product_id': int(line.product_id) if line.product_id is not None else None,
        'product_ref': str(line.product_ref),
        'uom': line.uom,
        'client_line_id': line.client_line_id,
        'physical_qty': float(line.physical_qty) if line.physical_qty is not None else None,
        'notes': line.notes,
        'counted_at': _iso(line.counted_at),
    }
    if include_theoretical:
        data['snapshot_qty'] = float(line.snapshot_qty or 0)
        data['expected_qty'] = float(line.expected_qty) if line.expected_qty is not None else None
        data['difference_qty'] = (
            float(line.difference_qty) if line.difference_qty is not None else None
        )
    return data


def count_to_dict(
    count: PhysicalInventoryCount,
    *,
    include_theoretical: bool | None = None,
    include_lines: bool = True,
) -> dict[str, Any]:
    status = str(count.status)
    if include_theoretical is None:
        include_theoretical = status in (COUNT_STATUS_COMPLETED, COUNT_STATUS_APPROVED)
    payload: dict[str, Any] = {
        'id': int(count.id),
        'organization_id': int(count.organization_id),
        'warehouse_org_unit_id': int(count.warehouse_org_unit_id),
        'status': status,
        'count_mode': str(count.count_mode),
        'client_count_id': count.client_count_id,
        'created_by_user_id': count.created_by_user_id,
        'approved_by_user_id': count.approved_by_user_id,
        'source_device_id': count.source_device_id,
        'source_system': count.source_system,
        'notes': count.notes,
        'started_at': _iso(count.started_at),
        'completed_at': _iso(count.completed_at),
        'approved_at': _iso(count.approved_at),
        'created_at': _iso(count.created_at),
    }
    if include_lines:
        payload['lines'] = [
            _line_dict(ln, include_theoretical=include_theoretical) for ln in list(count.lines or [])
        ]
    return payload


def list_location_products(
    organization_id: int,
    warehouse_org_unit_id: int,
    *,
    blind: bool = True,
) -> list[dict[str, Any]]:
    """Catálogo contable de la ubicación. En BLIND no incluye saldo teórico."""
    _assert_inventory_module(organization_id)
    oid = int(organization_id)
    wh = _assert_warehouse(oid, warehouse_org_unit_id)
    out: list[dict[str, Any]] = []
    for p in _stockable_products(oid):
        row: dict[str, Any] = {
            'product_id': int(p.id),
            'product_ref': str(p.product_ref),
            'name': str(p.name),
            'uom': p.uom or 'und',
            'warehouse_org_unit_id': wh,
        }
        if not blind:
            row['quantity_on_hand'] = get_on_hand(oid, p.product_ref, warehouse_org_unit_id=wh)
        out.append(row)
    return out


def start_count(
    organization_id: int,
    *,
    warehouse_org_unit_id: int,
    client_count_id: str | None = None,
    created_by_user_id: int | None = None,
    source_device_id: int | None = None,
    count_mode: str = COUNT_MODE_BLIND,
    notes: str | None = None,
    source_system: str = 'EP1',
) -> dict[str, Any]:
    from sqlalchemy.exc import IntegrityError

    from nodeone.core.db import db

    _assert_inventory_module(organization_id)
    oid = int(organization_id)
    wh = _assert_warehouse(oid, warehouse_org_unit_id)
    mode = (count_mode or COUNT_MODE_BLIND).strip().upper()
    if mode not in COUNT_MODES:
        raise PhysicalCountError(f'invalid_count_mode:{mode}')
    client_id = (client_count_id or '').strip() or None
    if client_id:
        existing = PhysicalInventoryCount.query.filter_by(
            organization_id=oid, client_count_id=client_id
        ).first()
        if existing is not None:
            return count_to_dict(existing, include_theoretical=False)
    else:
        open_row = (
            PhysicalInventoryCount.query.filter_by(
                organization_id=oid,
                warehouse_org_unit_id=wh,
                status=COUNT_STATUS_COUNTING,
            )
            .order_by(PhysicalInventoryCount.id.desc())
            .first()
        )
        if open_row is not None:
            return count_to_dict(open_row, include_theoretical=False)

    started_at = _utcnow()
    count = PhysicalInventoryCount(
        organization_id=oid,
        warehouse_org_unit_id=wh,
        status=COUNT_STATUS_COUNTING,
        count_mode=mode,
        client_count_id=client_id,
        created_by_user_id=int(created_by_user_id) if created_by_user_id else None,
        source_device_id=int(source_device_id) if source_device_id else None,
        source_system=(source_system or 'EP1').strip()[:32] or 'EP1',
        notes=(notes or '').strip() or None,
        started_at=started_at,
    )
    try:
        db.session.add(count)
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        if client_id:
            existing = PhysicalInventoryCount.query.filter_by(
                organization_id=oid, client_count_id=client_id
            ).first()
            if existing is not None:
                return count_to_dict(existing, include_theoretical=False)
        raise PhysicalCountError('count_create_conflict') from None

    for p in _stockable_products(oid):
        snap = get_on_hand(oid, p.product_ref, warehouse_org_unit_id=wh)
        db.session.add(
            PhysicalInventoryCountLine(
                count_id=int(count.id),
                organization_id=oid,
                product_id=int(p.id),
                product_ref=str(p.product_ref),
                uom=p.uom or 'und',
                snapshot_qty=float(snap),
            )
        )
    db.session.commit()
    db.session.refresh(count)
    return count_to_dict(count, include_theoretical=False)


def upsert_lines(
    organization_id: int,
    count_id: int,
    lines: list[dict[str, Any]],
) -> dict[str, Any]:
    from nodeone.core.db import db

    _assert_inventory_module(organization_id)
    oid = int(organization_id)
    count = _get_count(oid, count_id)
    if str(count.status) not in (COUNT_STATUS_DRAFT, COUNT_STATUS_COUNTING):
        raise PhysicalCountError('count_not_editable')

    by_ref = {str(ln.product_ref): ln for ln in list(count.lines or [])}
    by_client = {
        str(ln.client_line_id): ln for ln in list(count.lines or []) if ln.client_line_id
    }

    for raw in lines or []:
        client_line_id = (str(raw.get('client_line_id') or '')).strip() or None
        product_ref = (str(raw.get('product_ref') or '')).strip()
        product_id = raw.get('product_id')
        product = None
        if product_id is not None:
            product = CoreProduct.query.filter_by(
                id=int(product_id), organization_id=oid, status='active'
            ).first()
        if product is None and product_ref:
            product = CoreProduct.query.filter_by(
                organization_id=oid, product_ref=product_ref, status='active'
            ).first()
        if product is None or not product.tracks_inventory:
            raise PhysicalCountError('invalid_product')
        ref = str(product.product_ref)

        line = None
        if client_line_id and client_line_id in by_client:
            line = by_client[client_line_id]
            if str(line.product_ref) != ref:
                raise PhysicalCountError('client_line_product_mismatch')
        if line is None:
            line = by_ref.get(ref)

        if line is None:
            snap = get_on_hand(oid, ref, warehouse_org_unit_id=int(count.warehouse_org_unit_id))
            post = _movement_delta_between(
                oid,
                ref,
                int(count.warehouse_org_unit_id),
                count.started_at,
                _utcnow(),
            )
            line = PhysicalInventoryCountLine(
                count_id=int(count.id),
                organization_id=oid,
                product_id=int(product.id),
                product_ref=ref,
                uom=product.uom or 'und',
                snapshot_qty=round(float(snap) - post, 4),
            )
            db.session.add(line)
            by_ref[ref] = line

        if client_line_id:
            if line.client_line_id and line.client_line_id != client_line_id:
                raise PhysicalCountError('line_already_has_client_id')
            line.client_line_id = client_line_id
            by_client[client_line_id] = line

        if 'physical_qty' in raw and raw.get('physical_qty') is not None:
            line.physical_qty = float(raw.get('physical_qty'))
            counted_raw = raw.get('counted_at')
            if counted_raw:
                if isinstance(counted_raw, datetime):
                    line.counted_at = counted_raw
                else:
                    line.counted_at = datetime.fromisoformat(str(counted_raw).replace('Z', ''))
            elif line.counted_at is None:
                line.counted_at = _utcnow()
        if raw.get('notes') is not None:
            line.notes = (str(raw.get('notes') or '')).strip()[:500] or None
        line.uom = product.uom or line.uom or 'und'
        line.product_id = int(product.id)
        line.updated_at = _utcnow()

    count.updated_at = _utcnow()
    db.session.commit()
    db.session.refresh(count)
    return count_to_dict(count, include_theoretical=False)


def complete_count(organization_id: int, count_id: int) -> dict[str, Any]:
    from nodeone.core.db import db

    _assert_inventory_module(organization_id)
    oid = int(organization_id)
    count = _get_count(oid, count_id)
    if str(count.status) == COUNT_STATUS_COMPLETED:
        return count_to_dict(count, include_theoretical=True)
    if str(count.status) != COUNT_STATUS_COUNTING:
        raise PhysicalCountError('count_not_completable')

    completed_at = _utcnow()
    count.completed_at = completed_at
    count.status = COUNT_STATUS_COMPLETED
    for line in list(count.lines or []):
        if line.physical_qty is None:
            continue
        if line.counted_at is None:
            line.counted_at = completed_at
        expected = expected_qty_for_line(count, line)
        line.expected_qty = expected
        line.difference_qty = round(float(line.physical_qty) - expected, 4)
    count.updated_at = completed_at
    db.session.commit()
    db.session.refresh(count)
    return count_to_dict(count, include_theoretical=True)


def approve_count(
    organization_id: int,
    count_id: int,
    *,
    approved_by_user_id: int | None,
    allow_self_approve: bool = False,
    is_admin: bool = False,
) -> dict[str, Any]:
    from nodeone.core.db import db

    _assert_inventory_module(organization_id)
    oid = int(organization_id)
    count = _get_count(oid, count_id)
    if str(count.status) == COUNT_STATUS_APPROVED:
        return count_to_dict(count, include_theoretical=True)
    if str(count.status) != COUNT_STATUS_COMPLETED:
        raise PhysicalCountError('count_not_approvable')

    approver = int(approved_by_user_id) if approved_by_user_id else None
    if (
        not allow_self_approve
        and not is_admin
        and approver is not None
        and count.created_by_user_id is not None
        and int(count.created_by_user_id) == approver
    ):
        raise PhysicalCountError('cannot_self_approve')

    movements: list[dict[str, Any]] = []
    for line in list(count.lines or []):
        if line.physical_qty is None:
            continue
        diff = float(line.difference_qty or 0)
        if abs(diff) < 1e-9:
            continue
        kind = 'ADJUSTMENT_IN' if diff > 0 else 'ADJUSTMENT_OUT'
        event_id = f'physcount:{int(count.id)}:{line.product_ref}:{kind}'
        result = record_movement(
            oid,
            product_ref=str(line.product_ref),
            kind=kind,
            quantity=abs(diff),
            warehouse_org_unit_id=int(count.warehouse_org_unit_id),
            reason='physical_count',
            notes=f'physical_count_id={int(count.id)}',
            source_system=str(count.source_system or 'EP1'),
            source_event_id=event_id,
        )
        movements.append(result)

    now = _utcnow()
    count.status = COUNT_STATUS_APPROVED
    count.approved_at = now
    count.approved_by_user_id = approver
    count.updated_at = now
    db.session.commit()
    payload = count_to_dict(count, include_theoretical=True)
    payload['adjustments'] = movements
    return payload


def cancel_count(organization_id: int, count_id: int) -> dict[str, Any]:
    from nodeone.core.db import db

    _assert_inventory_module(organization_id)
    count = _get_count(int(organization_id), count_id)
    if str(count.status) == COUNT_STATUS_APPROVED:
        raise PhysicalCountError('cannot_cancel_approved')
    if str(count.status) == COUNT_STATUS_CANCELLED:
        return count_to_dict(count, include_theoretical=False)
    count.status = COUNT_STATUS_CANCELLED
    count.cancelled_at = _utcnow()
    count.updated_at = count.cancelled_at
    db.session.commit()
    return count_to_dict(count, include_theoretical=False)


def get_count(
    organization_id: int,
    count_id: int,
    *,
    include_theoretical: bool | None = None,
) -> dict[str, Any]:
    _assert_inventory_module(organization_id)
    count = _get_count(int(organization_id), count_id)
    return count_to_dict(count, include_theoretical=include_theoretical)


def list_counts(organization_id: int, *, limit: int = 80) -> list[dict[str, Any]]:
    _assert_inventory_module(organization_id)
    rows = (
        PhysicalInventoryCount.query.filter_by(organization_id=int(organization_id))
        .order_by(PhysicalInventoryCount.id.desc())
        .limit(max(1, min(int(limit), 200)))
        .all()
    )
    out: list[dict[str, Any]] = []
    for row in rows:
        data = count_to_dict(row, include_lines=False)
        lines = list(row.lines or [])
        data['lines_total'] = len(lines)
        data['lines_counted'] = sum(1 for ln in lines if ln.physical_qty is not None)
        out.append(data)
    return out


def enrich_count_with_product_names(payload: dict[str, Any]) -> dict[str, Any]:
    """Agrega name al catálogo de captura (sin saldo teórico)."""
    refs = [str(ln.get('product_ref') or '') for ln in payload.get('lines') or []]
    refs = [r for r in refs if r]
    if not refs:
        return payload
    oid = int(payload.get('organization_id') or 0)
    rows = (
        CoreProduct.query.filter_by(organization_id=oid)
        .filter(CoreProduct.product_ref.in_(refs))
        .all()
    )
    names = {str(p.product_ref): str(p.name) for p in rows}
    cats = {str(p.product_ref): (p.category or '').strip() for p in rows}
    for ln in payload.get('lines') or []:
        ref = str(ln.get('product_ref') or '')
        ln['name'] = names.get(ref, ln.get('product_ref'))
        ln['category'] = cats.get(ref, '')
    return payload


def delete_count(organization_id: int, count_id: int) -> None:
    from nodeone.core.db import db

    count = _get_count(int(organization_id), count_id)
    if str(count.status) == COUNT_STATUS_APPROVED:
        raise PhysicalCountError('cannot_delete_approved')
    db.session.delete(count)
    db.session.commit()
