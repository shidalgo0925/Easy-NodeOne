#!/usr/bin/env python3
"""Repara pagos paid: asegura participante desde event_registration existente."""

from __future__ import annotations

import argparse
import os
import sys

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--payment-ids', nargs='+', type=int)
    parser.add_argument('--event-id', type=int)
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

    fixed = skipped = 0
    for payment in payments:
        uid = int(payment.user_id)
        if args.event_id:
            reg = EventRegistration.query.filter_by(
                user_id=uid,
                event_id=args.event_id,
                registration_status='confirmed',
                payment_status='paid',
            ).first()
            if not reg:
                skipped += 1
                continue
            part = EventParticipant.query.filter_by(user_id=uid, event_id=args.event_id).first()
            if reg and part:
                skipped += 1
                continue
        else:
            regs = EventRegistration.query.filter_by(
                user_id=uid,
                registration_status='confirmed',
                payment_status='paid',
            ).all()
            if not regs:
                skipped += 1
                continue
            needs = any(
                not EventParticipant.query.filter_by(user_id=uid, event_id=r.event_id).first()
                for r in regs
            )
            if not needs:
                skipped += 1
                continue

        print(f'PROCESS payment {payment.id} user={uid}')
        if args.dry_run:
            fixed += 1
            continue
        cart = get_or_create_cart(uid)
        result = fulfill_paid_payment_events(payment, cart)
        print(f'  -> {result}')
        fixed += 1

    print(f'Done: processed={fixed} skipped={skipped}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
