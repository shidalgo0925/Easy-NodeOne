"""Borrado de transacciones del día — solo lab / platform admin (QA)."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from nodeone.core.timezone_service import TimeZoneService

logger = logging.getLogger(__name__)

CONFIRM_PHRASE = 'BORRAR HOY'
BUSINESS_TZ = 'America/Panama'


def wipe_tool_enabled() -> bool:
    """Activo solo en desarrollo o con flag explícito (nunca por defecto en prod)."""
    if (os.environ.get('EPOSONE_ALLOW_DEV_WIPE') or '').strip() in {'1', 'true', 'yes'}:
        return True
    env = (os.environ.get('FLASK_ENV') or os.environ.get('ENV') or '').strip().lower()
    return env in {'development', 'dev', 'local'}


def _day_bounds_utc_naive() -> tuple[datetime, datetime, str]:
    zone = ZoneInfo(BUSINESS_TZ)
    day_local = datetime.now(zone).strftime('%Y-%m-%d')
    start, end = TimeZoneService.day_bounds_utc_naive(day_local, zone)
    return start, end, day_local


def _day_query(model, organization_id: int, ts_col, start: datetime, end: datetime):
    return (
        model.query.filter_by(organization_id=int(organization_id))
        .filter(ts_col >= start, ts_col < end)
    )


def preview_today(organization_id: int) -> dict[str, Any]:
    from models.commercial_core import CoreCashShift, CoreCommercialOrder
    from models.eposone_order import EposoneOrder

    oid = int(organization_id)
    start, end, day_local = _day_bounds_utc_naive()
    orders = (
        _day_query(EposoneOrder, oid, EposoneOrder.opened_at, start, end)
        .order_by(EposoneOrder.id.asc())
        .all()
    )
    shifts = (
        _day_query(CoreCashShift, oid, CoreCashShift.opened_at, start, end)
        .order_by(CoreCashShift.id.asc())
        .all()
    )
    commercial_count = (
        _day_query(CoreCommercialOrder, oid, CoreCommercialOrder.created_at, start, end).count()
    )
    return {
        'timezone': BUSINESS_TZ,
        'day_local': day_local,
        'orders_count': len(orders),
        'orders': [
            {
                'id': int(o.id),
                'en1_number': o.en1_number,
                'status': o.status,
                'payment_status': o.payment_status,
                'table_ref': o.table_ref,
            }
            for o in orders[:50]
        ],
        'shifts_count': len(shifts),
        'shifts': [
            {
                'id': int(s.id),
                'register_ref': s.register_ref,
                'status': s.status,
                'cashier_name': s.cashier_name,
            }
            for s in shifts[:50]
        ],
        'commercial_count': int(commercial_count),
        'confirm_phrase': CONFIRM_PHRASE,
    }


def wipe_today(organization_id: int, *, actor: str | None = None) -> dict[str, Any]:
    """Elimina pedidos POS del día (+ hijos CASCADE), turnos y commercial orders del día."""
    from app import db
    from models.commercial_core import CoreCashShift, CoreCommercialOrder
    from models.eposone_order import EposoneOrder

    oid = int(organization_id)
    start, end, day_local = _day_bounds_utc_naive()

    deleted_orders = _day_query(
        EposoneOrder, oid, EposoneOrder.opened_at, start, end
    ).delete(synchronize_session=False)
    deleted_shifts = _day_query(
        CoreCashShift, oid, CoreCashShift.opened_at, start, end
    ).delete(synchronize_session=False)
    deleted_commercial = _day_query(
        CoreCommercialOrder, oid, CoreCommercialOrder.created_at, start, end
    ).delete(synchronize_session=False)
    db.session.commit()

    result = {
        'organization_id': oid,
        'deleted_orders': int(deleted_orders or 0),
        'deleted_shifts': int(deleted_shifts or 0),
        'deleted_commercial': int(deleted_commercial or 0),
        'day_local': day_local,
        'actor': actor,
    }
    logger.warning(
        'eposone.dev_wipe_today org=%s actor=%s orders=%s shifts=%s commercial=%s day=%s',
        oid,
        actor,
        result['deleted_orders'],
        result['deleted_shifts'],
        result['deleted_commercial'],
        result['day_local'],
    )
    return result
