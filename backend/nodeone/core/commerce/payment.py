"""PaymentService — pagos comerciales (Etapa 14)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from models.commercial_core import CoreCommercialOrder, CoreCommercialPayment
from nodeone.core.commerce.constants import (
    ORDER_FISCAL_STATUS_PENDING,
    ORDER_PAYMENT_STATUS_PAID,
    PAYMENT_STATUS_CAPTURED,
    PAYMENT_TYPE_CASH,
)
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
    def refund(organization_id: int, payment_id: int, *, amount: float | None = None) -> PaymentDTO:
        raise NotImplementedError('PaymentService.refund pendiente post-MVP')

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
