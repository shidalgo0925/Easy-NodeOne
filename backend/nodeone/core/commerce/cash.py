"""CashRegisterService — turnos de caja (Etapa 14)."""

from __future__ import annotations

from datetime import datetime

from models.commercial_core import CoreCashMovement, CoreCashShift
from nodeone.core.commerce.constants import (
    CASH_MOVEMENT_CASH_IN,
    CASH_MOVEMENT_CASH_OUT,
    CASH_MOVEMENT_TYPES,
    CASH_SHIFT_CLOSED,
    CASH_SHIFT_OPEN,
    CASH_SHIFT_RECONCILING,
)
from nodeone.core.commerce.dtos import CashShiftDTO
from nodeone.core.commerce.order import OrderValidationError
from nodeone.core.commerce.persistence import cash_shift_to_dto
from nodeone.core.commerce.events import (
    COMMERCE_CASH_CASHIER_CHANGED,
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
        cashier_contact_id: int | None = None,
        cashier_name: str | None = None,
        assigned_by_user_id: int | None = None,
        source_app_id: str = 'eposone',
        opened_at: datetime | None = None,
        client_shift_id: str | None = None,
    ) -> CashShiftDTO:
        from app import db

        ref = (register_ref or '').strip()
        if not ref:
            raise OrderValidationError('register_ref_required')
        client_key = (client_shift_id or '').strip() or None
        if client_key:
            prior = CoreCashShift.query.filter_by(
                organization_id=int(organization_id),
                client_shift_id=client_key,
            ).first()
            if prior is not None:
                return cash_shift_to_dto(prior)
        open_row = CoreCashShift.query.filter_by(
            organization_id=int(organization_id),
            register_ref=ref,
            status=CASH_SHIFT_OPEN,
        ).first()
        if open_row is not None:
            raise OrderValidationError('shift_already_open')
        # También bloquear si hay arqueo en curso
        reconciling = CoreCashShift.query.filter_by(
            organization_id=int(organization_id),
            register_ref=ref,
            status=CASH_SHIFT_RECONCILING,
        ).first()
        if reconciling is not None:
            raise OrderValidationError('shift_already_open')
        name = (cashier_name or '').strip() or None

        row = CoreCashShift(
            organization_id=int(organization_id),
            register_ref=ref,
            status=CASH_SHIFT_OPEN,
            cashier_contact_id=(
                int(cashier_contact_id) if cashier_contact_id is not None else None
            ),
            cashier_name=name,
            cashier_changed_at=datetime.utcnow(),
            cashier_changed_by_user_id=(
                int(assigned_by_user_id) if assigned_by_user_id is not None else None
            ),
            opening_balance=float(opening_balance or 0),
            opened_at=opened_at or datetime.utcnow(),
            client_shift_id=client_key,
            custodian_cashier_contact_id=(
                int(cashier_contact_id) if cashier_contact_id is not None else None
            ),
            custodian_cashier_name=name,
        )
        from nodeone.modules.eposone.ops_lifecycle import stamp_test_fields

        stamp_test_fields(row, int(organization_id))
        db.session.add(row)
        db.session.commit()
        CashRegisterService.publish_shift_opened(
            int(organization_id),
            register_ref=ref,
            opening_balance=float(opening_balance or 0),
            cashier_contact_id=(
                int(cashier_contact_id) if cashier_contact_id is not None else None
            ),
            cashier_name=name,
            assigned_by_user_id=(
                int(assigned_by_user_id) if assigned_by_user_id is not None else None
            ),
            source_app_id=source_app_id,
        )
        return cash_shift_to_dto(row)

    @staticmethod
    def change_cashier(
        organization_id: int,
        shift_id: int,
        *,
        cashier_contact_id: int,
        cashier_name: str | None,
        changed_by_user_id: int,
        source_app_id: str = 'eposone',
    ) -> CashShiftDTO:
        from app import db

        row = CoreCashShift.query.filter_by(
            organization_id=int(organization_id),
            id=int(shift_id),
        ).first()
        if row is None:
            raise OrderValidationError('cash_shift_not_found')
        if str(row.status or '') not in (CASH_SHIFT_OPEN, CASH_SHIFT_RECONCILING):
            raise OrderValidationError('cash_shift_not_active')
        from nodeone.modules.eposone.cash_operation_mode import is_chain_of_custody

        if is_chain_of_custody(int(organization_id)):
            # Modo B: cambio de cajero = handover Device API, no edición silenciosa BO.
            raise OrderValidationError('custody_handover_required')
        name = (cashier_name or '').strip()
        if not name:
            raise OrderValidationError('cashier_required')

        previous_contact_id = row.cashier_contact_id
        previous_name = row.cashier_name
        row.cashier_contact_id = int(cashier_contact_id)
        row.cashier_name = name
        row.cashier_changed_at = datetime.utcnow()
        row.cashier_changed_by_user_id = int(changed_by_user_id)
        # Mantener custodio alineado en SIMPLE (cajero = custodio)
        row.custodian_cashier_contact_id = int(cashier_contact_id)
        row.custodian_cashier_name = name
        db.session.commit()
        CashRegisterService.publish_cashier_changed(
            int(organization_id),
            shift_id=int(row.id),
            register_ref=str(row.register_ref),
            previous_cashier_contact_id=(
                int(previous_contact_id) if previous_contact_id is not None else None
            ),
            previous_cashier_name=previous_name,
            cashier_contact_id=int(cashier_contact_id),
            cashier_name=name,
            changed_by_user_id=int(changed_by_user_id),
            source_app_id=source_app_id,
        )
        return cash_shift_to_dto(row)

    @staticmethod
    def compute_expected_balance(shift_id: int) -> float:
        """Esperado del cajón (solo efectivo) — ADR-009 / B-R1-05c.

        Fuente única: ``cash_expected_for_shift`` (tesorería + pagos OD cash).
        """
        row = CoreCashShift.query.get(int(shift_id))
        if row is None:
            return 0.0
        from nodeone.modules.eposone.shift_close_service import cash_expected_for_shift

        return float(cash_expected_for_shift(row, include_opening=True)['expected'])

    @staticmethod
    def record_movement(
        organization_id: int,
        shift_id: int,
        movement_type: str,
        amount: float,
        *,
        payment_id: int | None = None,
        notes: str | None = None,
        cashier_contact_id: int | None = None,
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
            cashier_contact_id=(
                int(cashier_contact_id) if cashier_contact_id is not None else None
            ),
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
            cashier_contact_id=cashier_contact_id,
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
        approval: dict | None = None,
        cashier_contact_id: int | None = None,
        source_app_id: str = 'eposone',
    ) -> CashShiftDTO:
        from nodeone.core.commerce.authorization import CommerceAuthorizationService

        CommerceAuthorizationService.assert_supervisor(
            int(organization_id),
            dict(approval or {}),
            action='cash.manual_movement',
            shift_id=int(shift_id),
            source_app_id=source_app_id,
        )
        mtype = (movement_type or '').strip().lower()
        if mtype not in (CASH_MOVEMENT_CASH_IN, CASH_MOVEMENT_CASH_OUT):
            raise OrderValidationError('invalid_manual_cash_movement')
        CashRegisterService.record_movement(
            int(organization_id),
            int(shift_id),
            mtype,
            amount,
            notes=notes,
            cashier_contact_id=cashier_contact_id,
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
        cashier_contact_id: int | None = None,
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
            cashier_contact_id=cashier_contact_id,
            source_app_id=source_app_id,
        )
        CashRegisterService.publish_shift_reconciling(
            int(organization_id),
            register_ref=str(row.register_ref),
            counted_amount=counted,
            expected_balance=expected,
            variance=variance,
            cashier_contact_id=cashier_contact_id,
            source_app_id=source_app_id,
        )
        return cash_shift_to_dto(row, include_variance=False)

    @staticmethod
    def close_shift(
        organization_id: int,
        shift_id: int,
        *,
        source_app_id: str = 'eposone',
        cashier_contact_id: int | None = None,
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
        row.closed_by_cashier_contact_id = (
            int(cashier_contact_id) if cashier_contact_id is not None else None
        )
        db.session.commit()
        CashRegisterService.publish_shift_closed(
            int(organization_id),
            register_ref=str(row.register_ref),
            closing_balance=closing,
            expected_balance=expected,
            variance=variance,
            cashier_contact_id=cashier_contact_id,
            source_app_id=source_app_id,
        )
        return cash_shift_to_dto(row, include_variance=True)

    @staticmethod
    def close_shift_counted(
        organization_id: int,
        shift_id: int,
        *,
        counted_amount: float,
        source_app_id: str = 'eposone',
        cashier_contact_id: int | None = None,
        notes: str | None = None,
        closed_at: datetime | None = None,
    ) -> CashShiftDTO:
        """Cierre POS en un paso: arqueo + close (ADR-009 flujo Abrir→…→Arqueo→Cerrar)."""
        from app import db

        row = CoreCashShift.query.filter_by(
            organization_id=int(organization_id),
            id=int(shift_id),
        ).first()
        if row is None:
            raise OrderValidationError('shift_not_found')
        if row.status == CASH_SHIFT_CLOSED:
            return cash_shift_to_dto(row, include_variance=True)

        status = str(row.status or '')
        if status == CASH_SHIFT_OPEN:
            counted = round(float(counted_amount or 0), 2)
            expected = CashRegisterService.compute_expected_balance(int(row.id))
            row.status = CASH_SHIFT_RECONCILING
            row.counted_amount = counted
            row.expected_balance = expected
            db.session.flush()
            variance = round(counted - expected, 2)
            CashRegisterService.publish_count_recorded(
                int(organization_id),
                register_ref=str(row.register_ref),
                counted_amount=counted,
                cashier_contact_id=cashier_contact_id,
                source_app_id=source_app_id,
            )
            CashRegisterService.publish_shift_reconciling(
                int(organization_id),
                register_ref=str(row.register_ref),
                counted_amount=counted,
                expected_balance=expected,
                variance=variance,
                cashier_contact_id=cashier_contact_id,
                source_app_id=source_app_id,
            )
        elif status != CASH_SHIFT_RECONCILING:
            raise OrderValidationError('shift_must_reconcile_before_close')
        elif counted_amount is not None:
            # Reintento con monto: actualizar contado si aún reconciling
            row.counted_amount = round(float(counted_amount), 2)
            if row.expected_balance is None:
                row.expected_balance = CashRegisterService.compute_expected_balance(int(row.id))

        closing = round(float(row.counted_amount or 0), 2)
        expected = round(float(row.expected_balance or 0), 2)
        variance = round(closing - expected, 2)
        row.status = CASH_SHIFT_CLOSED
        row.closing_balance = closing
        row.closed_at = closed_at or datetime.utcnow()
        row.closed_by_cashier_contact_id = (
            int(cashier_contact_id) if cashier_contact_id is not None else None
        )
        db.session.commit()
        payload_extra = {'notes': notes} if notes else None
        CashRegisterService.publish_shift_closed(
            int(organization_id),
            register_ref=str(row.register_ref),
            closing_balance=closing,
            expected_balance=expected,
            variance=variance,
            cashier_contact_id=cashier_contact_id,
            source_app_id=source_app_id,
            extra=payload_extra,
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
        cashier_contact_id: int | None,
        cashier_name: str | None,
        assigned_by_user_id: int | None,
        source_app_id: str = 'eposone',
    ):
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_CASH_SHIFT_OPENED,
            {
                'register_ref': register_ref,
                'opening_balance': opening_balance,
                'cashier_contact_id': cashier_contact_id,
                'cashier_name': cashier_name,
                'assigned_by_user_id': assigned_by_user_id,
            },
            source_app_id=source_app_id,
        )

    @staticmethod
    def publish_cashier_changed(
        organization_id: int,
        *,
        shift_id: int,
        register_ref: str,
        previous_cashier_contact_id: int | None,
        previous_cashier_name: str | None,
        cashier_contact_id: int,
        cashier_name: str,
        changed_by_user_id: int,
        source_app_id: str = 'eposone',
    ):
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_CASH_CASHIER_CHANGED,
            {
                'shift_id': shift_id,
                'register_ref': register_ref,
                'previous_cashier_contact_id': previous_cashier_contact_id,
                'previous_cashier_name': previous_cashier_name,
                'cashier_contact_id': cashier_contact_id,
                'cashier_name': cashier_name,
                'changed_by_user_id': changed_by_user_id,
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
        cashier_contact_id: int | None = None,
        source_app_id: str = 'eposone',
    ):
        payload = {
            'register_ref': register_ref,
            'counted_amount': counted_amount,
            'expected_balance': expected_balance,
            'variance': variance,
        }
        if cashier_contact_id is not None:
            payload['cashier_contact_id'] = int(cashier_contact_id)
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_CASH_SHIFT_RECONCILING,
            payload,
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
        cashier_contact_id: int | None = None,
        source_app_id: str = 'eposone',
        extra: dict | None = None,
    ):
        payload: dict = {
            'register_ref': register_ref,
            'closing_balance': closing_balance,
        }
        if expected_balance is not None:
            payload['expected_balance'] = expected_balance
        if variance is not None:
            payload['variance'] = variance
        if cashier_contact_id is not None:
            payload['cashier_contact_id'] = int(cashier_contact_id)
        if extra:
            payload.update(extra)
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
        cashier_contact_id: int | None = None,
        source_app_id: str = 'eposone',
    ):
        payload = {
            'register_ref': register_ref,
            'counted_amount': counted_amount,
        }
        if cashier_contact_id is not None:
            payload['cashier_contact_id'] = int(cashier_contact_id)
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_CASH_COUNT_RECORDED,
            payload,
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
        cashier_contact_id: int | None = None,
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
        if cashier_contact_id is not None:
            payload['cashier_contact_id'] = int(cashier_contact_id)
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_CASH_MOVEMENT_RECORDED,
            payload,
            source_app_id=source_app_id,
        )
