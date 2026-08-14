"""Handlers bus — aplicar movimientos de stock desde eventos inventario (Etapa 7 slice 14)."""

from __future__ import annotations

from nodeone.core.commerce.events import (
    COMMERCE_INVENTORY_DEDUCTED,
    COMMERCE_INVENTORY_RELEASED,
    COMMERCE_INVENTORY_RESERVED,
    COMMERCE_INVENTORY_RETURNED,
)
from nodeone.core.platform.events import DomainEventMessage, subscribe

_REGISTERED = False

_INVENTORY_EVENT_TO_MOVEMENT = {
    COMMERCE_INVENTORY_RESERVED: 'reserve',
    COMMERCE_INVENTORY_RELEASED: 'release',
    COMMERCE_INVENTORY_DEDUCTED: 'deduct',
    COMMERCE_INVENTORY_RETURNED: 'return',
}


def _on_inventory_movement(message: DomainEventMessage) -> None:
    payload = dict(message.payload or {})
    order_ref = (payload.get('order_ref') or '').strip()
    movement = (payload.get('movement') or _INVENTORY_EVENT_TO_MOVEMENT.get(message.event_type or '')).strip().lower()
    if not order_ref or not movement:
        return
    try:
        from nodeone.core.platform.connected_inventory import apply_connected_order_movement

        apply_connected_order_movement(
            int(message.organization_id),
            order_ref,
            movement,
            source_system='EP1',
        )
    except Exception:
        pass


def register_commerce_stock_handlers() -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    for event_type in _INVENTORY_EVENT_TO_MOVEMENT:
        subscribe(event_type, _on_inventory_movement)
    _REGISTERED = True
