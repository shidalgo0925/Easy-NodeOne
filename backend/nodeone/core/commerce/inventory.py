"""Inventario comercial — reacción a eventos de pedido (Etapa 8, dominio 6.5)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from nodeone.core.commerce.constants import (
    INVENTORY_POLICY_NONE,
    ORDER_PAYMENT_STATUS_PAID,
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_CONFIRMED,
    ORDER_STATUS_DELIVERED,
    ORDER_STATUS_REFUNDED,
    DEFAULT_INVENTORY_POLICY,
    inventory_policy_deducts_on_delivered,
    inventory_policy_deducts_on_paid,
    inventory_policy_reserves_on_confirmed,
    normalize_inventory_policy,
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
    ORDER_STATUS_CANCELLED: ('release', COMMERCE_INVENTORY_RELEASED),
    ORDER_STATUS_DELIVERED: ('deduct', COMMERCE_INVENTORY_DEDUCTED),
    ORDER_STATUS_REFUNDED: ('return', COMMERCE_INVENTORY_RETURNED),
}


class CommerceInventoryService:
    """v1 — sin tablas de stock; publica movimientos derivados del pedido."""

    @staticmethod
    def resolve_policy(message: DomainEventMessage) -> str:
        payload = dict(message.payload or {})
        raw = (payload.get('inventory_policy') or '').strip().lower()
        if raw:
            return normalize_inventory_policy(raw)
        return DEFAULT_INVENTORY_POLICY

    @staticmethod
    def _load_order(organization_id: int, order_ref: str):
        from models.commercial_core import CoreCommercialOrder

        return CoreCommercialOrder.query.filter_by(
            organization_id=int(organization_id),
            order_ref=(order_ref or '').strip(),
        ).first()

    @staticmethod
    def _order_already_deducted(organization_id: int, order_ref: str) -> bool:
        row = CommerceInventoryService._load_order(organization_id, order_ref)
        return row is not None and row.inventory_deducted_at is not None

    @staticmethod
    def _mark_order_deducted(organization_id: int, order_ref: str) -> None:
        from app import db

        row = CommerceInventoryService._load_order(organization_id, order_ref)
        if row is None or row.inventory_deducted_at is not None:
            return
        row.inventory_deducted_at = datetime.utcnow()
        db.session.commit()

    @staticmethod
    def process_order_status_changed(message: DomainEventMessage) -> dict[str, Any]:
        payload = dict(message.payload or {})
        order_ref = (payload.get('order_ref') or '').strip()
        to_status = (
            (payload.get('to_status') or payload.get('to_operational_status') or '').strip().lower()
        )
        if not order_ref or not to_status:
            return {'status': 'skipped', 'reason': 'missing_fields'}

        policy = CommerceInventoryService.resolve_policy(message)
        if policy == INVENTORY_POLICY_NONE:
            return {'status': 'skipped', 'reason': 'policy_none'}

        if to_status == ORDER_STATUS_CONFIRMED:
            if not inventory_policy_reserves_on_confirmed(policy):
                return {'status': 'skipped', 'reason': 'no_reserve_policy'}
            return CommerceInventoryService._publish(
                message,
                order_ref=order_ref,
                movement='reserve',
                event_type=COMMERCE_INVENTORY_RESERVED,
                inventory_policy=policy,
                from_status=str(payload.get('from_status') or ''),
                to_status=to_status,
            )

        if to_status == ORDER_STATUS_DELIVERED:
            if not inventory_policy_deducts_on_delivered(policy):
                return {'status': 'skipped', 'reason': 'deduct_on_delivered_disabled'}
            if CommerceInventoryService._order_already_deducted(int(message.organization_id), order_ref):
                return {'status': 'skipped', 'reason': 'already_deducted'}
            return CommerceInventoryService._publish_deduct(
                message,
                order_ref=order_ref,
                inventory_policy=policy,
                trigger='operational_status_delivered',
                from_status=str(payload.get('from_status') or ''),
                to_status=to_status,
            )

        mapping = _STATUS_TO_INVENTORY_EVENT.get(to_status)
        if mapping is None:
            return {'status': 'skipped', 'reason': 'no_inventory_action'}

        movement, event_type = mapping
        return CommerceInventoryService._publish(
            message,
            order_ref=order_ref,
            movement=movement,
            event_type=event_type,
            inventory_policy=policy,
            from_status=str(payload.get('from_status') or ''),
            to_status=to_status,
        )

    @staticmethod
    def process_payment_status_changed(message: DomainEventMessage) -> dict[str, Any]:
        payload = dict(message.payload or {})
        order_ref = (payload.get('order_ref') or '').strip()
        to_status = (payload.get('to_payment_status') or '').strip().lower()
        if not order_ref or to_status != ORDER_PAYMENT_STATUS_PAID:
            return {'status': 'skipped', 'reason': 'not_paid'}

        policy = CommerceInventoryService.resolve_policy(message)
        if policy == INVENTORY_POLICY_NONE:
            return {'status': 'skipped', 'reason': 'policy_none'}
        if not inventory_policy_deducts_on_paid(policy):
            return {'status': 'skipped', 'reason': 'deduct_on_paid_disabled'}
        if CommerceInventoryService._order_already_deducted(int(message.organization_id), order_ref):
            return {'status': 'skipped', 'reason': 'already_deducted'}

        return CommerceInventoryService._publish_deduct(
            message,
            order_ref=order_ref,
            inventory_policy=policy,
            trigger='payment_status_paid',
            from_payment_status=str(payload.get('from_payment_status') or ''),
            to_payment_status=to_status,
        )

    @staticmethod
    def _publish_deduct(
        message: DomainEventMessage,
        *,
        order_ref: str,
        inventory_policy: str,
        trigger: str,
        **extra: Any,
    ) -> dict[str, Any]:
        result = CommerceInventoryService._publish(
            message,
            order_ref=order_ref,
            movement='deduct',
            event_type=COMMERCE_INVENTORY_DEDUCTED,
            inventory_policy=inventory_policy,
            trigger=trigger,
            **extra,
        )
        if result.get('status') == 'published':
            CommerceInventoryService._mark_order_deducted(int(message.organization_id), order_ref)
        return result

    @staticmethod
    def _publish(
        message: DomainEventMessage,
        *,
        order_ref: str,
        movement: str,
        event_type: str,
        **extra: Any,
    ) -> dict[str, Any]:
        CommerceInventoryService.publish_movement(
            int(message.organization_id),
            order_ref=order_ref,
            movement=movement,
            event_type=event_type,
            source_app_id=str(message.source_app_id or 'eposone'),
            **extra,
        )
        return {'status': 'published', 'movement': movement, 'order_ref': order_ref}

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
