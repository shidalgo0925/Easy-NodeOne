"""KPIs operativos EPosOne — Order Domain Hito 3 + stock/caja (BackOffice UX)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func

from models.commercial_core import CoreCashShift, CoreStockBalance
from models.core_master import CoreProduct
from models.eposone_order import EposoneOrder, EposoneOrderItem, EposoneOrderPayment
from models.platform_events import PlatformDomainEvent
from nodeone.core.commerce.constants import CASH_SHIFT_OPEN
from nodeone.core.commerce.events import (
    COMMERCE_REPORT_ORDER_VOIDED,
    COMMERCE_REPORT_REFUND_RECORDED,
    COMMERCE_REPORT_SALE_RECORDED,
    COMMERCE_REPORT_SHIFT_CLOSED,
)

_REPORT_EVENT_TYPES = frozenset(
    {
        COMMERCE_REPORT_SALE_RECORDED,
        COMMERCE_REPORT_REFUND_RECORDED,
        COMMERCE_REPORT_ORDER_VOIDED,
        COMMERCE_REPORT_SHIFT_CLOSED,
    }
)

_VALID_RANGES = frozenset({'hoy', 'ayer', 'semana', 'mes', 'custom'})
_UTC = timezone.utc


def business_timezone() -> ZoneInfo:
    """Zona operativa EPosOne (PC negocio / Itsmo). No muda el TZ del SO del VPS."""
    name = (os.environ.get('EPOSONE_DEFAULT_TIMEZONE') or 'America/Panama').strip() or 'America/Panama'
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo('America/Panama')


def _to_utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(_UTC).replace(tzinfo=None)


@dataclass(frozen=True)
class DashboardKpiSnapshot:
    orders_today: int
    sales_today: float
    open_registers: int
    stock_alerts: int
    currency: str

    def to_dict(self) -> dict[str, Any]:
        return {
            'orders_today': self.orders_today,
            'sales_today': self.sales_today,
            'open_registers': self.open_registers,
            'stock_alerts': self.stock_alerts,
            'currency': self.currency,
        }


def _parse_local_date(value: str | None, tz: ZoneInfo) -> datetime | None:
    raw = (value or '').strip()
    if not raw:
        return None
    try:
        d = datetime.strptime(raw[:10], '%Y-%m-%d')
        return d.replace(tzinfo=tz)
    except ValueError:
        return None


def resolve_dashboard_bounds(
    *,
    range_key: str | None,
    date_from: str | None = None,
    date_to: str | None = None,
    now: datetime | None = None,
    tz: ZoneInfo | None = None,
) -> tuple[str, datetime, datetime]:
    """Devuelve (range, start_inclusive, end_exclusive) en UTC naive.

    Los cortes de día (Hoy/Ayer/semana/mes) usan la zona de negocio
    (default America/Panama), no Europe/Berlin del VPS.
    """
    zone = tz or business_timezone()
    if now is None:
        now_local = datetime.now(zone)
    elif now.tzinfo is None:
        now_local = now.replace(tzinfo=_UTC).astimezone(zone)
    else:
        now_local = now.astimezone(zone)

    today_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    key = (range_key or 'hoy').strip().lower()
    if key not in _VALID_RANGES:
        key = 'hoy'

    if key == 'custom':
        start_local = _parse_local_date(date_from, zone) or today_local
        end_day = _parse_local_date(date_to, zone) or start_local
        end_local = end_day + timedelta(days=1)
        if end_local <= start_local:
            end_local = start_local + timedelta(days=1)
        return 'custom', _to_utc_naive(start_local), _to_utc_naive(end_local)
    if key == 'ayer':
        start_local = today_local - timedelta(days=1)
        return 'ayer', _to_utc_naive(start_local), _to_utc_naive(today_local)
    if key == 'semana':
        start_local = today_local - timedelta(days=today_local.weekday())  # lunes local
        return 'semana', _to_utc_naive(start_local), _to_utc_naive(today_local + timedelta(days=1))
    if key == 'mes':
        start_local = today_local.replace(day=1)
        return 'mes', _to_utc_naive(start_local), _to_utc_naive(today_local + timedelta(days=1))
    return 'hoy', _to_utc_naive(today_local), _to_utc_naive(today_local + timedelta(days=1))


def _order_bucket(order: EposoneOrder) -> str:
    status = (order.status or '').strip().lower()
    pay = (order.payment_status or '').strip().lower()
    if status in {'cancelled', 'void'}:
        return 'closed'
    if bool(order.financially_closed) or status == 'closed':
        return 'closed'
    if pay == 'paid':
        return 'paid'
    if status == 'ready':
        return 'ready'
    if status in {'sent', 'preparing', 'in_prep'}:
        return 'preparing'
    return 'open'


def _serialize_order(row: EposoneOrder) -> dict[str, Any]:
    from nodeone.modules.eposone.timefmt import format_business_dt

    bucket = _order_bucket(row)
    return {
        'id': int(row.id),
        'en1_number': str(row.en1_number or ''),
        'local_number': str(row.local_number or '') or None,
        'status': str(row.status or ''),
        'payment_status': str(row.payment_status or ''),
        'financially_closed': bool(row.financially_closed),
        'bucket': bucket,
        'table_ref': str(row.table_ref or '') or None,
        'customer_ref': str(row.customer_ref or '') or None,
        'total': float(row.total or 0),
        'amount_paid': float(row.amount_paid or 0),
        'updated_at': row.updated_at.isoformat() if row.updated_at else '',
        'opened_at': row.opened_at.isoformat() if row.opened_at else '',
        'updated_at_local': format_business_dt(row.updated_at),
        'opened_at_local': format_business_dt(row.opened_at),
    }


class CommerceDashboardService:
    """Snapshot operativo para el dashboard back office POS."""

    @staticmethod
    def _utc_day_bounds() -> tuple[datetime, datetime]:
        now = datetime.utcnow()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=1)

    @staticmethod
    def get_snapshot(organization_id: int) -> DashboardKpiSnapshot:
        """Compat: KPIs del día UTC (Analytics y consumidores previos)."""
        board = CommerceDashboardService.build_operational_dashboard(
            int(organization_id),
            range_key='hoy',
        )
        k = board['kpis']
        return DashboardKpiSnapshot(
            orders_today=int(k['orders']),
            sales_today=float(k['sales']),
            open_registers=int(k['open_registers']),
            stock_alerts=int(k['stock_critical']),
            currency=str(k['currency']),
        )

    @staticmethod
    def build_operational_dashboard(
        organization_id: int,
        *,
        range_key: str | None = 'hoy',
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict[str, Any]:
        """Payload completo del Dashboard UX Sprint 1 (solo BackOffice)."""
        from app import db

        oid = int(organization_id)
        key, start, end = resolve_dashboard_bounds(
            range_key=range_key,
            date_from=date_from,
            date_to=date_to,
        )

        orders_q = EposoneOrder.query.filter(
            EposoneOrder.organization_id == oid,
            EposoneOrder.opened_at >= start,
            EposoneOrder.opened_at < end,
        )
        orders_count = orders_q.count()

        sales_row = (
            db.session.query(func.coalesce(func.sum(EposoneOrderPayment.amount), 0.0))
            .join(EposoneOrder, EposoneOrder.id == EposoneOrderPayment.order_id)
            .filter(
                EposoneOrder.organization_id == oid,
                EposoneOrderPayment.kind == 'payment',
                EposoneOrderPayment.created_at >= start,
                EposoneOrderPayment.created_at < end,
            )
            .scalar()
        )
        sales = round(float(sales_row or 0), 2)

        avg_ticket = round(sales / orders_count, 2) if orders_count else 0.0

        customers = (
            db.session.query(func.count(func.distinct(EposoneOrder.customer_ref)))
            .filter(
                EposoneOrder.organization_id == oid,
                EposoneOrder.opened_at >= start,
                EposoneOrder.opened_at < end,
                EposoneOrder.customer_ref.isnot(None),
                EposoneOrder.customer_ref != '',
            )
            .scalar()
        )

        open_registers = CoreCashShift.query.filter_by(
            organization_id=oid,
            status=CASH_SHIFT_OPEN,
        ).count()

        stock_critical = 0
        stock_out = 0
        for row in CoreStockBalance.query.filter_by(organization_id=oid).all():
            available = float(row.quantity_on_hand or 0) - float(row.quantity_reserved or 0)
            if available <= 0:
                stock_out += 1
                stock_critical += 1
                continue
            prod = CoreProduct.query.filter_by(
                organization_id=oid, product_ref=str(row.product_ref)
            ).first()
            min_stock = float(getattr(prod, 'min_stock', None) or 0) if prod else 0.0
            if min_stock > 0 and available <= min_stock:
                stock_critical += 1

        currency = 'USD'
        last_pay = (
            db.session.query(EposoneOrderPayment)
            .join(EposoneOrder, EposoneOrder.id == EposoneOrderPayment.order_id)
            .filter(EposoneOrder.organization_id == oid)
            .order_by(EposoneOrderPayment.id.desc())
            .first()
        )
        if last_pay is not None and last_pay.currency:
            currency = str(last_pay.currency)

        pending_orders = EposoneOrder.query.filter(
            EposoneOrder.organization_id == oid,
            EposoneOrder.financially_closed.is_(False),
            EposoneOrder.status.in_(('open', 'draft', 'sent', 'ready')),
        ).count()

        # Pedidos del rango (opened_at) para el centro — coherente con KPIs/charts
        live_rows = (
            EposoneOrder.query.filter(
                EposoneOrder.organization_id == oid,
                EposoneOrder.opened_at >= start,
                EposoneOrder.opened_at < end,
            )
            .order_by(EposoneOrder.updated_at.desc(), EposoneOrder.id.desc())
            .limit(80)
            .all()
        )
        # Si el rango no trae filas, mostrar los más recientes (sin romper la vista)
        if not live_rows:
            live_rows = (
                EposoneOrder.query.filter_by(organization_id=oid)
                .order_by(EposoneOrder.updated_at.desc(), EposoneOrder.id.desc())
                .limit(20)
                .all()
            )
        buckets: dict[str, list[dict[str, Any]]] = {
            'open': [],
            'preparing': [],
            'ready': [],
            'paid': [],
            'closed': [],
        }
        board_orders: list[dict[str, Any]] = []
        for row in live_rows:
            item = _serialize_order(row)
            buckets[item['bucket']].append(item)
            board_orders.append(item)

        # Charts — ventas por hora
        hour_rows = (
            db.session.query(
                func.extract('hour', EposoneOrderPayment.created_at).label('hh'),
                func.coalesce(func.sum(EposoneOrderPayment.amount), 0.0),
            )
            .join(EposoneOrder, EposoneOrder.id == EposoneOrderPayment.order_id)
            .filter(
                EposoneOrder.organization_id == oid,
                EposoneOrderPayment.kind == 'payment',
                EposoneOrderPayment.created_at >= start,
                EposoneOrderPayment.created_at < end,
            )
            .group_by('hh')
            .all()
        )
        sales_by_hour = [0.0] * 24
        for hh, amount in hour_rows:
            try:
                idx = int(hh)
            except (TypeError, ValueError):
                continue
            if 0 <= idx < 24:
                sales_by_hour[idx] = round(float(amount or 0), 2)

        # Top productos
        top_rows = (
            db.session.query(
                EposoneOrderItem.product_ref,
                func.coalesce(func.sum(EposoneOrderItem.qty), 0.0),
                func.coalesce(
                    func.sum(
                        (EposoneOrderItem.qty * EposoneOrderItem.unit_price)
                        - EposoneOrderItem.discount
                    ),
                    0.0,
                ),
            )
            .join(EposoneOrder, EposoneOrder.id == EposoneOrderItem.order_id)
            .filter(
                EposoneOrder.organization_id == oid,
                EposoneOrder.opened_at >= start,
                EposoneOrder.opened_at < end,
                EposoneOrderItem.line_status != 'cancelled',
            )
            .group_by(EposoneOrderItem.product_ref)
            .order_by(func.sum(EposoneOrderItem.qty).desc())
            .limit(8)
            .all()
        )
        top_products = [
            {
                'product_ref': str(ref),
                'qty': round(float(qty or 0), 2),
                'sales': round(float(amount or 0), 2),
            }
            for ref, qty, amount in top_rows
        ]

        # Formas de pago
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
        payment_methods = [
            {
                'method': str(method or 'otros'),
                'amount': round(float(amount or 0), 2),
                'count': int(count or 0),
            }
            for method, amount, count in pay_rows
        ]

        # Ventas por categoría (vía core_product.category)
        cat_rows = (
            db.session.query(
                func.coalesce(CoreProduct.category, 'sin_categoria'),
                func.coalesce(
                    func.sum(
                        (EposoneOrderItem.qty * EposoneOrderItem.unit_price)
                        - EposoneOrderItem.discount
                    ),
                    0.0,
                ),
            )
            .select_from(EposoneOrderItem)
            .join(EposoneOrder, EposoneOrder.id == EposoneOrderItem.order_id)
            .outerjoin(
                CoreProduct,
                and_(
                    CoreProduct.organization_id == oid,
                    CoreProduct.product_ref == EposoneOrderItem.product_ref,
                ),
            )
            .filter(
                EposoneOrder.organization_id == oid,
                EposoneOrder.opened_at >= start,
                EposoneOrder.opened_at < end,
                EposoneOrderItem.line_status != 'cancelled',
            )
            .group_by(func.coalesce(CoreProduct.category, 'sin_categoria'))
            .order_by(
                func.sum(
                    (EposoneOrderItem.qty * EposoneOrderItem.unit_price) - EposoneOrderItem.discount
                ).desc()
            )
            .limit(10)
            .all()
        )
        sales_by_category = [
            {'category': str(cat), 'sales': round(float(amount or 0), 2)}
            for cat, amount in cat_rows
        ]

        alerts: list[dict[str, Any]] = []
        if stock_out:
            alerts.append(
                {
                    'tone': 'danger',
                    'icon': 'fa-box',
                    'title': f'{stock_out} producto(s) sin stock',
                    'text': 'Revisá existencias antes del servicio.',
                    'href': '/admin/eposone/section/inventory',
                }
            )
        elif stock_critical:
            alerts.append(
                {
                    'tone': 'warning',
                    'icon': 'fa-exclamation-triangle',
                    'title': f'{stock_critical} alerta(s) de stock',
                    'text': 'Hay productos en nivel crítico o mínimo.',
                    'href': '/admin/eposone/section/inventory',
                }
            )
        if open_registers:
            alerts.append(
                {
                    'tone': 'info',
                    'icon': 'fa-cash-register',
                    'title': f'{open_registers} caja(s) abierta(s)',
                    'text': 'Turnos de caja activos en la organización.',
                    'href': '/admin/eposone/section/registers',
                }
            )
        if pending_orders:
            alerts.append(
                {
                    'tone': 'warning',
                    'icon': 'fa-receipt',
                    'title': f'{pending_orders} pedido(s) pendientes',
                    'text': 'Abiertos / en cocina / listos sin cierre financiero.',
                    'href': '/admin/eposone/section/orders',
                }
            )
        # Sync pendiente: sin cola BO aún → empty honesto si no hay nada
        if not alerts:
            alerts = []

        tz = business_timezone()
        generated_local = datetime.now(tz)
        # Fechas del filtro en calendario local (no UTC)
        start_local = start.replace(tzinfo=_UTC).astimezone(tz)
        end_local_inclusive = (end - timedelta(seconds=1)).replace(tzinfo=_UTC).astimezone(tz)
        return {
            'range': key,
            'date_from': start_local.strftime('%Y-%m-%d'),
            'date_to': end_local_inclusive.strftime('%Y-%m-%d'),
            'timezone': str(tz),
            'generated_at': generated_local.isoformat(),
            'kpis': {
                'orders': int(orders_count),
                'sales': sales,
                'avg_ticket': avg_ticket,
                'customers': int(customers or 0),
                'open_registers': int(open_registers),
                'stock_critical': int(stock_critical),
                'pending_orders': int(pending_orders),
                'pending_sync': 0,
                'currency': currency,
                # aliases legacy template
                'orders_today': int(orders_count),
                'sales_today': sales,
                'stock_alerts': int(stock_critical),
            },
            'system_status': {
                'online': True,
                'title': 'EN1 Conectado',
                'last_sync_label': (
                    f'Panel actualizado {generated_local.strftime("%H:%M:%S")} '
                    f'({tz.key if hasattr(tz, "key") else tz})'
                ),
                'pending_count': int(pending_orders),
            },
            'bucket_counts': {k: len(v) for k, v in buckets.items()},
            'orders': board_orders,
            'buckets': buckets,
            'charts': {
                'sales_by_hour': sales_by_hour,
                'top_products': top_products,
                'payment_methods': payment_methods,
                'sales_by_category': sales_by_category,
            },
            'alerts': alerts,
        }

    @staticmethod
    def list_recent_domain_orders(organization_id: int, *, limit: int = 12) -> list[dict[str, Any]]:
        """Últimos pedidos Hito 3 para el dashboard (read-only)."""
        rows = (
            EposoneOrder.query.filter_by(organization_id=int(organization_id))
            .order_by(EposoneOrder.updated_at.desc(), EposoneOrder.id.desc())
            .limit(max(1, min(int(limit), 50)))
            .all()
        )
        return [_serialize_order(row) for row in rows]

    @staticmethod
    def list_recent_report_events(organization_id: int, *, limit: int = 8) -> list[dict[str, Any]]:
        rows = (
            PlatformDomainEvent.query.filter(
                PlatformDomainEvent.organization_id == int(organization_id),
                PlatformDomainEvent.event_type.in_(_REPORT_EVENT_TYPES),
            )
            .order_by(PlatformDomainEvent.id.desc())
            .limit(max(1, min(int(limit), 30)))
            .all()
        )
        out: list[dict[str, Any]] = []
        for row in rows:
            payload = dict(row.payload or {})
            out.append(
                {
                    'event_type': str(row.event_type or ''),
                    'metric': str(payload.get('metric') or ''),
                    'order_ref': str(payload.get('order_ref') or ''),
                    'amount': payload.get('amount'),
                    'register_ref': str(payload.get('register_ref') or ''),
                    'created_at': row.created_at.isoformat() if row.created_at else '',
                }
            )
        return out
