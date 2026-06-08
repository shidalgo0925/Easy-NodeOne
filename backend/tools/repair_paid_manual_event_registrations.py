#!/usr/bin/env python3
"""Repara pagos manuales paid: inscripción al evento + participante."""

from __future__ import annotations

import argparse
import json
import os
import sys

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)


def _payment_event_ids(payment, cart) -> list[int]:
    from nodeone.services.payment_event_fulfillment import (
        cart_event_ids,
        event_ids_for_paid_payment,
        restore_cart_items_from_payment,
    )

    restore_cart_items_from_payment(payment, cart)
    ids = cart_event_ids(cart)
    if not ids:
        try:
            meta = json.loads(getattr(payment, 'payment_metadata', None) or '{}')
        except (TypeError, ValueError, json.JSONDecodeError):
            meta = {}
        for row in meta.get('cart_items') or []:
            if (row.get('product_type') or '').strip() == 'event' and row.get('product_id'):
                ids.append(int(row['product_id']))
    if not ids:
        ids = event_ids_for_paid_payment(payment)
    return list(dict.fromkeys(ids))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--payment-ids', nargs='+', type=int, help='IDs de payment a reprocesar')
    parser.add_argument('--event-id', type=int, help='Solo pagos vinculados a este evento')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    from app import EventParticipant, EventRegistration, Payment, app, get_or_create_cart
    from nodeone.services.payment_event_fulfillment import fulfill_paid_payment_events

    with app.app_context():
        return _run(args)


def _run(args) -> int:
    from app import EventParticipant, EventRegistration, Payment, get_or_create_cart
    from nodeone.services.payment_event_fulfillment import fulfill_paid_payment_events

    q = Payment.query.filter(Payment.status == 'paid')
    if args.payment_ids:
        q = q.filter(Payment.id.in_(args.payment_ids))
    payments = q.order_by(Payment.id).all()

    fixed = 0
    skipped = 0
    for payment in payments:
        cart = get_or_create_cart(payment.user_id)
        event_ids = _payment_event_ids(payment, cart)
        if args.event_id and args.event_id not in event_ids:
            skipped += 1
            continue
        if not event_ids:
            print(f'SKIP payment {payment.id}: sin eventos en carrito/metadata')
            skipped += 1
            continue

        needs = False
        for eid in event_ids:
            reg = EventRegistration.query.filter_by(
                user_id=payment.user_id, event_id=eid
            ).first()
            part = EventParticipant.query.filter_by(
                user_id=payment.user_id, event_id=eid
            ).first()
            if not reg or not part:
                needs = True
                break
        if not needs:
            print(f'SKIP payment {payment.id}: ya tiene registro y participante')
            skipped += 1
            continue

        print(f'PROCESS payment {payment.id} user={payment.user_id} events={event_ids}')
        if args.dry_run:
            fixed += 1
            continue
        result = fulfill_paid_payment_events(payment, cart)
        print(f'  -> {result}')
        fixed += 1

    print(f'Done: processed={fixed} skipped={skipped}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
