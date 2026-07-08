"""Bus de eventos de plataforma — outbox transaccional (Etapa 8)."""

from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

# Tipos iniciales (EPosOne → Core / otras apps)
EPOSONE_ORDER_CREATED = 'eposone.order.created'
EPOSONE_ORDER_PAID = 'eposone.order.paid'
INVENTORY_STOCK_ADJUSTED = 'inventory.stock.adjusted'
SALES_INVOICE_ISSUED = 'sales.invoice.issued'


@dataclass(frozen=True)
class DomainEventMessage:
    id: int
    organization_id: int
    event_type: str
    source_app_id: str
    payload: dict[str, Any]
    created_at: datetime | None


EventHandler = Callable[[DomainEventMessage], None]

_REGISTRY: dict[str, list[EventHandler]] = defaultdict(list)


def subscribe(event_pattern: str, handler: EventHandler) -> None:
    """
    Registra un handler. ``event_pattern`` exacto o prefijo con ``.*``
    (ej. ``eposone.order.*``).
    """
    key = (event_pattern or '').strip()
    if not key:
        raise ValueError('event_pattern vacío')
    if handler not in _REGISTRY[key]:
        _REGISTRY[key].append(handler)


def clear_subscribers() -> None:
    """Solo tests — vacía el registro in-process."""
    _REGISTRY.clear()


def _handlers_for(event_type: str) -> list[EventHandler]:
    et = (event_type or '').strip()
    out: list[EventHandler] = []
    seen: set[EventHandler] = set()
    for pattern, handlers in _REGISTRY.items():
        if pattern == et:
            matched = True
        elif pattern.endswith('.*'):
            matched = et.startswith(pattern[:-1])
        else:
            matched = False
        if not matched:
            continue
        for fn in handlers:
            if fn not in seen:
                seen.add(fn)
                out.append(fn)
    return out


def _sync_dispatch_enabled() -> bool:
    return (os.environ.get('NODEONE_EVENT_BUS_SYNC') or '1').strip().lower() in (
        '1',
        'true',
        'yes',
    )


def publish_domain_event(
    organization_id: int,
    event_type: str,
    payload: dict[str, Any] | None = None,
    *,
    source_app_id: str = 'core',
    sync_dispatch: bool | None = None,
) -> DomainEventMessage:
    """
    Persiste en outbox ``platform_domain_event`` y opcionalmente despacha en el mismo proceso.
    """
    from models.platform_events import EVENT_STATUS_PENDING, PlatformDomainEvent

    from app import db

    oid = int(organization_id)
    et = (event_type or '').strip()
    if not et:
        raise ValueError('event_type vacío')

    row = PlatformDomainEvent(
        organization_id=oid,
        event_type=et,
        source_app_id=(source_app_id or 'core').strip().lower() or 'core',
        payload=dict(payload or {}),
        status=EVENT_STATUS_PENDING,
    )
    db.session.add(row)
    db.session.commit()

    msg = _row_to_message(row)
    do_sync = _sync_dispatch_enabled() if sync_dispatch is None else sync_dispatch
    if do_sync:
        dispatch_event_by_id(int(row.id))
        row = PlatformDomainEvent.query.get(int(row.id))
        if row is not None:
            msg = _row_to_message(row)
    return msg


def dispatch_event_by_id(event_id: int) -> bool:
    """Despacha un evento por id (idempotente si ya está dispatched)."""
    from models.platform_events import (
        EVENT_STATUS_DISPATCHED,
        EVENT_STATUS_FAILED,
        EVENT_STATUS_PENDING,
        PlatformDomainEvent,
    )

    from app import db

    row = PlatformDomainEvent.query.get(int(event_id))
    if row is None:
        return False
    if row.status == EVENT_STATUS_DISPATCHED:
        return True
    if row.status != EVENT_STATUS_PENDING:
        return False

    msg = _row_to_message(row)
    handlers = _handlers_for(msg.event_type)
    try:
        for handler in handlers:
            handler(msg)
        row.status = EVENT_STATUS_DISPATCHED
        row.dispatched_at = datetime.utcnow()
        row.error_message = None
        db.session.commit()
        return True
    except Exception as exc:
        row.status = EVENT_STATUS_FAILED
        row.error_message = str(exc)[:2000]
        db.session.commit()
        return False


def dispatch_pending_events(
    *,
    limit: int = 100,
    organization_id: int | None = None,
) -> int:
    """Procesa eventos pendientes; devuelve cantidad despachada."""
    from models.platform_events import EVENT_STATUS_PENDING, PlatformDomainEvent

    q = PlatformDomainEvent.query.filter_by(status=EVENT_STATUS_PENDING).order_by(
        PlatformDomainEvent.id.asc()
    )
    if organization_id is not None:
        q = q.filter_by(organization_id=int(organization_id))
    rows = q.limit(max(1, int(limit))).all()
    count = 0
    for row in rows:
        if dispatch_event_by_id(int(row.id)):
            count += 1
    return count


def _row_to_message(row) -> DomainEventMessage:
    return DomainEventMessage(
        id=int(row.id),
        organization_id=int(row.organization_id),
        event_type=str(row.event_type),
        source_app_id=str(row.source_app_id or 'core'),
        payload=dict(row.payload or {}),
        created_at=row.created_at,
    )
