"""DeliveryService — entregas (Etapa 12 stub)."""

from __future__ import annotations

from nodeone.core.commerce.dtos import DeliveryDTO
from nodeone.core.commerce.events import COMMERCE_DELIVERY_COMPLETED, COMMERCE_DELIVERY_STARTED
from nodeone.core.commerce.order import CommerceNotReadyError
from nodeone.core.services.audit import AuditService


class DeliveryService:
    @staticmethod
    def get(organization_id: int, delivery_id: int) -> DeliveryDTO | None:
        raise CommerceNotReadyError(
            'DeliveryService pendiente de core_commercial_delivery (Etapa 14).'
        )

    @staticmethod
    def publish_started(
        organization_id: int,
        *,
        order_ref: str,
        source_app_id: str = 'eposone',
    ):
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_DELIVERY_STARTED,
            {'order_ref': order_ref},
            source_app_id=source_app_id,
        )

    @staticmethod
    def publish_completed(
        organization_id: int,
        *,
        order_ref: str,
        source_app_id: str = 'eposone',
    ):
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_DELIVERY_COMPLETED,
            {'order_ref': order_ref},
            source_app_id=source_app_id,
        )
