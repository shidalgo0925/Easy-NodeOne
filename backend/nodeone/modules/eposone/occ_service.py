"""OCC Fase A — Visibilidad (ADR-025): Dashboard Hoy + Cierres."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from models.commercial_core import CoreCashShift
from models.eposone_order import EposoneOrder, EposoneOrderPayment
from nodeone.core.commerce.constants import (
    CASH_SHIFT_CLOSED,
    CASH_SHIFT_OPEN,
    CASH_SHIFT_RECONCILING,
)
from nodeone.core.master.constants import (
    ORG_UNIT_TYPE_BRANCH,
    ORG_UNIT_TYPE_POS,
    ORG_UNIT_TYPE_REGISTER,
)
from nodeone.core.timezone_service import TimeZoneService
from nodeone.modules.eposone.shift_close_service import (
    cash_expected_for_shift,
    shift_activity_stats,
)

# Semáforo ADR-025
OCC_STATUS_OK = 'ok'  # Conciliado
OCC_STATUS_WARN = 'warn'  # Conciliado con observaciones / arqueo pendiente
OCC_STATUS_ALERT = 'alert'  # Diferencia pendiente
OCC_STATUS_OPEN = 'open'  # Turno abierto

_STATUS_LABELS = {
    OCC_STATUS_OK: 'Conciliado',
    OCC_STATUS_WARN: 'Conciliado con observaciones',
    OCC_STATUS_ALERT: 'Diferencia pendiente',
    OCC_STATUS_OPEN: 'Turno abierto',
}


def _money(value: float | int | None) -> float:
    return round(float(value or 0) + 1e-12, 2)


def _biz_bounds_today(organization_id: int) -> tuple[datetime, datetime, str, ZoneInfo]:
    from models.saas import SaasOrganization

    org = SaasOrganization.query.filter_by(id=int(organization_id)).first()
    zone = TimeZoneService.effective_timezone(user=None, organization=org)
    now_local = datetime.now(zone)
    day_local = now_local.strftime('%Y-%m-%d')
    start, end = TimeZoneService.day_bounds_utc_naive(day_local, zone)
    return start, end, day_local, zone


def _register_branch_map(organization_id: int) -> dict[str, dict[str, str]]:
    """register_ref → {register_name, branch_name, branch_ref}."""
    from nodeone.core.services.org_unit import OrgUnitService

    oid = int(organization_id)
    registers = OrgUnitService.list_units(oid, unit_type=ORG_UNIT_TYPE_REGISTER)
    pos_units = {int(p.id): p for p in OrgUnitService.list_units(oid, unit_type=ORG_UNIT_TYPE_POS)}
    branches = {int(b.id): b for b in OrgUnitService.list_units(oid, unit_type=ORG_UNIT_TYPE_BRANCH)}
    out: dict[str, dict[str, str]] = {}
    for reg in registers:
        ref = str(reg.unit_ref)
        branch_name = '—'
        branch_ref = ''
        parent_id = getattr(reg, 'parent_id', None)
        # register → POS → branch (or register → branch)
        node = pos_units.get(int(parent_id)) if parent_id else None
        if node is not None:
            gp = getattr(node, 'parent_id', None)
            br = branches.get(int(gp)) if gp else None
            if br is not None:
                branch_name = str(br.name)
                branch_ref = str(br.unit_ref)
            else:
                branch_name = str(node.name)
                branch_ref = str(node.unit_ref)
        elif parent_id and int(parent_id) in branches:
            br = branches[int(parent_id)]
            branch_name = str(br.name)
            branch_ref = str(br.unit_ref)
        out[ref] = {
            'register_name': str(reg.name or ref),
            'branch_name': branch_name,
            'branch_ref': branch_ref,
        }
    return out


def _sales_for_shift(shift: CoreCashShift) -> float:
    """Ventas (pagos kind=payment) en la ventana del turno."""
    from app import db
    from sqlalchemy import func

    start = shift.opened_at or datetime.utcnow()
    end = shift.closed_at or datetime.utcnow()
    if end <= start:
        end = start + timedelta(seconds=1)
    row = (
        db.session.query(func.coalesce(func.sum(EposoneOrderPayment.amount), 0.0))
        .join(EposoneOrder, EposoneOrder.id == EposoneOrderPayment.order_id)
        .filter(
            EposoneOrder.organization_id == int(shift.organization_id),
            EposoneOrderPayment.kind == 'payment',
            EposoneOrderPayment.created_at >= start,
            EposoneOrderPayment.created_at < end,
            # Pedidos del mismo register cuando hay register_ref
            EposoneOrder.register_ref == str(shift.register_ref),
        )
        .scalar()
    )
    return _money(row)


def _classify_shift(shift: CoreCashShift, *, expected: float, counted: float | None, variance: float | None) -> str:
    status = str(shift.status or '')
    if status == CASH_SHIFT_OPEN:
        return OCC_STATUS_OPEN
    if status == CASH_SHIFT_RECONCILING:
        if counted is None:
            return OCC_STATUS_WARN
        if variance is not None and abs(variance) >= 0.01:
            return OCC_STATUS_ALERT
        return OCC_STATUS_WARN
    # closed
    if counted is None:
        return OCC_STATUS_WARN
    if variance is not None and abs(variance) >= 0.01:
        return OCC_STATUS_ALERT
    return OCC_STATUS_OK


def shift_control_row(
    shift: CoreCashShift,
    *,
    meta: dict[str, str] | None = None,
) -> dict[str, Any]:
    meta = meta or {}
    cash = cash_expected_for_shift(shift, include_opening=True)
    expected = (
        _money(shift.expected_balance)
        if shift.expected_balance is not None
        and str(shift.status) in (CASH_SHIFT_RECONCILING, CASH_SHIFT_CLOSED)
        else cash['expected']
    )
    counted = _money(shift.counted_amount) if shift.counted_amount is not None else None
    variance = _money(counted - expected) if counted is not None else None
    occ_status = _classify_shift(shift, expected=expected, counted=counted, variance=variance)
    sales = _sales_for_shift(shift)
    activity = shift_activity_stats(shift)
    return {
        'shift_id': int(shift.id),
        'register_ref': str(shift.register_ref),
        'register_name': meta.get('register_name') or str(shift.register_ref),
        'branch_name': meta.get('branch_name') or '—',
        'branch_ref': meta.get('branch_ref') or '',
        'cashier_name': str(shift.cashier_name or 'Sin asignar'),
        'shift_status': str(shift.status or ''),
        'sales': sales,
        'expected': expected,
        'counted': counted,
        'variance': variance,
        'occ_status': occ_status,
        'occ_status_label': _STATUS_LABELS.get(occ_status, occ_status),
        'orders_count': int(activity.get('orders_count') or 0),
        'opened_at': shift.opened_at,
        'closed_at': shift.closed_at,
        'detail_url_path': f'/admin/eposone/shifts/{int(shift.id)}',
    }


def build_operations_control_today(organization_id: int) -> dict[str, Any]:
    """Payload Centro de Control — vista Hoy (Fase A)."""
    oid = int(organization_id)
    start, end, day_local, zone = _biz_bounds_today(oid)
    meta_map = _register_branch_map(oid)

    # Turnos que tocan el día: abiertos ahora o cerrados/abiertos en la ventana
    shifts = (
        CoreCashShift.query.filter_by(organization_id=oid)
        .filter(
            # abierto en cualquier momento del día de negocio
            (
                (CoreCashShift.opened_at < end)
                & (
                    (CoreCashShift.closed_at.is_(None))
                    | (CoreCashShift.closed_at >= start)
                )
            )
        )
        .order_by(CoreCashShift.opened_at.desc())
        .all()
    )

    rows = [
        shift_control_row(s, meta=meta_map.get(str(s.register_ref)))
        for s in shifts
    ]

    open_n = sum(1 for r in rows if r['shift_status'] == CASH_SHIFT_OPEN)
    closed_n = sum(1 for r in rows if r['shift_status'] == CASH_SHIFT_CLOSED)
    alert_n = sum(1 for r in rows if r['occ_status'] == OCC_STATUS_ALERT)
    warn_n = sum(1 for r in rows if r['occ_status'] == OCC_STATUS_WARN)
    sales_total = _money(sum(r['sales'] for r in rows))

    branches = sorted({r['branch_name'] for r in rows if r['branch_name'] and r['branch_name'] != '—'})
    problems = [r for r in rows if r['occ_status'] in (OCC_STATUS_ALERT, OCC_STATUS_WARN, OCC_STATUS_OPEN)]

    return {
        'day_local': day_local,
        'timezone': str(getattr(zone, 'key', None) or zone),
        'summary': {
            'branches': len(branches) or len({r['branch_ref'] for r in rows if r['branch_ref']}),
            'shifts_open': open_n,
            'shifts_closed': closed_n,
            'shifts_total': len(rows),
            'differences': alert_n,
            'alerts': alert_n + warn_n,
            'sales': sales_total,
            'currency': 'USD',
        },
        'rows': rows,
        'problems': problems[:20],
        'branches_list': branches,
    }


def build_operations_control_cierres(
    organization_id: int,
    *,
    only_closed: bool = False,
) -> dict[str, Any]:
    """Vista Cierres — misma fuente que Hoy, lista completa del día."""
    board = build_operations_control_today(organization_id)
    rows = board['rows']
    if only_closed:
        rows = [r for r in rows if r['shift_status'] == CASH_SHIFT_CLOSED]
    return {
        **board,
        'rows': rows,
        'view': 'cierres',
    }
