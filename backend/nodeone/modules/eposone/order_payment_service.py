"""Order Domain — pagos 1:N (mismo servicio para POS y BackOffice)."""

from __future__ import annotations

import secrets
import unicodedata
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
    apply_financial_state,
)


def _recalc_payment_status(order: EposoneOrder) -> None:
    """Actualiza flags de pago/cierre sin tocar totales de líneas."""
    apply_financial_state(order)


def _fold(value: str) -> str:
    """Normaliza texto de método (minúsculas, sin acentos, espacios → _)."""
    raw = unicodedata.normalize('NFKD', str(value or ''))
    ascii_only = ''.join(ch for ch in raw if not unicodedata.combining(ch))
    return '_'.join(ascii_only.strip().lower().replace('-', ' ').split())


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
    ('card', 'Tarjeta', 95, True, False),  # legado APK genérico
    ('other', 'Otros', 100, False, False),
)

# Alias que envía la APK / BO hacia method_key canónico.
METHOD_ALIASES: dict[str, str] = {
    'cash': 'cash',
    'efectivo': 'cash',
    'visa': 'visa',
    'mastercard': 'mastercard',
    'master': 'mastercard',
    'master_card': 'mastercard',
    'clave': 'clave',
    'yappy': 'yappy',
    'ach': 'ach',
    'transferencia': 'ach',
    'transfer': 'ach',
    'vale': 'voucher',
    'voucher': 'voucher',
    'credito': 'customer_credit',
    'credito_cliente': 'customer_credit',
    'customer_credit': 'customer_credit',
    'cxc': 'customer_credit',
    'gift': 'gift_card',
    'giftcard': 'gift_card',
    'gift_card': 'gift_card',
    'tarjeta_regalo': 'gift_card',
    'card': 'card',
    'tarjeta': 'card',
    'credit_card': 'card',
    'debit_card': 'card',
    'otros': 'other',
    'other': 'other',
}


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
    def _raw_method_from_body(body: dict[str, Any]) -> str:
        for key in (
            'method',
            'method_key',
            'payment_method',
            'payment_type',
            'forma_pago',
            'tipo_pago',
        ):
            val = body.get(key)
            if val is not None and str(val).strip():
                return str(val).strip()
        return ''

    @staticmethod
    def _resolve_method(
        organization_id: int, body: dict[str, Any]
    ) -> tuple[EposonePaymentMethod | None, str]:
        """Devuelve (row|None, method_key). Acepta key, alias o etiqueta del catálogo."""
        rows = OrderPaymentService.ensure_methods_for_org(int(organization_id))
        method_id = body.get('payment_method_id')

        if method_id is not None and str(method_id).strip() != '':
            row = EposonePaymentMethod.query.filter_by(
                id=int(method_id), organization_id=int(organization_id)
            ).first()
            if row is None or not bool(row.enabled):
                raise OrderDomainError('payment_method_invalid', http_status=400)
            return row, str(row.method_key)

        raw = OrderPaymentService._raw_method_from_body(body)
        folded = _fold(raw) if raw else 'cash'
        if not folded:
            folded = 'cash'

        canonical = METHOD_ALIASES.get(folded, folded)
        by_key = {str(r.method_key): r for r in rows if bool(r.enabled)}
        if canonical in by_key:
            row = by_key[canonical]
            return row, str(row.method_key)

        # Match por etiqueta ("Yappy", "Crédito Cliente", …)
        for row in rows:
            if not bool(row.enabled):
                continue
            if _fold(row.label) == folded or _fold(row.method_key) == folded:
                return row, str(row.method_key)

        raise OrderDomainError('payment_method_invalid', http_status=400)

    @staticmethod
    def _ensure_reference(
        method_row: EposonePaymentMethod | None,
        *,
        reference: str | None,
        authorization_code: str | None,
        payment_ref: str,
    ) -> str | None:
        """Si el método exige referencia y no viene, genera una para no perder el cobro."""
        ref = (reference or '').strip() or None
        if ref:
            return ref
        if method_row is None or not bool(method_row.requires_reference):
            return None
        auth = (authorization_code or '').strip()
        if auth:
            return auth
        # Continuidad operativa: registrar el pago aunque la APK omita la referencia.
        return f'NR-{payment_ref}'[:128]

    @staticmethod
    def _base_total(order: EposoneOrder) -> float:
        return round(
            float(order.subtotal or 0) + float(order.tax or 0) - float(order.discount or 0),
            4,
        )

    @staticmethod
    def _apply_tip(order: EposoneOrder, tip: float) -> None:
        order.tip = round(max(0.0, float(tip or 0)), 4)
        order.total = round(OrderPaymentService._base_total(order) + float(order.tip), 4)

    @staticmethod
    def _sync_tip_before_payment(order: EposoneOrder, body: dict[str, Any], amount: float) -> None:
        """Aplica propina explícita o inferida del monto (APK suele cobrar subtotal+tip).

        No acumula tip inferido sobre un tip ya presente (evita partial artificial).
        """
        tip_raw = body.get('tip')
        if tip_raw is None:
            tip_raw = body.get('propina')
        if tip_raw is not None:
            OrderPaymentService._apply_tip(order, float(tip_raw or 0))
            return

        # Ya hay tip en el pedido: no inventar overflow adicional.
        if float(order.tip or 0) > 1e-6:
            return

        paid = float(order.amount_paid or 0)
        base = OrderPaymentService._base_total(order)
        remaining_base = round(base - paid, 4)
        if remaining_base < -1e-6:
            return
        # Si el cobro supera el saldo sin tip, asumir que la diferencia es propina.
        overflow = round(amount - remaining_base, 4)
        if overflow <= 1e-6:
            return
        # Tope razonable: propina ≤ 50% del subtotal (evita overpay accidental).
        max_tip = round(max(base, 0.0) * 0.5, 4)
        if overflow > max_tip + 1e-6:
            return
        OrderPaymentService._apply_tip(order, overflow)

    @staticmethod
    def add_payment(device: CorePosTerminal, order_id: int, body: dict[str, Any]) -> EposoneOrder:
        """Registra uno o varios pagos (lista `payments` = cobro mixto en un request)."""
        payments_in = body.get('payments')
        if isinstance(payments_in, list) and payments_in:
            order: EposoneOrder | None = None
            for idx, raw in enumerate(payments_in):
                if not isinstance(raw, dict):
                    continue
                part = dict(body)
                part.pop('payments', None)
                part.update(raw)
                if not part.get('payment_ref'):
                    part['payment_ref'] = (
                        str(body.get('payment_ref') or f'pay-{secrets.token_hex(3)}')
                        + f'-{idx}'
                    )
                if not part.get('event_id'):
                    part['event_id'] = str(uuid.uuid4())
                order = OrderPaymentService._add_single_payment(device, order_id, part)
            if order is None:
                raise OrderDomainError('payments_required', http_status=400)
            return order
        return OrderPaymentService._add_single_payment(device, order_id, body)

    @staticmethod
    def _add_single_payment(
        device: CorePosTerminal, order_id: int, body: dict[str, Any]
    ) -> EposoneOrder:
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
        if kind in ('deposit', 'partial', 'abono') and not (
            order.customer_ref or body.get('customer_ref')
        ):
            raise OrderDomainError('customer_required_for_partial', http_status=400)
        if body.get('customer_ref'):
            order.customer_ref = str(body.get('customer_ref')).strip()

        method_row, method_key = OrderPaymentService._resolve_method(
            int(order.organization_id), body
        )
        payment_ref = str(body.get('payment_ref') or f'pay-{secrets.token_hex(4)}').strip()
        event_id = str(body.get('event_id') or uuid.uuid4()).strip()
        authorization_code = (body.get('authorization_code') or '').strip() or None
        reference = OrderPaymentService._ensure_reference(
            method_row,
            reference=(body.get('reference') or body.get('ref') or None),
            authorization_code=authorization_code,
            payment_ref=payment_ref,
        )
        if method_row and bool(method_row.requires_authorization) and not authorization_code:
            raise OrderDomainError('authorization_required', http_status=400)

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

        # Propina: explícita en payload o inferida si el monto incluye tip no sincronizado.
        OrderPaymentService._sync_tip_before_payment(order, body, amount)

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
