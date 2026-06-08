"""Tras pago aprobado: inscripción al evento + participante (idempotente)."""

from __future__ import annotations

import json
from typing import Any


def build_cart_items_snapshot(cart) -> list[dict]:
    rows: list[dict] = []
    for item in getattr(cart, 'items', []) or []:
        rows.append(
            {
                'product_type': item.product_type,
                'product_id': int(item.product_id),
                'product_name': item.product_name,
                'product_description': getattr(item, 'product_description', None),
                'unit_price': int(item.unit_price),
                'quantity': int(item.quantity or 1),
                'item_metadata': getattr(item, 'item_metadata', None),
            }
        )
    return rows


def cart_event_ids(cart) -> list[int]:
    ids: list[int] = []
    for item in getattr(cart, 'items', []) or []:
        if getattr(item, 'product_type', None) != 'event':
            continue
        eid = getattr(item, 'product_id', None)
        if eid is None and getattr(item, 'item_metadata', None):
            try:
                meta = json.loads(item.item_metadata)
                eid = meta.get('event_id')
            except (TypeError, ValueError, json.JSONDecodeError):
                eid = None
        if eid is not None:
            try:
                ids.append(int(eid))
            except (TypeError, ValueError):
                pass
    return list(dict.fromkeys(ids))


def ensure_participants_for_event_ids(event_ids: list[int]) -> dict[str, Any]:
    from nodeone.modules.events.services.participants_from_registrations import (
        import_participants_from_registrations,
    )

    totals = {'created': 0, 'skipped': 0, 'cancelled_skipped': 0, 'events': []}
    for eid in event_ids:
        stats = import_participants_from_registrations(int(eid), only_confirmed=True)
        totals['created'] += stats.get('created', 0)
        totals['skipped'] += stats.get('skipped', 0)
        totals['cancelled_skipped'] += stats.get('cancelled_skipped', 0)
        totals['events'].append({'event_id': int(eid), **stats})
    return totals


def fulfill_paid_payment_events(payment, cart=None) -> dict[str, Any]:
    """Procesa carrito tras paid y asegura participantes (sin duplicar)."""
    from app import db, get_or_create_cart
    from nodeone.services.manual_payment_flow import is_manual_validation_method
    from nodeone.services.payment_post_process import process_cart_after_payment

    result: dict[str, Any] = {
        'payment_id': int(payment.id),
        'cart_processed': False,
        'participant_stats': None,
    }
    st = (getattr(payment, 'status', None) or '').strip()
    method = (getattr(payment, 'payment_method', None) or '').strip()
    if is_manual_validation_method(method) and st != 'paid':
        result['error'] = 'Solo pagos manuales en estado paid.'
        return result
    if not is_manual_validation_method(method) and st != 'succeeded':
        result['error'] = 'Solo pagos confirmados (succeeded/paid).'
        return result

    cart = cart or get_or_create_cart(int(payment.user_id))
    event_ids: list[int] = []

    if cart.get_items_count() > 0:
        process_cart_after_payment(cart, payment)
        event_ids = cart_event_ids(cart)
        cart.clear()
        db.session.commit()
        result['cart_processed'] = True
    else:
        db.session.commit()

    if not event_ids:
        from app import EventRegistration

        pref = (getattr(payment, 'payment_reference', None) or '').strip()
        refs = {str(int(payment.id)), pref} if pref else {str(int(payment.id))}
        for reg in EventRegistration.query.filter_by(
            user_id=int(payment.user_id),
            registration_status='confirmed',
            payment_status='paid',
        ).all():
            rpref = (getattr(reg, 'payment_reference', None) or '').strip()
            if rpref in refs:
                event_ids.append(int(reg.event_id))
        event_ids = list(dict.fromkeys(event_ids))

    if event_ids:
        result['participant_stats'] = ensure_participants_for_event_ids(event_ids)
        db.session.commit()
    return result
