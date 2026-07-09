"""KPIs operativos EPosOne — lectura directa + eventos de reporte (Etapa 8)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func

from models.commercial_core import (
    CoreCashShift,
    CoreCommercialOrder,
    CoreCommercialPayment,
    CoreStockBalance,
)
from models.platform_events import PlatformDomainEvent
from nodeone.core.commerce.constants import CASH_SHIFT_OPEN, PAYMENT_STATUS_CAPTURED
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
        oid = int(organization_id)
        start, end = CommerceDashboardService._utc_day_bounds()

        orders_today = CoreCommercialOrder.query.filter(
            CoreCommercialOrder.organization_id == oid,
            CoreCommercialOrder.created_at >= start,
            CoreCommercialOrder.created_at < end,
        ).count()

        sales_row = (
            CoreCommercialPayment.query.filter(
                CoreCommercialPayment.organization_id == oid,
                CoreCommercialPayment.status == PAYMENT_STATUS_CAPTURED,
                CoreCommercialPayment.captured_at >= start,
                CoreCommercialPayment.captured_at < end,
            )
            .with_entities(func.coalesce(func.sum(CoreCommercialPayment.amount), 0.0))
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
        last_order = (
            CoreCommercialOrder.query.filter_by(organization_id=oid)
            .order_by(CoreCommercialOrder.id.desc())
            .first()
        )
        if last_order is not None and last_order.currency:
            currency = str(last_order.currency)

        return DashboardKpiSnapshot(
            orders_today=int(orders_today),
            sales_today=round(float(sales_row or 0), 2),
            open_registers=int(open_registers),
            stock_alerts=int(stock_alerts),
            currency=currency,
        )

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
