"""Handlers bus — inventario comercial derivado de pedidos (Etapa 8)."""

from __future__ import annotations

from nodeone.core.commerce.events import (
    COMMERCE_ORDER_PAYMENT_STATUS_CHANGED,
    COMMERCE_ORDER_STATUS_CHANGED,
)
from nodeone.core.commerce.inventory import CommerceInventoryService
from nodeone.core.platform.events import DomainEventMessage, subscribe

_REGISTERED = False


def _on_order_status_changed(message: DomainEventMessage) -> None:
    try:
        CommerceInventoryService.process_order_status_changed(message)
    except Exception:
        pass


def _on_payment_status_changed(message: DomainEventMessage) -> None:
    try:
        CommerceInventoryService.process_payment_status_changed(message)
    except Exception:
        pass


def register_commerce_inventory_handlers() -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    subscribe(COMMERCE_ORDER_STATUS_CHANGED, _on_order_status_changed)
    subscribe(COMMERCE_ORDER_PAYMENT_STATUS_CHANGED, _on_payment_status_changed)
    _REGISTERED = True
