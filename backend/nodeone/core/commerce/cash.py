"""CashRegisterService — turnos de caja (Etapa 14)."""

from __future__ import annotations

from datetime import datetime

from models.commercial_core import CoreCashShift
from nodeone.core.commerce.constants import CASH_SHIFT_CLOSED, CASH_SHIFT_OPEN
from nodeone.core.commerce.dtos import CashShiftDTO
from nodeone.core.commerce.order import OrderValidationError
from nodeone.core.commerce.persistence import cash_shift_to_dto
from nodeone.core.commerce.events import (
    COMMERCE_CASH_COUNT_RECORDED,
    COMMERCE_CASH_SHIFT_CLOSED,
    COMMERCE_CASH_SHIFT_OPENED,
)
from nodeone.core.services.audit import AuditService


class CashRegisterService:
    @staticmethod
    def open_shift(organization_id: int, *, register_ref: str, opening_balance: float) -> CashShiftDTO:
        from app import db

        ref = (register_ref or '').strip()
        if not ref:
            raise OrderValidationError('register_ref_required')
        open_row = CoreCashShift.query.filter_by(
            organization_id=int(organization_id),
            register_ref=ref,
            status=CASH_SHIFT_OPEN,
        ).first()
        if open_row is not None:
            raise OrderValidationError('shift_already_open')

        row = CoreCashShift(
            organization_id=int(organization_id),
            register_ref=ref,
            status=CASH_SHIFT_OPEN,
            opening_balance=float(opening_balance or 0),
            opened_at=datetime.utcnow(),
        )
        db.session.add(row)
        db.session.commit()
        CashRegisterService.publish_shift_opened(
            int(organization_id),
            register_ref=ref,
            opening_balance=float(opening_balance or 0),
        )
        return cash_shift_to_dto(row)

    @staticmethod
    def close_shift(organization_id: int, shift_id: int, *, closing_balance: float) -> CashShiftDTO:
        from app import db

        row = CoreCashShift.query.filter_by(
            organization_id=int(organization_id),
            id=int(shift_id),
        ).first()
        if row is None:
            raise OrderValidationError('shift_not_found')
        if row.status == CASH_SHIFT_CLOSED:
            return cash_shift_to_dto(row)

        row.status = CASH_SHIFT_CLOSED
        row.closing_balance = float(closing_balance or 0)
        row.closed_at = datetime.utcnow()
        db.session.commit()
        CashRegisterService.publish_shift_closed(
            int(organization_id),
            register_ref=str(row.register_ref),
            closing_balance=float(closing_balance or 0),
        )
        return cash_shift_to_dto(row)

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
