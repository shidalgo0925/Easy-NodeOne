"""PaymentService — pagos comerciales (Etapa 14)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from models.commercial_core import CoreCommercialOrder, CoreCommercialPayment
from nodeone.core.commerce.constants import (
    ORDER_FISCAL_STATUS_NOT_REQUIRED,
    ORDER_FISCAL_STATUS_PENDING,
    ORDER_FISCAL_STATUS_INVOICED,
    ORDER_PAYMENT_STATUS_PAID,
    ORDER_STATUS_REFUNDED,
    PAYMENT_STATUS_CAPTURED,
    PAYMENT_STATUS_PARTIAL_REFUND,
    PAYMENT_STATUS_REFUNDED,
    PAYMENT_TYPE_CASH,
    can_transition_order_status,
)

_REFUNDABLE_PAYMENT_STATUSES = frozenset({PAYMENT_STATUS_CAPTURED, PAYMENT_STATUS_PARTIAL_REFUND})
from nodeone.core.commerce.dtos import PaymentDTO
from nodeone.core.commerce.events import (
    COMMERCE_PAYMENT_CAPTURED,
    COMMERCE_PAYMENT_FAILED,
    COMMERCE_PAYMENT_INITIATED,
    COMMERCE_PAYMENT_REFUNDED,
)
from nodeone.core.commerce.order import OrderService, OrderValidationError
from nodeone.core.commerce.persistence import payment_to_dto
from nodeone.core.services.audit import AuditService


class PaymentService:
    @staticmethod
    def get(organization_id: int, payment_id: int) -> PaymentDTO | None:
        row = CoreCommercialPayment.query.filter_by(
            organization_id=int(organization_id),
            id=int(payment_id),
        ).first()
        if row is None:
            return None
        order = CoreCommercialOrder.query.get(int(row.order_id))
        order_ref = str(order.order_ref) if order else ''
        return payment_to_dto(row, order_ref=order_ref)

    @staticmethod
    def capture(organization_id: int, data: dict[str, Any], *, source_app_id: str = 'eposone') -> PaymentDTO:
        from app import db

        oid = int(organization_id)
        order_id = data.get('order_id')
        order_ref = (data.get('order_ref') or '').strip()
        if order_id:
            order = CoreCommercialOrder.query.filter_by(organization_id=oid, id=int(order_id)).first()
        elif order_ref:
            order = CoreCommercialOrder.query.filter_by(organization_id=oid, order_ref=order_ref).first()
        else:
            raise OrderValidationError('order_id_or_ref_required')
        if order is None:
            raise OrderValidationError('order_not_found')

        amount = float(data.get('amount') or 0)
        if amount <= 0:
            raise OrderValidationError('amount_required')

        payment_type = str(data.get('payment_type') or PAYMENT_TYPE_CASH).strip().lower() or PAYMENT_TYPE_CASH
        payment_ref = (data.get('payment_ref') or '').strip() or PaymentService._next_payment_ref(oid)

        cash_shift_id = None
        if payment_type == PAYMENT_TYPE_CASH:
            from nodeone.core.commerce.cash import CashRegisterService

            register_ref = (data.get('register_ref') or '').strip()
            shift = CashRegisterService.require_open_shift(oid, register_ref)
            cash_shift_id = int(shift.id)

        PaymentService.publish_initiated(
            oid,
            payment_ref=payment_ref,
            order_ref=str(order.order_ref),
            amount=amount,
            payment_type=payment_type,
            source_app_id=source_app_id,
        )

        row = CoreCommercialPayment(
            organization_id=oid,
            order_id=int(order.id),
            payment_ref=payment_ref,
            status=PAYMENT_STATUS_CAPTURED,
            payment_type=payment_type,
            amount=amount,
            currency=str(order.currency or 'USD'),
            captured_at=datetime.utcnow(),
            cash_shift_id=cash_shift_id,
        )
        db.session.add(row)
        prev_payment_status = str(order.payment_status or 'unpaid')
        order.amount_paid = round(float(order.amount_paid or 0) + amount, 2)
        order.version = int(order.version or 1) + 1
        new_payment_status = order.sync_payment_status()
        skip_fiscal = bool(data.get('skip_fiscal'))
        prev_fiscal_status = order.maybe_mark_fiscal_pending(skip_fiscal=skip_fiscal)
        db.session.commit()

        if new_payment_status != prev_payment_status:
            OrderService.publish_payment_status_changed(
                oid,
                order_ref=str(order.order_ref),
                from_status=prev_payment_status,
                to_status=new_payment_status,
                source_app_id=source_app_id,
            )
        if prev_fiscal_status is not None:
            OrderService.publish_fiscal_status_changed(
                oid,
                order_ref=str(order.order_ref),
                from_status=prev_fiscal_status,
                to_status=ORDER_FISCAL_STATUS_PENDING,
                source_app_id=source_app_id,
            )
            try:
                from nodeone.core.commerce.fiscal import CommerceFiscalService

                CommerceFiscalService.request_for_order(oid, int(order.id), source_app_id=source_app_id)
            except Exception:
                pass

        PaymentService.publish_captured(
            oid,
            payment_ref=payment_ref,
            order_ref=str(order.order_ref),
            amount=amount,
            source_app_id=source_app_id,
        )
        if cash_shift_id is not None:
            try:
                from nodeone.core.commerce.cash import CashRegisterService
                from nodeone.core.commerce.constants import CASH_MOVEMENT_SALE_CASH

                CashRegisterService.record_movement(
                    oid,
                    int(cash_shift_id),
                    CASH_MOVEMENT_SALE_CASH,
                    amount,
                    payment_id=int(row.id),
                    source_app_id=source_app_id,
                )
            except Exception:
                pass
        return payment_to_dto(row, order_ref=str(order.order_ref))

    @staticmethod
    def _next_payment_ref(organization_id: int) -> str:
        import re

        prefix = 'PAY'
        rx = re.compile(rf'^{re.escape(prefix)}-(\d{{1,12}})\Z')
        max_seq = 0
        for (ref,) in (
            CoreCommercialPayment.query.filter_by(organization_id=int(organization_id))
            .with_entities(CoreCommercialPayment.payment_ref)
            .all()
        ):
            m = rx.match(str(ref or '').strip())
            if m:
                max_seq = max(max_seq, int(m.group(1)))
        return f'{prefix}-{max_seq + 1:04d}'

    @staticmethod
    def refund(
        organization_id: int,
        payment_id: int,
        *,
        amount: float | None = None,
        approval: dict | None = None,
        source_app_id: str = 'eposone',
    ) -> PaymentDTO:
        from app import db

        oid = int(organization_id)
        row = CoreCommercialPayment.query.filter_by(organization_id=oid, id=int(payment_id)).first()
        if row is None:
            raise OrderValidationError('payment_not_found')

        from nodeone.core.commerce.authorization import CommerceAuthorizationService

        order = CoreCommercialOrder.query.filter_by(organization_id=oid, id=int(row.order_id)).first()
        CommerceAuthorizationService.assert_supervisor(
            oid,
            dict(approval or {}),
            action='payment.refund',
            order_id=int(row.order_id) if order else None,
            order_ref=str(order.order_ref) if order else None,
            payment_id=int(row.id),
            source_app_id=source_app_id,
        )

        if str(row.status or '') not in _REFUNDABLE_PAYMENT_STATUSES:
            raise OrderValidationError('payment_not_refundable')

        captured_amt = round(float(row.amount or 0), 2)
        already_refunded = round(float(row.refunded_amount or 0), 2)
        remaining = round(captured_amt - already_refunded, 2)
        if remaining <= 0:
            raise OrderValidationError('payment_already_refunded')

        if str(row.payment_type or '') == PAYMENT_TYPE_CASH and row.cash_shift_id:
            from nodeone.core.commerce.cash import CashRegisterService

            CashRegisterService.assert_cash_refund_allowed(oid, int(row.cash_shift_id))

        if order is None:
            raise OrderValidationError('order_not_found')

        refund_amt = round(float(amount if amount is not None else remaining), 2)
        if refund_amt <= 0:
            raise OrderValidationError('amount_required')
        if refund_amt > remaining:
            raise OrderValidationError('refund_exceeds_payment')

        prev_payment_status = str(order.payment_status or 'unpaid')
        prev_operational = str(order.status or '')
        prev_fiscal_status = str(order.fiscal_status or '')

        row.refunded_amount = round(already_refunded + refund_amt, 2)
        row.status = (
            PAYMENT_STATUS_REFUNDED
            if row.refunded_amount >= captured_amt
            else PAYMENT_STATUS_PARTIAL_REFUND
        )
        order.amount_paid = round(max(0.0, float(order.amount_paid or 0) - refund_amt), 2)
        order.version = int(order.version or 1) + 1
        new_payment_status = order.sync_payment_status()

        fiscal_reverted = PaymentService._maybe_revert_fiscal_on_full_refund(order)
        operational_changed = PaymentService._maybe_transition_refunded(order, prev_operational)

        db.session.commit()

        if new_payment_status != prev_payment_status:
            OrderService.publish_payment_status_changed(
                oid,
                order_ref=str(order.order_ref),
                from_status=prev_payment_status,
                to_status=new_payment_status,
                source_app_id=source_app_id,
            )
        if fiscal_reverted is not None:
            OrderService.publish_fiscal_status_changed(
                oid,
                order_ref=str(order.order_ref),
                from_status=prev_fiscal_status,
                to_status=str(order.fiscal_status),
                source_app_id=source_app_id,
            )
        if operational_changed:
            OrderService.publish_status_changed(
                oid,
                order_ref=str(order.order_ref),
                from_status=prev_operational,
                to_status=ORDER_STATUS_REFUNDED,
                source_app_id=source_app_id,
            )

        PaymentService.publish_refunded(
            oid,
            payment_ref=str(row.payment_ref),
            order_ref=str(order.order_ref),
            amount=refund_amt,
            source_app_id=source_app_id,
        )
        if str(row.payment_type or '') == PAYMENT_TYPE_CASH and row.cash_shift_id:
            try:
                from nodeone.core.commerce.cash import CashRegisterService
                from nodeone.core.commerce.constants import CASH_MOVEMENT_REFUND_CASH

                CashRegisterService.record_movement(
                    oid,
                    int(row.cash_shift_id),
                    CASH_MOVEMENT_REFUND_CASH,
                    refund_amt,
                    payment_id=int(row.id),
                    source_app_id=source_app_id,
                )
            except Exception:
                pass
        return payment_to_dto(row, order_ref=str(order.order_ref))

    @staticmethod
    def _maybe_revert_fiscal_on_full_refund(order: CoreCommercialOrder) -> str | None:
        paid = round(float(order.amount_paid or 0), 2)
        if paid > 0:
            return None
        fs = str(order.fiscal_status or '')
        if fs == ORDER_FISCAL_STATUS_PENDING:
            order.fiscal_status = ORDER_FISCAL_STATUS_NOT_REQUIRED
            return fs
        if fs == ORDER_FISCAL_STATUS_INVOICED:
            return None
        return None

    @staticmethod
    def _maybe_transition_refunded(order: CoreCommercialOrder, prev_operational: str) -> bool:
        paid = round(float(order.amount_paid or 0), 2)
        if paid > 0:
            return False
        cur = str(order.status or '')
        if cur == ORDER_STATUS_REFUNDED:
            return False
        if not can_transition_order_status(cur, ORDER_STATUS_REFUNDED):
            return False
        order.status = ORDER_STATUS_REFUNDED
        return True

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
