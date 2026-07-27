"""Reporte de cierre de turno (ADR-009 / B-R1-05b–c) — nivel EPOS1."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from models.commercial_core import CoreCashMovement, CoreCashShift
from models.eposone_order import EposoneOrder, EposoneOrderPayment
from nodeone.core.commerce.constants import (
    CASH_MOVEMENT_CASH_IN,
    CASH_MOVEMENT_CASH_OUT,
    CASH_MOVEMENT_REFUND_CASH,
    CASH_MOVEMENT_SALE_CASH,
    CASH_SHIFT_CLOSED,
    CASH_SHIFT_OPEN,
    CASH_SHIFT_RECONCILING,
)
from nodeone.core.timezone_service import TimeZoneService

# Métodos que cuentan como efectivo en cajón (arqueo físico).
_CASH_METHOD_KEYS = frozenset({'cash', 'efectivo'})
_BUSINESS_TZ = 'America/Panama'


def _money(value: float | int | None) -> float:
    return round(float(value or 0) + 1e-12, 2)


def _is_cash_method(method: str | None) -> bool:
    key = str(method or '').strip().lower().replace('-', '_').replace(' ', '_')
    return key in _CASH_METHOD_KEYS


def _biz_zone() -> ZoneInfo:
    return ZoneInfo(_BUSINESS_TZ)


def _shift_window(shift: CoreCashShift) -> tuple[datetime, datetime]:
    start = shift.opened_at or datetime.utcnow()
    end = shift.closed_at or datetime.utcnow()
    if end <= start:
        end = start + timedelta(seconds=1)
    return start, end


def _payment_ts(pay: EposoneOrderPayment) -> datetime:
    return pay.paid_at or pay.created_at or datetime.utcnow()


def _to_local_day(dt: datetime) -> str:
    zone = _biz_zone()
    if dt.tzinfo is None:
        from datetime import timezone

        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(zone).strftime('%Y-%m-%d')


def _days_spanned(shift: CoreCashShift) -> list[str]:
    """Días calendario (negocio) tocados por la ventana del turno."""
    start, end = _shift_window(shift)
    # end es exclusivo en pagos; para listar días usar end-1s si es exacto midnight edge
    first = _to_local_day(start)
    last = _to_local_day(end - timedelta(seconds=1) if end > start else end)
    days: list[str] = []
    cur = datetime.strptime(first, '%Y-%m-%d').date()
    last_d = datetime.strptime(last, '%Y-%m-%d').date()
    while cur <= last_d:
        days.append(cur.strftime('%Y-%m-%d'))
        cur += timedelta(days=1)
    return days


def _resolve_report_window(
    shift: CoreCashShift, day_local: str | None
) -> tuple[datetime, datetime, dict[str, Any]]:
    """Ventana efectiva: turno completo o turno ∩ día de negocio."""
    shift_start, shift_end = _shift_window(shift)
    days = _days_spanned(shift)
    multi_day = len(days) > 1
    raw = (day_local or '').strip().lower()
    if not raw or raw in {'all', 'todo', '*'}:
        return shift_start, shift_end, {
            'mode': 'all',
            'day_local': None,
            'days': days,
            'multi_day': multi_day,
            'label': 'Todo el turno',
        }
    # validar formato
    try:
        day_start, day_end = TimeZoneService.day_bounds_utc_naive(raw[:10], _biz_zone())
    except ValueError:
        return shift_start, shift_end, {
            'mode': 'all',
            'day_local': None,
            'days': days,
            'multi_day': multi_day,
            'label': 'Todo el turno',
        }
    # intersección
    start = max(shift_start, day_start)
    end = min(shift_end, day_end)
    if end <= start:
        # día fuera de ventana → vacío
        start, end = shift_start, shift_start
    return start, end, {
        'mode': 'day',
        'day_local': raw[:10],
        'days': days,
        'multi_day': multi_day,
        'label': raw[:10],
    }


def _movement_breakdown(
    shift_id: int, *, window_start: datetime | None = None, window_end: datetime | None = None
) -> dict[str, float]:
    sale = 0.0
    cash_in = 0.0
    cash_out = 0.0
    refund = 0.0
    q = CoreCashMovement.query.filter_by(shift_id=int(shift_id))
    if window_start is not None and window_end is not None:
        q = q.filter(
            CoreCashMovement.created_at >= window_start,
            CoreCashMovement.created_at < window_end,
        )
    for amt, mtype in q.with_entities(
        CoreCashMovement.amount, CoreCashMovement.movement_type
    ).all():
        amount = _money(amt)
        kind = str(mtype or '')
        if kind == CASH_MOVEMENT_SALE_CASH:
            sale += amount
        elif kind == CASH_MOVEMENT_CASH_IN:
            cash_in += amount
        elif kind == CASH_MOVEMENT_CASH_OUT:
            cash_out += amount
        elif kind == CASH_MOVEMENT_REFUND_CASH:
            refund += amount
    return {
        'sale_cash': _money(sale),
        'cash_in': _money(cash_in),
        'cash_out': _money(cash_out),
        'refund_cash': _money(refund),
    }


def _od_payments_for_shift(
    shift: CoreCashShift, *, window_start: datetime, window_end: datetime
) -> list[tuple[EposoneOrderPayment, EposoneOrder]]:
    """Pagos Order Domain de la misma caja en la ventana indicada."""
    ref = str(shift.register_ref or '').strip()
    if not ref or window_end <= window_start:
        return []
    rows = (
        EposoneOrderPayment.query.join(EposoneOrder, EposoneOrder.id == EposoneOrderPayment.order_id)
        .filter(
            EposoneOrder.organization_id == int(shift.organization_id),
            EposoneOrder.register_ref == ref,
            EposoneOrderPayment.status == 'captured',
        )
        .order_by(EposoneOrderPayment.id.asc())
        .all()
    )
    out: list[tuple[EposoneOrderPayment, EposoneOrder]] = []
    for pay in rows:
        order = pay.order
        if order is None:
            continue
        ts = _payment_ts(pay)
        if ts < window_start or ts >= window_end:
            continue
        out.append((pay, order))
    return out


def shift_activity_stats(
    shift: CoreCashShift,
    *,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    pay_rows: list[tuple[EposoneOrderPayment, EposoneOrder]] | None = None,
) -> dict[str, int]:
    """Actividad del turno: pagos OD + movimientos de tesorería (misma ventana que el esperado)."""
    if window_start is None or window_end is None:
        window_start, window_end = _shift_window(shift)
    if pay_rows is None:
        pay_rows = _od_payments_for_shift(
            shift, window_start=window_start, window_end=window_end
        )
    treasury_count = int(
        CoreCashMovement.query.filter_by(shift_id=int(shift.id))
        .filter(
            CoreCashMovement.created_at >= window_start,
            CoreCashMovement.created_at < window_end,
        )
        .count()
        or 0
    )
    payment_count = len(pay_rows)
    orders_count = len({int(order.id) for _pay, order in pay_rows})
    return {
        'payment_count': payment_count,
        'treasury_count': treasury_count,
        'orders_count': orders_count,
        'activity_count': payment_count + treasury_count,
    }


def cash_expected_for_shift(
    shift: CoreCashShift,
    *,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    include_opening: bool = True,
    pay_rows: list[tuple[EposoneOrderPayment, EposoneOrder]] | None = None,
) -> dict[str, float]:
    """Esperado del cajón = solo efectivo (ADR-009 §arqueo / B-R1-05c)."""
    if window_start is None or window_end is None:
        window_start, window_end = _shift_window(shift)
    mov = _movement_breakdown(
        int(shift.id), window_start=window_start, window_end=window_end
    )
    if pay_rows is None:
        pay_rows = _od_payments_for_shift(
            shift, window_start=window_start, window_end=window_end
        )
    od_cash_sales = 0.0
    od_cash_refunds = 0.0
    for pay, _order in pay_rows:
        if not _is_cash_method(pay.method):
            continue
        amt = _money(pay.amount)
        kind = str(pay.kind or 'payment').lower()
        if kind in ('refund', 'reembolso'):
            od_cash_refunds += amt
        else:
            od_cash_sales += amt

    opening = _money(shift.opening_balance) if include_opening else 0.0
    cash_sales = _money(mov['sale_cash'] + od_cash_sales)
    cash_in = mov['cash_in']
    cash_out = mov['cash_out']
    refunds = _money(mov['refund_cash'] + od_cash_refunds)
    expected = _money(opening + cash_sales + cash_in - cash_out - refunds)
    return {
        'opening': opening,
        'cash_sales': cash_sales,
        'cash_in': cash_in,
        'cash_out': cash_out,
        'refunds': refunds,
        'expected': expected,
    }


def build_shift_close_report(
    organization_id: int,
    shift_id: int,
    *,
    day_local: str | None = None,
) -> dict[str, Any] | None:
    """Payload completo para pantalla BO de cierre (paridad EPOS1).

    day_local: YYYY-MM-DD para filtrar resumen al día; None/'all' = todo el turno.
    """
    shift = CoreCashShift.query.filter_by(
        organization_id=int(organization_id), id=int(shift_id)
    ).first()
    if shift is None:
        return None

    window_start, window_end, day_filter = _resolve_report_window(shift, day_local)
    include_opening = day_filter['mode'] == 'all'
    # Primer día del turno: si filtra ese día, incluir apertura
    if day_filter['mode'] == 'day' and day_filter['day_local'] and day_filter['days']:
        if day_filter['day_local'] == day_filter['days'][0]:
            include_opening = True

    pay_rows = _od_payments_for_shift(
        shift, window_start=window_start, window_end=window_end
    )
    activity = shift_activity_stats(
        shift,
        window_start=window_start,
        window_end=window_end,
        pay_rows=pay_rows,
    )
    orders_by_id: dict[int, EposoneOrder] = {}
    method_totals: dict[str, float] = {}
    for pay, order in pay_rows:
        orders_by_id[int(order.id)] = order
        key = str(pay.method or 'other').strip().lower() or 'other'
        method_totals[key] = _money(method_totals.get(key, 0) + _money(pay.amount))

    sales_gross = 0.0
    discounts = 0.0
    tax = 0.0
    tips = 0.0
    refunds_total = 0.0
    sales_count = 0
    refund_count = 0
    for order in orders_by_id.values():
        st = str(order.status or '').lower()
        if st in ('cancelled',):
            continue
        if st == 'returned':
            refund_count += 1
            refunds_total += _money(order.total)
            continue
        sales_count += 1
        sales_gross += _money(order.subtotal)
        discounts += _money(order.discount)
        tax += _money(order.tax)
        tips += _money(order.tip)

    sales_net = _money(sales_gross - discounts + tax)

    method_labels: dict[str, str] = {}
    try:
        from nodeone.modules.eposone.order_payment_service import OrderPaymentService

        for m in OrderPaymentService.list_methods(int(organization_id), enabled_only=False):
            method_labels[str(m['method_key'])] = str(m['label'])
    except Exception:
        method_labels = {}

    payment_methods = [
        {
            'method_key': key,
            'label': method_labels.get(key) or key.replace('_', ' ').title(),
            'amount': amt,
            'is_cash': _is_cash_method(key),
        }
        for key, amt in sorted(method_totals.items(), key=lambda x: (-x[1], x[0]))
    ]

    cash = cash_expected_for_shift(
        shift,
        window_start=window_start,
        window_end=window_end,
        include_opening=include_opening,
        pay_rows=pay_rows,
    )
    # Arqueo oficial siempre es del turno completo (ADR-009).
    if day_filter['mode'] == 'all' and include_opening:
        cash_full = cash
    else:
        cash_full = cash_expected_for_shift(shift, include_opening=True)
    status = str(shift.status or '')
    counted = (
        _money(shift.counted_amount)
        if shift.counted_amount is not None
        else None
    )
    expected_official = (
        _money(shift.expected_balance)
        if shift.expected_balance is not None
        and status in (CASH_SHIFT_RECONCILING, CASH_SHIFT_CLOSED)
        else cash_full['expected']
    )
    variance = None
    if counted is not None:
        variance = _money(counted - expected_official)

    return {
        'shift': shift,
        'status': status,
        'can_reconcile': status == CASH_SHIFT_OPEN and day_filter['mode'] == 'all',
        'can_close': status == CASH_SHIFT_RECONCILING and day_filter['mode'] == 'all',
        'can_move': status == CASH_SHIFT_OPEN and day_filter['mode'] == 'all',
        'day_filter': day_filter,
        'sales': {
            'gross': _money(sales_gross),
            'refunds': _money(refunds_total),
            'net': sales_net,
            'discounts': _money(discounts),
            'tax': _money(tax),
            'tips': _money(tips),
            'sales_count': sales_count,
            'refund_count': refund_count,
        },
        'payment_methods': payment_methods,
        'electronic_methods': [m for m in payment_methods if not m['is_cash']],
        'cash': {
            **cash,
            # En vista día, "expected" = movimiento del período (sin confundir con arqueo).
            'expected': cash['expected'],
            'counted': counted if day_filter['mode'] == 'all' else None,
            'variance': variance if day_filter['mode'] == 'all' else None,
            'include_opening': include_opening,
        },
        'cash_official': {
            **cash_full,
            'expected': expected_official,
            'counted': counted,
            'variance': variance,
        },
        'activity': activity,
        'movement_count': activity['activity_count'],
        'orders_count': len(orders_by_id),
    }
