"""KPIs operativos EPosOne — Order Domain Hito 3 + stock/caja."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func

from models.commercial_core import CoreCashShift, CoreStockBalance
from models.eposone_order import EposoneOrder, EposoneOrderPayment
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


class CommerceDashboardService:
    """Snapshot operativo para el dashboard back office POS."""

    @staticmethod
    def _utc_day_bounds() -> tuple[datetime, datetime]:
        now = datetime.utcnow()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=1)

    @staticmethod
    def get_snapshot(organization_id: int) -> DashboardKpiSnapshot:
        """KPIs del día UTC desde Order Domain (eposone_order*), no commercial_core."""
        from app import db

        oid = int(organization_id)
        start, end = CommerceDashboardService._utc_day_bounds()

        orders_today = EposoneOrder.query.filter(
            EposoneOrder.organization_id == oid,
            EposoneOrder.opened_at >= start,
            EposoneOrder.opened_at < end,
        ).count()

        sales_row = (
            db.session.query(func.coalesce(func.sum(EposoneOrderPayment.amount), 0.0))
            .join(EposoneOrder, EposoneOrder.id == EposoneOrderPayment.order_id)
            .filter(
                EposoneOrder.organization_id == oid,
                EposoneOrderPayment.created_at >= start,
                EposoneOrderPayment.created_at < end,
            )
            .scalar()
        )

        open_registers = CoreCashShift.query.filter_by(
            organization_id=oid,
            status=CASH_SHIFT_OPEN,
        ).count()

        stock_alerts = 0
        for row in CoreStockBalance.query.filter_by(organization_id=oid).all():
            available = float(row.quantity_on_hand or 0) - float(row.quantity_reserved or 0)
            if available <= 0:
                stock_alerts += 1

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

        return DashboardKpiSnapshot(
            orders_today=int(orders_today),
            sales_today=round(float(sales_row or 0), 2),
            open_registers=int(open_registers),
            stock_alerts=int(stock_alerts),
            currency=currency,
        )

    @staticmethod
    def list_recent_domain_orders(organization_id: int, *, limit: int = 12) -> list[dict[str, Any]]:
        """Últimos pedidos Hito 3 para el dashboard (read-only)."""
        rows = (
            EposoneOrder.query.filter_by(organization_id=int(organization_id))
            .order_by(EposoneOrder.updated_at.desc(), EposoneOrder.id.desc())
            .limit(max(1, min(int(limit), 50)))
            .all()
        )
        out: list[dict[str, Any]] = []
        for row in rows:
            out.append(
                {
                    'id': int(row.id),
                    'en1_number': str(row.en1_number or ''),
                    'local_number': str(row.local_number or '') or None,
                    'status': str(row.status or ''),
                    'payment_status': str(row.payment_status or ''),
                    'financially_closed': bool(row.financially_closed),
                    'total': float(row.total or 0),
                    'amount_paid': float(row.amount_paid or 0),
                    'updated_at': row.updated_at.isoformat() if row.updated_at else '',
                }
            )
        return out

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
