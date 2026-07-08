"""PaymentService — pagos comerciales (Etapa 12)."""

from __future__ import annotations

from typing import Any

from nodeone.core.commerce.dtos import PaymentDTO
from nodeone.core.commerce.events import (
    COMMERCE_PAYMENT_CAPTURED,
    COMMERCE_PAYMENT_FAILED,
    COMMERCE_PAYMENT_INITIATED,
    COMMERCE_PAYMENT_REFUNDED,
)
from nodeone.core.services.audit import AuditService


class PaymentService:
    """Contrato de pagos POS/ventas. Persistencia en Etapa 14."""

    @staticmethod
    def get(organization_id: int, payment_id: int) -> PaymentDTO | None:
        from nodeone.core.commerce.order import CommerceNotReadyError

        raise CommerceNotReadyError(
            'PaymentService.get pendiente de core_commercial_payment (Etapa 14).'
        )

    @staticmethod
    def capture(organization_id: int, data: dict[str, Any]) -> PaymentDTO:
        from nodeone.core.commerce.order import CommerceNotReadyError

        raise CommerceNotReadyError(
            'PaymentService.capture pendiente de core_commercial_payment (Etapa 14).'
        )

    @staticmethod
    def refund(organization_id: int, payment_id: int, *, amount: float | None = None) -> PaymentDTO:
        from nodeone.core.commerce.order import CommerceNotReadyError

        raise CommerceNotReadyError(
            'PaymentService.refund pendiente de core_commercial_payment (Etapa 14).'
        )

    @staticmethod
    def publish_initiated(
        organization_id: int,
        *,
        payment_ref: str,
        order_ref: str,
        amount: float,
        payment_type: str,
        source_app_id: str = 'eposone',
    ):
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_PAYMENT_INITIATED,
            {
                'payment_ref': payment_ref,
                'order_ref': order_ref,
                'amount': amount,
                'payment_type': payment_type,
            },
            source_app_id=source_app_id,
        )

    @staticmethod
    def publish_captured(
        organization_id: int,
        *,
        payment_ref: str,
        order_ref: str,
        amount: float,
        source_app_id: str = 'eposone',
    ):
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_PAYMENT_CAPTURED,
            {
                'payment_ref': payment_ref,
                'order_ref': order_ref,
                'amount': amount,
            },
            source_app_id=source_app_id,
        )

    @staticmethod
    def publish_failed(
        organization_id: int,
        *,
        payment_ref: str,
        order_ref: str,
        reason: str,
        source_app_id: str = 'eposone',
    ):
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_PAYMENT_FAILED,
            {
                'payment_ref': payment_ref,
                'order_ref': order_ref,
                'reason': reason,
            },
            source_app_id=source_app_id,
        )

    @staticmethod
    def publish_refunded(
        organization_id: int,
        *,
        payment_ref: str,
        order_ref: str,
        amount: float,
        source_app_id: str = 'eposone',
    ):
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_PAYMENT_REFUNDED,
            {
                'payment_ref': payment_ref,
                'order_ref': order_ref,
                'amount': amount,
            },
            source_app_id=source_app_id,
        )
