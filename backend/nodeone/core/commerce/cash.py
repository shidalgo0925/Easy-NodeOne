"""CashRegisterService — turnos y arqueos de caja (Etapa 12 stub)."""

from __future__ import annotations

from nodeone.core.commerce.dtos import CashShiftDTO
from nodeone.core.commerce.events import (
    COMMERCE_CASH_COUNT_RECORDED,
    COMMERCE_CASH_SHIFT_CLOSED,
    COMMERCE_CASH_SHIFT_OPENED,
)
from nodeone.core.commerce.order import CommerceNotReadyError
from nodeone.core.services.audit import AuditService


class CashRegisterService:
    @staticmethod
    def open_shift(organization_id: int, *, register_ref: str, opening_balance: float) -> CashShiftDTO:
        raise CommerceNotReadyError(
            'CashRegisterService.open_shift pendiente de core_cash_shift (Etapa 14).'
        )

    @staticmethod
    def close_shift(organization_id: int, shift_id: int, *, closing_balance: float) -> CashShiftDTO:
        raise CommerceNotReadyError(
            'CashRegisterService.close_shift pendiente de core_cash_shift (Etapa 14).'
        )

    @staticmethod
    def publish_shift_opened(
        organization_id: int,
        *,
        register_ref: str,
        opening_balance: float,
        source_app_id: str = 'eposone',
    ):
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_CASH_SHIFT_OPENED,
            {
                'register_ref': register_ref,
                'opening_balance': opening_balance,
            },
            source_app_id=source_app_id,
        )

    @staticmethod
    def publish_shift_closed(
        organization_id: int,
        *,
        register_ref: str,
        closing_balance: float,
        source_app_id: str = 'eposone',
    ):
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_CASH_SHIFT_CLOSED,
            {
                'register_ref': register_ref,
                'closing_balance': closing_balance,
            },
            source_app_id=source_app_id,
        )

    @staticmethod
    def publish_count_recorded(
        organization_id: int,
        *,
        register_ref: str,
        counted_amount: float,
        source_app_id: str = 'eposone',
    ):
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_CASH_COUNT_RECORDED,
            {
                'register_ref': register_ref,
                'counted_amount': counted_amount,
            },
            source_app_id=source_app_id,
        )
