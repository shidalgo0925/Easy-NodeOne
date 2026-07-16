"""Order Domain — pagos 1:N (mismo servicio para POS y BackOffice)."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime
from typing import Any

from models.commercial_core import CorePosTerminal
from models.eposone_order import (
    EposoneOrder,
    EposoneOrderEvent,
    EposoneOrderPayment,
    EposonePaymentMethod,
)
from nodeone.modules.eposone.order_domain import (
    OrderDomainError,
    OrderDomainService,
)


def _recalc_payment_status(order: EposoneOrder) -> None:
    """Actualiza payment_status / financially_closed sin tocar totales de líneas.

    Seguro cuando los items no están cargados (lock FOR UPDATE sin outer join).
    """
    total = float(order.total or 0)
    paid = float(order.amount_paid or 0)
    if paid <= 0:
        order.payment_status = 'unpaid'
        order.financially_closed = False
    elif paid + 1e-9 < total:
        order.payment_status = 'partial'
        order.financially_closed = False
    else:
        order.payment_status = 'paid'
        order.financially_closed = True

DEFAULT_PAYMENT_METHODS: tuple[tuple[str, str, int, bool, bool], ...] = (
    # method_key, label, display_order, requires_reference, requires_authorization
    ('cash', 'Efectivo', 10, False, False),
    ('visa', 'Visa', 20, True, False),
    ('mastercard', 'Mastercard', 30, True, False),
    ('clave', 'Clave', 40, True, False),
    ('yappy', 'Yappy', 50, True, False),
    ('ach', 'ACH', 60, True, False),
    ('voucher', 'Vale', 70, False, False),
    ('customer_credit', 'Crédito Cliente', 80, False, False),
    ('gift_card', 'Gift Card', 90, True, False),
    ('other', 'Otros', 100, False, False),
)


class OrderPaymentService:
    """Liquidación de pedidos Order Domain mediante pagos sucesivos (1:N)."""

    @staticmethod
    def ensure_methods_for_org(organization_id: int) -> list[EposonePaymentMethod]:
        from app import db

        oid = int(organization_id)
        existing = {
            str(r.method_key): r
            for r in EposonePaymentMethod.query.filter_by(organization_id=oid).all()
        }
        created = False
        for key, label, order, req_ref, req_auth in DEFAULT_PAYMENT_METHODS:
            if key in existing:
                continue
            row = EposonePaymentMethod(
                organization_id=oid,
                method_key=key,
                label=label,
                enabled=True,
                display_order=order,
                requires_reference=req_ref,
                requires_authorization=req_auth,
            )
            db.session.add(row)
            created = True
        if created:
            db.session.commit()
        return (
            EposonePaymentMethod.query.filter_by(organization_id=oid)
            .order_by(EposonePaymentMethod.display_order.asc(), EposonePaymentMethod.id.asc())
            .all()
        )

    @staticmethod
    def list_methods(organization_id: int, *, enabled_only: bool = True) -> list[dict[str, Any]]:
        rows = OrderPaymentService.ensure_methods_for_org(int(organization_id))
        out: list[dict[str, Any]] = []
        for r in rows:
            if enabled_only and not bool(r.enabled):
                continue
            out.append(
                {
                    'id': int(r.id),
                    'method_key': r.method_key,
                    'label': r.label,
                    'enabled': bool(r.enabled),
                    'display_order': int(r.display_order or 0),
                    'requires_reference': bool(r.requires_reference),
                    'requires_authorization': bool(r.requires_authorization),
                }
            )
        return out

    @staticmethod
    def _resolve_method(
        organization_id: int, body: dict[str, Any]
    ) -> tuple[EposonePaymentMethod | None, str]:
        """Devuelve (row|None, method_key). Valida contra catálogo org."""
        OrderPaymentService.ensure_methods_for_org(int(organization_id))
        method_id = body.get('payment_method_id')
        method_key = (body.get('method') or body.get('method_key') or '').strip().lower()

        row: EposonePaymentMethod | None = None
        if method_id is not None and str(method_id).strip() != '':
            row = EposonePaymentMethod.query.filter_by(
                id=int(method_id), organization_id=int(organization_id)
            ).first()
            if row is None or not bool(row.enabled):
                raise OrderDomainError('payment_method_invalid', http_status=400)
            return row, str(row.method_key)

        if not method_key:
            method_key = 'cash'
        row = EposonePaymentMethod.query.filter_by(
            organization_id=int(organization_id), method_key=method_key
        ).first()
        if row is None or not bool(row.enabled):
            raise OrderDomainError('payment_method_invalid', http_status=400)
        return row, str(row.method_key)

    @staticmethod
    def add_payment(device: CorePosTerminal, order_id: int, body: dict[str, Any]) -> EposoneOrder:
        from app import db
        from sqlalchemy.orm import noload

        order = (
            EposoneOrder.query.options(
                noload(EposoneOrder.items),
                noload(EposoneOrder.payments),
                noload(EposoneOrder.events),
            )
            .filter_by(id=int(order_id), organization_id=int(device.organization_id))
            .with_for_update()
            .first()
        )
        if order is None:
            raise OrderDomainError('order_not_found', http_status=404)
        OrderDomainService._require_owner(order, device, for_payment=True)

        amount = float(body.get('amount') or 0)
        if amount <= 0:
            raise OrderDomainError('amount_invalid', http_status=400)

        kind = str(body.get('kind') or 'payment').strip().lower()
        if kind not in ('payment', 'deposit', 'partial', 'abono'):
            kind = 'payment'
        # Abonos formales (deposit/partial/abono) requieren cliente
        if kind in ('deposit', 'partial', 'abono') and not (order.customer_ref or body.get('customer_ref')):
            raise OrderDomainError('customer_required_for_partial', http_status=400)
        if body.get('customer_ref'):
            order.customer_ref = str(body.get('customer_ref')).strip()

        method_row, method_key = OrderPaymentService._resolve_method(
            int(order.organization_id), body
        )
        reference = (body.get('reference') or '').strip() or None
        authorization_code = (body.get('authorization_code') or '').strip() or None
        if method_row and bool(method_row.requires_reference) and not reference:
            raise OrderDomainError('reference_required', http_status=400)
        if method_row and bool(method_row.requires_authorization) and not authorization_code:
            raise OrderDomainError('authorization_required', http_status=400)

        payment_ref = str(body.get('payment_ref') or f'pay-{secrets.token_hex(4)}').strip()
        event_id = str(body.get('event_id') or uuid.uuid4()).strip()

        existing_pay = EposoneOrderPayment.query.filter_by(
            order_id=int(order.id), payment_ref=payment_ref
        ).first()
        if existing_pay is not None:
            return order

        existing_ev = EposoneOrderEvent.query.filter_by(
            organization_id=int(order.organization_id), event_id=event_id
        ).first()
        if existing_ev is not None:
            return order

        other_ref = (
            EposoneOrderPayment.query.join(EposoneOrder)
            .filter(
                EposoneOrder.organization_id == int(order.organization_id),
                EposoneOrderPayment.payment_ref == payment_ref,
                EposoneOrderPayment.order_id != int(order.id),
            )
            .first()
        )
        if other_ref is not None:
            raise OrderDomainError('payment_ref_conflict', http_status=409)

        st = str(order.status or '').lower()
        if st in ('cancelled', 'returned'):
            raise OrderDomainError('order_not_payable', http_status=409)

        if bool(order.financially_closed) or str(order.payment_status or '').lower() == 'paid':
            raise OrderDomainError('already_paid', http_status=409)

        total = float(order.total or 0)
        paid = float(order.amount_paid or 0)
        balance = round(total - paid, 4)
        if balance <= 1e-9:
            raise OrderDomainError('already_paid', http_status=409)
        if amount > balance + 1e-6:
            raise OrderDomainError('amount_exceeds_balance', http_status=409)

        actor_user_ref = (body.get('actor_user_ref') or '').strip() or order.user_ref
        currency = str(body.get('currency') or 'USD').strip() or 'USD'
        now = datetime.utcnow()

        pay = EposoneOrderPayment(
            order_id=order.id,
            payment_ref=payment_ref,
            amount=amount,
            method=method_key,
            kind=kind,
            currency=currency,
            payment_method_id=int(method_row.id) if method_row else None,
            reference=reference,
            authorization_code=authorization_code,
            received_by=actor_user_ref,
            paid_at=now,
            status='captured',
            exchange_rate=(
                float(body['exchange_rate']) if body.get('exchange_rate') is not None else None
            ),
        )
        db.session.add(pay)
        order.amount_paid = round(paid + amount, 4)
        _recalc_payment_status(order)

        OrderDomainService._append_event(
            order,
            event_id=event_id,
            event_type='pago.registrado',
            device=device,
            user_ref=actor_user_ref,
            payload={
                'payment_ref': payment_ref,
                'amount': amount,
                'method': method_key,
                'method_label': method_row.label if method_row else method_key,
                'payment_method_id': int(method_row.id) if method_row else None,
                'reference': reference,
                'authorization_code': authorization_code,
                'kind': pay.kind,
                'register_ref': order.register_ref,
                'actor_user_ref': actor_user_ref,
                'balance_after': round(float(order.total or 0) - float(order.amount_paid or 0), 4),
                'payment_status': order.payment_status,
            },
        )
        if order.financially_closed:
            OrderDomainService._append_event(
                order,
                event_id=str(uuid.uuid4()),
                event_type='pedido.cobrado',
                device=device,
                user_ref=actor_user_ref,
                payload={
                    'total': float(order.total),
                    'amount_paid': float(order.amount_paid),
                    'register_ref': order.register_ref,
                    'actor_user_ref': actor_user_ref,
                },
            )
        order.updated_at = now
        db.session.commit()
        return order
