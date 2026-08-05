"""OCC Fase A/B/C — Visibilidad + Control + Inteligencia (ADR-025).

Fase A: Dashboard Hoy + Cierres.
Fase B: Excepciones (Alertas) + Bitácora del turno (Auditoría).
Fase C: Operación (salud + ranking) + Pagos (medios del día).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from models.commercial_core import CoreCashMovement, CoreCashShift, CorePosTerminal
from models.eposone_order import EposoneOrder, EposoneOrderEvent, EposoneOrderPayment
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

# Umbrales Fase B (Control) — fijos v1; configurable más adelante
OCC_OPEN_SHIFT_HOURS_ALERT = 12
OCC_VARIANCE_CRITICAL_ABS = 20.0

# Umbrales Fase C (Inteligencia)
OCC_DEVICE_STALE_MINUTES = 15
OCC_OPEN_ORDER_STALE_MINUTES = 45

OCC_SEV_CRITICAL = 'critical'
OCC_SEV_HIGH = 'high'
OCC_SEV_MEDIUM = 'medium'

_SEV_LABELS = {
    OCC_SEV_CRITICAL: 'Crítica',
    OCC_SEV_HIGH: 'Alta',
    OCC_SEV_MEDIUM: 'Media',
}

_SEV_RANK = {
    OCC_SEV_CRITICAL: 0,
    OCC_SEV_HIGH: 1,
    OCC_SEV_MEDIUM: 2,
}

_BITACORA_ORDER_EVENT_TYPES = frozenset(
    {
        'pedido.anulado',
        'pedido.devuelto',
        'pago.registrado',
        'pedido.cobrado',
        'producto.eliminado',
        'linea.cancelada',
        'pedido.dividido',
    }
)

_ORDER_EVENT_TITLES = {
    'pedido.creado': 'Pedido creado',
    'pedido.actualizado': 'Pedido actualizado',
    'pedido.dividido': 'Pedido dividido',
    'producto.agregado': 'Producto agregado',
    'producto.eliminado': 'Producto quitado',
    'cantidad.modificada': 'Cantidad modificada',
    'pedido.enviado': 'Enviado a cocina',
    'linea.lista': 'Línea lista',
    'pedido.listo': 'Listo',
    'linea.entregada': 'Línea entregada',
    'pedido.entregado': 'Entregado',
    'pago.registrado': 'Pago',
    'pedido.cobrado': 'Cobrado',
    'linea.cancelada': 'Línea cancelada',
    'pedido.anulado': 'Anulado',
    'pedido.devuelto': 'Devuelto',
}

_MOVEMENT_TITLES = {
    'sale_cash': 'Venta efectivo',
    'refund_cash': 'Reembolso efectivo',
    'cash_in': 'Entrada de efectivo',
    'cash_out': 'Salida de efectivo',
    'opening': 'Fondo de apertura',
    'closing': 'Retiro de cierre',
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


def _hours_open(opened_at: datetime | None, *, now: datetime | None = None) -> float:
    if opened_at is None:
        return 0.0
    end = now or datetime.utcnow()
    start = opened_at
    if start.tzinfo is not None:
        start = start.replace(tzinfo=None)
    if end.tzinfo is not None:
        end = end.replace(tzinfo=None)
    secs = max(0.0, (end - start).total_seconds())
    return round(secs / 3600.0, 2)


def _exception_entry(
    *,
    code: str,
    severity: str,
    title: str,
    detail: str,
    row: dict[str, Any],
) -> dict[str, Any]:
    return {
        'code': code,
        'severity': severity,
        'severity_label': _SEV_LABELS.get(severity, severity),
        'title': title,
        'detail': detail,
        'shift_id': row['shift_id'],
        'register_ref': row['register_ref'],
        'register_name': row['register_name'],
        'branch_name': row['branch_name'],
        'cashier_name': row['cashier_name'],
        'occ_status': row['occ_status'],
        'occ_status_label': row.get('occ_status_label') or _STATUS_LABELS.get(row['occ_status'], row['occ_status']),
        'variance': row.get('variance'),
        'sales': row.get('sales'),
        'opened_at': row.get('opened_at'),
        'closed_at': row.get('closed_at'),
        'detail_url_path': row.get('detail_url_path'),
        'bitacora_url_path': f"/admin/eposone/control/auditoria/{int(row['shift_id'])}",
    }


def exceptions_for_shift_row(
    row: dict[str, Any],
    *,
    now: datetime | None = None,
    open_hours_threshold: float = OCC_OPEN_SHIFT_HOURS_ALERT,
    variance_critical: float = OCC_VARIANCE_CRITICAL_ABS,
) -> list[dict[str, Any]]:
    """Reglas de excepción v1 sobre una fila OCC (sin I/O)."""
    out: list[dict[str, Any]] = []
    status = row.get('occ_status')
    variance = row.get('variance')
    shift_status = row.get('shift_status')

    if status == OCC_STATUS_ALERT and variance is not None and abs(float(variance)) >= 0.01:
        sev = (
            OCC_SEV_CRITICAL
            if abs(float(variance)) >= float(variance_critical)
            else OCC_SEV_HIGH
        )
        out.append(
            _exception_entry(
                code='cash_difference',
                severity=sev,
                title='Diferencia de caja',
                detail=f"Varianza ${float(variance):+.2f} (esperado ${float(row.get('expected') or 0):.2f})",
                row=row,
            )
        )

    if status == OCC_STATUS_WARN:
        if row.get('counted') is None:
            out.append(
                _exception_entry(
                    code='pending_count',
                    severity=OCC_SEV_MEDIUM,
                    title='Arqueo pendiente',
                    detail='Turno en conciliación / cerrado sin monto contado',
                    row=row,
                )
            )
        else:
            out.append(
                _exception_entry(
                    code='observations',
                    severity=OCC_SEV_MEDIUM,
                    title='Conciliado con observaciones',
                    detail='Requiere revisión del arqueo',
                    row=row,
                )
            )

    if shift_status == CASH_SHIFT_OPEN:
        hours = _hours_open(row.get('opened_at'), now=now)
        if hours >= float(open_hours_threshold):
            out.append(
                _exception_entry(
                    code='shift_open_long',
                    severity=OCC_SEV_HIGH,
                    title='Turno abierto demasiado tiempo',
                    detail=f'Abierto {hours:.1f} h (umbral {open_hours_threshold:g} h)',
                    row=row,
                )
            )

    return out


def build_operations_control_excepciones(organization_id: int) -> dict[str, Any]:
    """Vista Alertas / Excepciones — solo turnos con riesgo (Fase B)."""
    board = build_operations_control_today(organization_id)
    now = datetime.utcnow()
    exceptions: list[dict[str, Any]] = []
    for row in board['rows']:
        exceptions.extend(exceptions_for_shift_row(row, now=now))

    exceptions.sort(
        key=lambda e: (
            _SEV_RANK.get(e['severity'], 9),
            -(abs(float(e['variance'])) if e.get('variance') is not None else 0.0),
            str(e.get('register_name') or ''),
        )
    )

    by_sev = {
        OCC_SEV_CRITICAL: sum(1 for e in exceptions if e['severity'] == OCC_SEV_CRITICAL),
        OCC_SEV_HIGH: sum(1 for e in exceptions if e['severity'] == OCC_SEV_HIGH),
        OCC_SEV_MEDIUM: sum(1 for e in exceptions if e['severity'] == OCC_SEV_MEDIUM),
    }
    return {
        **board,
        'view': 'excepciones',
        'exceptions': exceptions,
        'exception_summary': {
            'total': len(exceptions),
            **by_sev,
        },
    }


def build_operations_control_auditoria(organization_id: int) -> dict[str, Any]:
    """Índice Auditoría — turnos del día con enlace a bitácora."""
    board = build_operations_control_today(organization_id)
    rows = []
    for r in board['rows']:
        rows.append(
            {
                **r,
                'bitacora_url_path': f"/admin/eposone/control/auditoria/{int(r['shift_id'])}",
            }
        )
    return {
        **board,
        'rows': rows,
        'view': 'auditoria',
    }


def build_shift_bitacora(organization_id: int, shift_id: int) -> dict[str, Any] | None:
    """Timeline operacional del turno (movimientos + eventos sensibles de pedido)."""
    oid = int(organization_id)
    shift = CoreCashShift.query.filter_by(id=int(shift_id), organization_id=oid).first()
    if shift is None:
        return None

    meta_map = _register_branch_map(oid)
    row = shift_control_row(shift, meta=meta_map.get(str(shift.register_ref)))
    start = shift.opened_at or datetime.utcnow()
    end = shift.closed_at or datetime.utcnow()
    if end <= start:
        end = start + timedelta(seconds=1)

    entries: list[dict[str, Any]] = []
    entries.append(
        {
            'at': shift.opened_at,
            'kind': 'shift.open',
            'title': 'Turno abierto',
            'meta': row['cashier_name'],
            'amount': _money(shift.opening_balance),
            'order_id': None,
            'en1_number': None,
        }
    )

    movements = (
        CoreCashMovement.query.filter_by(organization_id=oid, shift_id=int(shift.id))
        .order_by(CoreCashMovement.created_at.asc(), CoreCashMovement.id.asc())
        .all()
    )
    for mv in movements:
        mtype = str(mv.movement_type or '')
        entries.append(
            {
                'at': mv.created_at,
                'kind': 'cash.movement',
                'title': _MOVEMENT_TITLES.get(mtype) or mtype.replace('_', ' ').title(),
                'meta': (mv.notes or '')[:120],
                'amount': _money(mv.amount),
                'order_id': None,
                'en1_number': None,
            }
        )

    order_ids = [
        int(row_id)
        for (row_id,) in EposoneOrder.query.filter(
            EposoneOrder.organization_id == oid,
            EposoneOrder.register_ref == str(shift.register_ref),
            EposoneOrder.opened_at < end,
            EposoneOrder.opened_at >= start,
        )
        .with_entities(EposoneOrder.id)
        .all()
    ]
    # También pedidos con eventos en la ventana del turno (mismo register)
    if order_ids:
        events = (
            EposoneOrderEvent.query.filter(
                EposoneOrderEvent.organization_id == oid,
                EposoneOrderEvent.order_id.in_(order_ids),
                EposoneOrderEvent.type.in_(list(_BITACORA_ORDER_EVENT_TYPES)),
                EposoneOrderEvent.occurred_at >= start,
                EposoneOrderEvent.occurred_at < end,
            )
            .order_by(EposoneOrderEvent.occurred_at.asc(), EposoneOrderEvent.sequence.asc())
            .all()
        )
    else:
        events = []

    order_numbers: dict[int, str] = {}
    if events:
        for o in EposoneOrder.query.filter(EposoneOrder.id.in_({int(e.order_id) for e in events})).all():
            order_numbers[int(o.id)] = str(o.en1_number)

    for ev in events:
        etype = str(ev.type or '')
        oid_ord = int(ev.order_id)
        en1 = order_numbers.get(oid_ord, '')
        entries.append(
            {
                'at': ev.occurred_at,
                'kind': 'order.event',
                'title': _ORDER_EVENT_TITLES.get(etype) or etype.replace('.', ' · '),
                'meta': ev.actor_user_ref or ev.actor_device_uuid or '',
                'amount': None,
                'order_id': oid_ord,
                'en1_number': en1,
            }
        )

    if shift.closed_at is not None:
        entries.append(
            {
                'at': shift.closed_at,
                'kind': 'shift.close',
                'title': 'Turno cerrado',
                'meta': row['occ_status_label'],
                'amount': _money(shift.counted_amount) if shift.counted_amount is not None else None,
                'order_id': None,
                'en1_number': None,
            }
        )

    def _sort_key(e: dict[str, Any]) -> tuple:
        at = e.get('at') or datetime.min
        if getattr(at, 'tzinfo', None) is not None:
            at = at.replace(tzinfo=None)
        return (at, str(e.get('kind') or ''), str(e.get('title') or ''))

    entries.sort(key=_sort_key)

    return {
        'view': 'bitacora',
        'shift_row': row,
        'shift': shift,
        'entries': entries,
        'exceptions': exceptions_for_shift_row(row, now=datetime.utcnow()),
        'day_local': None,
        'timezone': None,
    }


def _device_health_rows(organization_id: int, *, now: datetime | None = None) -> list[dict[str, Any]]:
    oid = int(organization_id)
    now = now or datetime.utcnow()
    stale_before = now - timedelta(minutes=OCC_DEVICE_STALE_MINUTES)
    terminals = (
        CorePosTerminal.query.filter_by(organization_id=oid)
        .filter(CorePosTerminal.status == 'active')
        .order_by(CorePosTerminal.id.asc())
        .all()
    )
    rows: list[dict[str, Any]] = []
    _health_rank = {'stale': 0, 'unknown': 1, 'ok': 2}
    for t in terminals:
        seen = t.last_seen_at
        if seen is not None and getattr(seen, 'tzinfo', None) is not None:
            seen_naive = seen.replace(tzinfo=None)
        else:
            seen_naive = seen
        if seen_naive is None:
            health = 'unknown'
            health_label = 'Sin señal'
        elif seen_naive < stale_before:
            health = 'stale'
            health_label = 'Retrasado'
        else:
            health = 'ok'
            health_label = 'En línea'
        rows.append(
            {
                'terminal_ref': str(t.terminal_ref),
                'device_label': str(t.device_label or t.terminal_ref),
                'register_ref': str(t.register_ref or ''),
                'platform': str(t.platform or ''),
                'app_version': str(t.app_version or ''),
                'last_seen_at': t.last_seen_at,
                'health': health,
                'health_label': health_label,
            }
        )
    rows.sort(
        key=lambda d: (
            _health_rank.get(d['health'], 9),
            str(d.get('device_label') or '').lower(),
        )
    )
    return rows


_PAYMENT_METHOD_LABELS = {
    'cash': 'Efectivo',
    'card': 'Tarjeta',
    'transfer': 'Transferencia',
    'wallet': 'Billetera',
    'credit': 'Crédito',
    'other': 'Otros',
    'otros': 'Otros',
}


def _payment_method_label(method: str) -> str:
    key = str(method or 'otros').strip().lower()
    return _PAYMENT_METHOD_LABELS.get(key) or key.replace('_', ' ').title()


def build_operations_control_pagos(organization_id: int) -> dict[str, Any]:
    """Vista Pagos — mix de medios del día de negocio (Order Domain)."""
    from app import db
    from sqlalchemy import func

    oid = int(organization_id)
    start, end, day_local, zone = _biz_bounds_today(oid)
    pay_rows = (
        db.session.query(
            EposoneOrderPayment.method,
            func.coalesce(func.sum(EposoneOrderPayment.amount), 0.0),
            func.count(EposoneOrderPayment.id),
        )
        .join(EposoneOrder, EposoneOrder.id == EposoneOrderPayment.order_id)
        .filter(
            EposoneOrder.organization_id == oid,
            EposoneOrderPayment.kind == 'payment',
            EposoneOrderPayment.created_at >= start,
            EposoneOrderPayment.created_at < end,
        )
        .group_by(EposoneOrderPayment.method)
        .order_by(func.sum(EposoneOrderPayment.amount).desc())
        .all()
    )
    methods: list[dict[str, Any]] = []
    total_amount = 0.0
    total_count = 0
    for method, amount, count in pay_rows:
        amt = _money(amount)
        cnt = int(count or 0)
        if amt <= 0 and cnt <= 0:
            continue
        total_amount += amt
        total_count += cnt
        key = str(method or 'otros')
        methods.append(
            {
                'method': key,
                'method_label': _payment_method_label(key),
                'amount': amt,
                'count': cnt,
                'share_pct': 0.0,
            }
        )
    total_amount = _money(total_amount)
    for m in methods:
        m['share_pct'] = round((m['amount'] / total_amount) * 100.0, 1) if total_amount else 0.0

    lead = methods[0] if methods else None
    insights: list[str] = []
    if lead and total_amount > 0:
        insights.append(
            f"Medio dominante: {lead['method_label']} ({lead['share_pct']:.0f}% · ${lead['amount']:.2f})"
        )
    if len(methods) >= 2:
        insights.append(f'{len(methods)} medios activos en el día')
    elif not methods:
        insights.append('Sin cobros registrados en el día de negocio')

    return {
        'day_local': day_local,
        'timezone': str(getattr(zone, 'key', None) or zone),
        'view': 'pagos',
        'methods': methods,
        'summary': {
            'amount': total_amount,
            'count': total_count,
            'methods': len(methods),
            'currency': 'USD',
        },
        'insights': insights,
    }


def build_operations_control_operacion(organization_id: int) -> dict[str, Any]:
    """Vista Operación — salud + ranking + insights (Fase C)."""
    from app import db
    from sqlalchemy import func

    oid = int(organization_id)
    board = build_operations_control_today(oid)
    now = datetime.utcnow()
    start, end, day_local, zone = _biz_bounds_today(oid)

    exceptions: list[dict[str, Any]] = []
    for row in board['rows']:
        exceptions.extend(exceptions_for_shift_row(row, now=now))
    exc_summary = {
        'total': len(exceptions),
        OCC_SEV_CRITICAL: sum(1 for e in exceptions if e['severity'] == OCC_SEV_CRITICAL),
        OCC_SEV_HIGH: sum(1 for e in exceptions if e['severity'] == OCC_SEV_HIGH),
        OCC_SEV_MEDIUM: sum(1 for e in exceptions if e['severity'] == OCC_SEV_MEDIUM),
    }

    devices = _device_health_rows(oid, now=now)
    devices_ok = sum(1 for d in devices if d['health'] == 'ok')
    devices_stale = sum(1 for d in devices if d['health'] == 'stale')
    devices_unknown = sum(1 for d in devices if d['health'] == 'unknown')

    open_orders = (
        EposoneOrder.query.filter_by(organization_id=oid, status='open')
        .filter(EposoneOrder.opened_at >= start, EposoneOrder.opened_at < end)
        .count()
    )
    stale_cut = now - timedelta(minutes=OCC_OPEN_ORDER_STALE_MINUTES)
    stale_orders = (
        EposoneOrder.query.filter_by(organization_id=oid, status='open')
        .filter(
            EposoneOrder.opened_at < stale_cut,
            EposoneOrder.opened_at >= start,
        )
        .count()
    )

    ticket_row = (
        db.session.query(
            func.count(EposoneOrder.id),
            func.coalesce(func.avg(EposoneOrder.total), 0.0),
            func.coalesce(func.sum(EposoneOrder.total), 0.0),
        )
        .filter(
            EposoneOrder.organization_id == oid,
            EposoneOrder.opened_at >= start,
            EposoneOrder.opened_at < end,
            EposoneOrder.status != 'cancelled',
        )
        .first()
    )
    orders_n = int(ticket_row[0] or 0) if ticket_row else 0
    avg_ticket = _money(ticket_row[1]) if ticket_row else 0.0
    sales_orders = _money(ticket_row[2]) if ticket_row else 0.0

    ranking = sorted(
        [r for r in board['rows'] if float(r.get('sales') or 0) > 0],
        key=lambda r: float(r.get('sales') or 0),
        reverse=True,
    )[:8]

    insights: list[dict[str, str]] = []
    if exc_summary['total']:
        insights.append(
            {
                'tone': 'warning',
                'title': f"{exc_summary['total']} excepción(es) activas",
                'text': 'Priorizá Excepciones antes de revisar el ranking.',
                'href': '/admin/eposone/control/excepciones',
            }
        )
    if devices_stale or devices_unknown:
        insights.append(
            {
                'tone': 'danger' if devices_stale else 'secondary',
                'title': f'{devices_stale} dispositivo(s) retrasado(s)',
                'text': f'{devices_unknown} sin señal · umbral {OCC_DEVICE_STALE_MINUTES} min',
                'href': '/admin/eposone/section/terminals',
            }
        )
    if stale_orders:
        insights.append(
            {
                'tone': 'warning',
                'title': f'{stale_orders} pedido(s) abiertos >{OCC_OPEN_ORDER_STALE_MINUTES} min',
                'text': 'Pueden requerir atención en piso.',
                'href': '/admin/eposone/section/orders',
            }
        )
    if ranking:
        top = ranking[0]
        insights.append(
            {
                'tone': 'info',
                'title': f"Caja líder: {top['register_name']}",
                'text': f"${top['sales']:.2f} · {top['branch_name']}",
                'href': top.get('detail_url_path') or '/admin/eposone/control/cierres',
            }
        )
    if not insights:
        insights.append(
            {
                'tone': 'success',
                'title': 'Operación estable',
                'text': 'Sin señales de riesgo en salud ni excepciones.',
                'href': '/admin/eposone/control/hoy',
            }
        )

    # Semáforo: turnos abiertos son normales; no bajan a ámbar solos.
    health_score = 'green'
    if devices_stale or exc_summary.get(OCC_SEV_CRITICAL) or stale_orders >= 3:
        health_score = 'red'
    elif devices_unknown or exc_summary['total'] or stale_orders:
        health_score = 'amber'

    return {
        **board,
        'view': 'operacion',
        'day_local': day_local,
        'timezone': str(getattr(zone, 'key', None) or zone),
        'health': {
            'score': health_score,
            'devices_total': len(devices),
            'devices_ok': devices_ok,
            'devices_stale': devices_stale,
            'devices_unknown': devices_unknown,
            'open_orders': open_orders,
            'stale_orders': stale_orders,
            'exceptions': exc_summary['total'],
            'avg_ticket': avg_ticket,
            'orders_count': orders_n,
            'sales_orders': sales_orders,
            'shifts_open': board['summary']['shifts_open'],
        },
        'devices': devices,
        'ranking': ranking,
        'insights': insights,
        'exception_summary': exc_summary,
    }
