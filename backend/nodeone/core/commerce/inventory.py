"""Inventario comercial — reacción a eventos de pedido (Etapa 8, dominio 6.5)."""

from __future__ import annotations

from typing import Any

from nodeone.core.commerce.constants import (
    ORDER_PAYMENT_STATUS_PAID,
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_CONFIRMED,
    ORDER_STATUS_DELIVERED,
    ORDER_STATUS_REFUNDED,
)
from nodeone.core.commerce.events import (
    COMMERCE_INVENTORY_DEDUCTED,
    COMMERCE_INVENTORY_RELEASED,
    COMMERCE_INVENTORY_RESERVED,
    COMMERCE_INVENTORY_RETURNED,
)
from nodeone.core.platform.events import DomainEventMessage
from nodeone.core.services.audit import AuditService

_STATUS_TO_INVENTORY_EVENT: dict[str, tuple[str, str]] = {
    ORDER_STATUS_CONFIRMED: ('reserve', COMMERCE_INVENTORY_RESERVED),
    ORDER_STATUS_CANCELLED: ('release', COMMERCE_INVENTORY_RELEASED),
    ORDER_STATUS_DELIVERED: ('deduct', COMMERCE_INVENTORY_DEDUCTED),
    ORDER_STATUS_REFUNDED: ('return', COMMERCE_INVENTORY_RETURNED),
}


class CommerceInventoryService:
    """v1 — sin tablas de stock; publica movimientos derivados del pedido."""

    @staticmethod
    def process_order_status_changed(message: DomainEventMessage) -> dict[str, Any]:
        payload = dict(message.payload or {})
        order_ref = (payload.get('order_ref') or '').strip()
        to_status = (
            (payload.get('to_status') or payload.get('to_operational_status') or '').strip().lower()
        )
        if not order_ref or not to_status:
            return {'status': 'skipped', 'reason': 'missing_fields'}

        mapping = _STATUS_TO_INVENTORY_EVENT.get(to_status)
        if mapping is None:
            return {'status': 'skipped', 'reason': 'no_inventory_action'}

        movement, event_type = mapping
        CommerceInventoryService.publish_movement(
            int(message.organization_id),
            order_ref=order_ref,
            movement=movement,
            event_type=event_type,
            from_status=str(payload.get('from_status') or ''),
            to_status=to_status,
            source_app_id=str(message.source_app_id or 'eposone'),
        )
        return {'status': 'published', 'movement': movement, 'order_ref': order_ref}

    @staticmethod
    def process_payment_status_changed(message: DomainEventMessage) -> dict[str, Any]:
        """Retail deduct_on_paid — solo si aún no hubo deduct por delivered."""
        payload = dict(message.payload or {})
        order_ref = (payload.get('order_ref') or '').strip()
        to_status = (payload.get('to_payment_status') or '').strip().lower()
        if not order_ref or to_status != ORDER_PAYMENT_STATUS_PAID:
            return {'status': 'skipped', 'reason': 'not_paid'}

        CommerceInventoryService.publish_movement(
            int(message.organization_id),
            order_ref=order_ref,
            movement='deduct',
            event_type=COMMERCE_INVENTORY_DEDUCTED,
            trigger='payment_status_paid',
            from_payment_status=str(payload.get('from_payment_status') or ''),
            to_payment_status=to_status,
            source_app_id=str(message.source_app_id or 'eposone'),
        )
        return {'status': 'published', 'movement': 'deduct', 'order_ref': order_ref}

    @staticmethod
    def publish_movement(
        organization_id: int,
        *,
        order_ref: str,
        movement: str,
        event_type: str,
        source_app_id: str = 'eposone',
        **extra: Any,
    ):
        payload: dict[str, Any] = {
            'order_ref': order_ref,
            'movement': movement,
        }
        payload.update(extra)
        return AuditService.publish_domain_event(
            organization_id,
            event_type,
            payload,
            source_app_id=source_app_id,
        )
