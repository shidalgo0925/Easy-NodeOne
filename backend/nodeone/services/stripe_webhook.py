"""Webhook Stripe: verificación de firma, eventos y fulfillment EN1."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger('nodeone.stripe')


def _stripe_pi_id_from_event(parsed: dict[str, Any]) -> str | None:
    obj = (parsed.get('data') or {}).get('object') or {}
    etype = (parsed.get('type') or '').strip()
    if etype.startswith('payment_intent.'):
        return (obj.get('id') or '').strip() or None
    if etype == 'charge.refunded':
        return (obj.get('payment_intent') or '').strip() or None
    return None


def collect_webhook_secrets(payment_intent_id: str | None = None) -> list[str]:
    """Secrets a probar: tenant del pago (si existe) y resto de tenants con secret configurado."""
    import app as M

    seen: set[str] = set()
    ordered: list[str] = []

    def _add(raw: str | None) -> None:
        wh = (raw or '').strip()
        if wh and wh not in seen:
            seen.add(wh)
            ordered.append(wh)

    if payment_intent_id:
        payment = M.Payment.query.filter_by(payment_reference=payment_intent_id).first()
        if payment:
            oid = getattr(payment, 'organization_id', None)
            if oid:
                cfg = M.PaymentConfig.get_active_config(organization_id=int(oid))
                if cfg:
                    _add(cfg.get_stripe_webhook_secret())

    for cfg in M.PaymentConfig.query.filter_by(is_active=True).order_by(M.PaymentConfig.id.asc()).all():
        _add(cfg.get_stripe_webhook_secret())

    env_wh = (__import__('os').environ.get('STRIPE_WEBHOOK_SECRET') or '').strip()
    _add(env_wh)
    return ordered


def construct_stripe_event(raw_payload: bytes, sig_header: str | None):
    """Valida firma Stripe; devuelve (event, error_code)."""
    import app as M

    if not M.STRIPE_AVAILABLE or not M.stripe:
        logger.error('stripe_webhook: librería Stripe no disponible')
        return None, 'stripe_unavailable'

    if not sig_header:
        logger.warning('stripe_webhook: falta cabecera Stripe-Signature')
        return None, 'missing_signature'

    try:
        parsed = json.loads(raw_payload.decode('utf-8'))
    except Exception:
        logger.warning('stripe_webhook: payload JSON inválido')
        return None, 'invalid_json'

    pi_id = _stripe_pi_id_from_event(parsed)
    secrets = collect_webhook_secrets(pi_id)
    if not secrets:
        logger.error('stripe_webhook: ningún webhook secret configurado en tenants')
        return None, 'no_webhook_secret'

    last_err = None
    for wh in secrets:
        try:
            event = M.stripe.Webhook.construct_event(raw_payload, sig_header, wh)
            logger.info(
                'stripe_webhook: firma válida event_id=%s type=%s pi=%s',
                event.get('id'),
                event.get('type'),
                pi_id,
            )
            return event, None
        except ValueError as exc:
            logger.warning('stripe_webhook: payload inválido: %s', exc)
            return None, 'invalid_payload'
        except M.stripe.error.SignatureVerificationError as exc:
            last_err = exc
            continue

    logger.warning('stripe_webhook: firma inválida pi=%s err=%s', pi_id, last_err)
    return None, 'invalid_signature'


def dispatch_stripe_webhook_event(event: dict[str, Any]) -> None:
    etype = (event.get('type') or '').strip()
    logger.info('stripe_webhook: procesando type=%s id=%s', etype, event.get('id'))

    if etype == 'payment_intent.succeeded':
        handle_payment_intent_succeeded((event.get('data') or {}).get('object') or {}, etype)
    elif etype == 'payment_intent.payment_failed':
        handle_payment_intent_failed((event.get('data') or {}).get('object') or {}, etype)
    elif etype == 'charge.refunded':
        handle_charge_refunded((event.get('data') or {}).get('object') or {}, etype)
    else:
        logger.info('stripe_webhook: evento ignorado type=%s', etype)


def _find_payment_by_intent(payment_intent: dict[str, Any]):
    import app as M

    pi_id = (payment_intent.get('id') or '').strip()
    if not pi_id:
        return None
    return M.Payment.query.filter_by(payment_reference=pi_id).first()


def _append_stripe_audit(payment, *, event_type: str, status: str, extra: dict | None = None) -> None:
    try:
        from history_module import HistoryLogger

        payload = {
            'payment_id': payment.id,
            'payment_method': 'stripe',
            'amount': payment.amount,
            'event_type': event_type,
        }
        if extra:
            payload.update(extra)
        HistoryLogger.log_user_action(
            user_id=payment.user_id,
            action=f'Stripe webhook — {event_type} — ${payment.amount / 100:.2f}',
            status=status,
            context={'app': 'webhook', 'screen': 'payment', 'module': 'stripe'},
            payload=payload,
            result={'payment_id': payment.id, 'status': payment.status},
            visibility='both',
        )
    except Exception as exc:
        logger.warning('stripe_webhook: error auditoría payment_id=%s: %s', payment.id, exc)


def _fulfill_stripe_payment(payment) -> None:
    """Carrito, acceso y notificaciones tras pago confirmado."""
    import app as M

    from nodeone.services.payment_post_process import process_cart_after_payment, send_payment_to_odoo

    if (payment.status or '').strip() == 'succeeded':
        logger.info('stripe_webhook: pago %s ya succeeded, omitiendo fulfillment', payment.id)
        return

    payment.status = 'succeeded'
    payment.paid_at = datetime.utcnow()
    M.db.session.commit()
    logger.info('stripe_webhook: payment_id=%s marcado succeeded', payment.id)

    user = M.User.query.get(payment.user_id)
    cart = M.get_or_create_cart(payment.user_id)
    try:
        process_cart_after_payment(cart, payment)
        cart.clear()
        M.db.session.commit()
        logger.info('stripe_webhook: carrito procesado payment_id=%s', payment.id)
    except Exception as exc:
        logger.exception('stripe_webhook: error fulfillment payment_id=%s: %s', payment.id, exc)
        M.db.session.rollback()
        raise

    try:
        send_payment_to_odoo(payment, user, cart)
    except Exception as exc:
        logger.warning('stripe_webhook: Odoo sync payment_id=%s: %s', payment.id, exc)


def handle_payment_intent_succeeded(payment_intent: dict[str, Any], event_type: str | None = None) -> None:
    import app as M

    payment = _find_payment_by_intent(payment_intent)
    if not payment:
        logger.warning(
            'stripe_webhook: payment_intent.succeeded sin pago EN1 pi=%s',
            payment_intent.get('id'),
        )
        return

    try:
        _fulfill_stripe_payment(payment)
        _append_stripe_audit(payment, event_type=event_type or 'payment_intent.succeeded', status='success')
    except Exception:
        M.db.session.rollback()
        raise


def handle_payment_intent_failed(payment_intent: dict[str, Any], event_type: str | None = None) -> None:
    import app as M

    payment = _find_payment_by_intent(payment_intent)
    if not payment:
        logger.warning(
            'stripe_webhook: payment_intent.payment_failed sin pago EN1 pi=%s',
            payment_intent.get('id'),
        )
        return

    payment.status = 'failed'
    M.db.session.commit()
    logger.info('stripe_webhook: payment_id=%s marcado failed', payment.id)
    _append_stripe_audit(
        payment,
        event_type=event_type or 'payment_intent.payment_failed',
        status='failed',
        extra={'failure_message': (payment_intent.get('last_payment_error') or {}).get('message')},
    )


def handle_charge_refunded(charge: dict[str, Any], event_type: str | None = None) -> None:
    import app as M

    pi_id = (charge.get('payment_intent') or '').strip()
    if not pi_id:
        logger.warning('stripe_webhook: charge.refunded sin payment_intent')
        return

    payment = M.Payment.query.filter_by(payment_reference=pi_id).first()
    if not payment:
        logger.warning('stripe_webhook: charge.refunded sin pago EN1 pi=%s', pi_id)
        return

    payment.status = 'refunded'
    M.db.session.commit()
    logger.info('stripe_webhook: payment_id=%s marcado refunded', payment.id)
    _append_stripe_audit(
        payment,
        event_type=event_type or 'charge.refunded',
        status='refunded',
        extra={'charge_id': charge.get('id')},
    )


def stripe_credentials_configured(payment_config) -> bool:
    if not payment_config:
        return False
    pk = (payment_config.get_stripe_publishable_key() or '').strip()
    sk = (payment_config.get_stripe_secret_key() or '').strip()
    return bool(
        pk
        and sk
        and not sk.startswith('sk_test_your_')
        and not pk.startswith('pk_test_your_')
    )
