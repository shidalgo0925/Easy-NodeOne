"""CashRegisterService — turnos de caja (Etapa 14)."""

from __future__ import annotations

from datetime import datetime

from models.commercial_core import CoreCashMovement, CoreCashShift
from nodeone.core.commerce.constants import (
    CASH_MOVEMENT_CASH_IN,
    CASH_MOVEMENT_CASH_OUT,
    CASH_MOVEMENT_REFUND_CASH,
    CASH_MOVEMENT_SALE_CASH,
    CASH_MOVEMENT_TYPES,
    CASH_SHIFT_CLOSED,
    CASH_SHIFT_OPEN,
    CASH_SHIFT_RECONCILING,
)
from nodeone.core.commerce.dtos import CashShiftDTO
from nodeone.core.commerce.order import OrderValidationError
from nodeone.core.commerce.persistence import cash_shift_to_dto
from nodeone.core.commerce.events import (
    COMMERCE_CASH_COUNT_RECORDED,
    COMMERCE_CASH_MOVEMENT_RECORDED,
    COMMERCE_CASH_SHIFT_CLOSED,
    COMMERCE_CASH_SHIFT_OPENED,
    COMMERCE_CASH_SHIFT_RECONCILING,
)
from nodeone.core.services.audit import AuditService


class CashRegisterService:
    @staticmethod
    def get_open_shift(organization_id: int, register_ref: str) -> CoreCashShift | None:
        ref = (register_ref or '').strip()
        if not ref:
            return None
        return CoreCashShift.query.filter_by(
            organization_id=int(organization_id),
            register_ref=ref,
            status=CASH_SHIFT_OPEN,
        ).first()

    @staticmethod
    def require_open_shift(organization_id: int, register_ref: str) -> CoreCashShift:
        ref = (register_ref or '').strip()
        if not ref:
            raise OrderValidationError('register_ref_required')
        row = CashRegisterService.get_open_shift(int(organization_id), ref)
        if row is None:
            raise OrderValidationError('cash_shift_not_open')
        return row

    @staticmethod
    def open_shift(
        organization_id: int,
        *,
        register_ref: str,
        opening_balance: float,
        source_app_id: str = 'eposone',
    ) -> CashShiftDTO:
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
            source_app_id=source_app_id,
        )
        return cash_shift_to_dto(row)

    @staticmethod
    def compute_expected_balance(shift_id: int) -> float:
        row = CoreCashShift.query.get(int(shift_id))
        if row is None:
            return 0.0
        total = float(row.opening_balance or 0)
        for amt, mtype in (
            CoreCashMovement.query.filter_by(shift_id=int(shift_id))
            .with_entities(CoreCashMovement.amount, CoreCashMovement.movement_type)
            .all()
        ):
            amount = float(amt or 0)
            movement_type = str(mtype or '')
            if movement_type in (CASH_MOVEMENT_SALE_CASH, CASH_MOVEMENT_CASH_IN):
                total += amount
            elif movement_type in (CASH_MOVEMENT_REFUND_CASH, CASH_MOVEMENT_CASH_OUT):
                total -= amount
        return round(total, 2)

    @staticmethod
    def record_movement(
        organization_id: int,
        shift_id: int,
        movement_type: str,
        amount: float,
        *,
        payment_id: int | None = None,
        notes: str | None = None,
        source_app_id: str = 'eposone',
    ) -> None:
        from app import db

        mtype = (movement_type or '').strip().lower()
        if mtype not in CASH_MOVEMENT_TYPES:
            raise OrderValidationError('invalid_cash_movement_type')
        amt = round(float(amount or 0), 2)
        if amt <= 0:
            raise OrderValidationError('amount_required')

        shift = CoreCashShift.query.filter_by(
            organization_id=int(organization_id),
            id=int(shift_id),
        ).first()
        if shift is None:
            raise OrderValidationError('shift_not_found')
        if str(shift.status or '') != CASH_SHIFT_OPEN:
            raise OrderValidationError('cash_shift_not_accepting_movements')

        mv = CoreCashMovement(
            organization_id=int(organization_id),
            shift_id=int(shift_id),
            movement_type=mtype,
            amount=amt,
            payment_id=int(payment_id) if payment_id else None,
            notes=(notes or None),
        )
        db.session.add(mv)
        db.session.commit()
        CashRegisterService.publish_movement_recorded(
            int(organization_id),
            register_ref=str(shift.register_ref),
            movement_type=mtype,
            amount=amt,
            shift_id=int(shift_id),
            payment_id=payment_id,
            source_app_id=source_app_id,
        )

    @staticmethod
    def record_manual_movement(
        organization_id: int,
        shift_id: int,
        movement_type: str,
        amount: float,
        *,
        notes: str | None = None,
        source_app_id: str = 'eposone',
    ) -> CashShiftDTO:
        mtype = (movement_type or '').strip().lower()
        if mtype not in (CASH_MOVEMENT_CASH_IN, CASH_MOVEMENT_CASH_OUT):
            raise OrderValidationError('invalid_manual_cash_movement')
        CashRegisterService.record_movement(
            int(organization_id),
            int(shift_id),
            mtype,
            amount,
            notes=notes,
            source_app_id=source_app_id,
        )
        row = CoreCashShift.query.filter_by(organization_id=int(organization_id), id=int(shift_id)).first()
        if row is None:
            raise OrderValidationError('shift_not_found')
        return cash_shift_to_dto(row)

    @staticmethod
    def begin_reconcile(
        organization_id: int,
        shift_id: int,
        *,
        counted_amount: float,
        source_app_id: str = 'eposone',
    ) -> CashShiftDTO:
        from app import db

        row = CoreCashShift.query.filter_by(
            organization_id=int(organization_id),
            id=int(shift_id),
        ).first()
        if row is None:
            raise OrderValidationError('shift_not_found')
        if str(row.status or '') != CASH_SHIFT_OPEN:
            raise OrderValidationError('shift_not_open')

        counted = round(float(counted_amount or 0), 2)
        expected = CashRegisterService.compute_expected_balance(int(row.id))
        row.status = CASH_SHIFT_RECONCILING
        row.counted_amount = counted
        row.expected_balance = expected
        db.session.commit()

        variance = round(counted - expected, 2)
        CashRegisterService.publish_count_recorded(
            int(organization_id),
            register_ref=str(row.register_ref),
            counted_amount=counted,
            source_app_id=source_app_id,
        )
        CashRegisterService.publish_shift_reconciling(
            int(organization_id),
            register_ref=str(row.register_ref),
            counted_amount=counted,
            expected_balance=expected,
            variance=variance,
            source_app_id=source_app_id,
        )
        return cash_shift_to_dto(row, include_variance=False)

    @staticmethod
    def close_shift(
        organization_id: int,
        shift_id: int,
        *,
        source_app_id: str = 'eposone',
    ) -> CashShiftDTO:
        from app import db

        row = CoreCashShift.query.filter_by(
            organization_id=int(organization_id),
            id=int(shift_id),
        ).first()
        if row is None:
            raise OrderValidationError('shift_not_found')
        if row.status == CASH_SHIFT_CLOSED:
            return cash_shift_to_dto(row, include_variance=True)
        if str(row.status or '') != CASH_SHIFT_RECONCILING:
            raise OrderValidationError('shift_must_reconcile_before_close')

        closing = round(float(row.counted_amount or 0), 2)
        expected = round(float(row.expected_balance or 0), 2)
        variance = round(closing - expected, 2)
        row.status = CASH_SHIFT_CLOSED
        row.closing_balance = closing
        row.closed_at = datetime.utcnow()
        db.session.commit()
        CashRegisterService.publish_shift_closed(
            int(organization_id),
            register_ref=str(row.register_ref),
            closing_balance=closing,
            expected_balance=expected,
            variance=variance,
            source_app_id=source_app_id,
        )
        return cash_shift_to_dto(row, include_variance=True)

    @staticmethod
    def assert_cash_refund_allowed(organization_id: int, shift_id: int) -> None:
        row = CoreCashShift.query.filter_by(
            organization_id=int(organization_id),
            id=int(shift_id),
        ).first()
        if row is None:
            raise OrderValidationError('cash_shift_not_found')
        if str(row.status or '') != CASH_SHIFT_OPEN:
            raise OrderValidationError('cash_refund_requires_open_shift')

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
    def publish_shift_reconciling(
        organization_id: int,
        *,
        register_ref: str,
        counted_amount: float,
        expected_balance: float,
        variance: float,
        source_app_id: str = 'eposone',
    ):
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_CASH_SHIFT_RECONCILING,
            {
                'register_ref': register_ref,
                'counted_amount': counted_amount,
                'expected_balance': expected_balance,
                'variance': variance,
            },
            source_app_id=source_app_id,
        )

    @staticmethod
    def publish_shift_closed(
        organization_id: int,
        *,
        register_ref: str,
        closing_balance: float,
        expected_balance: float | None = None,
        variance: float | None = None,
        source_app_id: str = 'eposone',
    ):
        payload: dict = {
            'register_ref': register_ref,
            'closing_balance': closing_balance,
        }
        if expected_balance is not None:
            payload['expected_balance'] = expected_balance
        if variance is not None:
            payload['variance'] = variance
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_CASH_SHIFT_CLOSED,
            payload,
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

    @staticmethod
    def publish_movement_recorded(
        organization_id: int,
        *,
        register_ref: str,
        movement_type: str,
        amount: float,
        shift_id: int,
        payment_id: int | None = None,
        source_app_id: str = 'eposone',
    ):
        payload: dict = {
            'register_ref': register_ref,
            'movement_type': movement_type,
            'amount': amount,
            'shift_id': shift_id,
        }
        if payment_id is not None:
            payload['payment_id'] = payment_id
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_CASH_MOVEMENT_RECORDED,
            payload,
            source_app_id=source_app_id,
        )
