"""OrderService — pedidos comerciales (Etapa 12)."""

from __future__ import annotations

from typing import Any

from nodeone.core.commerce.constants import can_transition_order_status
from nodeone.core.commerce.dtos import OrderDTO
from nodeone.core.commerce.events import (
    COMMERCE_ORDER_CANCELLED,
    COMMERCE_ORDER_CONFIRMED,
    COMMERCE_ORDER_CREATED,
    COMMERCE_ORDER_STATUS_CHANGED,
)
from nodeone.core.services.audit import AuditService


class CommerceNotReadyError(NotImplementedError):
    """Tablas core_commercial_order pendientes (Etapa 14)."""


class OrderService:
    """Contrato de pedidos. Persistencia en EPosOne MVP (Etapa 14)."""

    @staticmethod
    def can_transition(current_status: str, target_status: str) -> bool:
        return can_transition_order_status(current_status, target_status)

    @staticmethod
    def get(organization_id: int, order_id: int) -> OrderDTO | None:
        raise CommerceNotReadyError(
            'OrderService.get pendiente de core_commercial_order (Etapa 14).'
        )

    @staticmethod
    def create(organization_id: int, data: dict[str, Any], *, source_app_id: str = 'eposone') -> OrderDTO:
        raise CommerceNotReadyError(
            'OrderService.create pendiente de core_commercial_order (Etapa 14).'
        )

    @staticmethod
    def transition_status(
        organization_id: int,
        order_id: int,
        target_status: str,
        *,
        source_app_id: str = 'eposone',
    ) -> OrderDTO:
        raise CommerceNotReadyError(
            'OrderService.transition_status pendiente de core_commercial_order (Etapa 14).'
        )

    @staticmethod
    def publish_created(
        organization_id: int,
        *,
        order_ref: str,
        status: str,
        grand_total: float | None = None,
        source_app_id: str = 'eposone',
        extra: dict[str, Any] | None = None,
    ):
        payload: dict[str, Any] = {'order_ref': order_ref, 'status': status}
        if grand_total is not None:
            payload['grand_total'] = grand_total
        if extra:
            payload.update(extra)
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_ORDER_CREATED,
            payload,
            source_app_id=source_app_id,
        )

    @staticmethod
    def publish_status_changed(
        organization_id: int,
        *,
        order_ref: str,
        from_status: str,
        to_status: str,
        source_app_id: str = 'eposone',
    ):
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_ORDER_STATUS_CHANGED,
            {
                'order_ref': order_ref,
                'from_status': from_status,
                'to_status': to_status,
            },
            source_app_id=source_app_id,
        )

    @staticmethod
    def publish_confirmed(organization_id: int, *, order_ref: str, source_app_id: str = 'eposone'):
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_ORDER_CONFIRMED,
            {'order_ref': order_ref},
            source_app_id=source_app_id,
        )

    @staticmethod
    def publish_cancelled(
        organization_id: int,
        *,
        order_ref: str,
        reason: str | None = None,
        source_app_id: str = 'eposone',
    ):
        payload: dict[str, Any] = {'order_ref': order_ref}
        if reason:
            payload['reason'] = reason
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_ORDER_CANCELLED,
            payload,
            source_app_id=source_app_id,
        )
