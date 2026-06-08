#!/usr/bin/env python3
"""Rechaza pendientes cuando el usuario ya tiene inscripción pagada activa (event_registration)."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

EVENT_ID = 2
PENDING_STATUSES = ('pending_admin_review', 'pending_validation', 'manual_review')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--event-id', type=int, default=EVENT_ID)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--payment-ids', nargs='*', type=int)
    args = parser.parse_args()

    from app import Payment, User, app, db, get_or_create_cart
    from nodeone.services.event_registration_guard import (
        REJECTED_DUPLICATE_REASON,
        REJECTED_DUPLICATE_STATUS,
        blocked_by_existing_registration,
        event_ids_in_cart,
        is_user_already_registered,
        mark_payment_rejected_duplicate,
    )

    stats = {
        'reviewed': 0,
        'rejected': 0,
        'skipped_legit': 0,
        'skipped_no_event': 0,
        'skipped_already': 0,
        'errors': 0,
    }

    with app.app_context():
        q = Payment.query.filter(Payment.status.in_(PENDING_STATUSES))
        if args.payment_ids:
            q = q.filter(Payment.id.in_(args.payment_ids))
        pending = q.order_by(Payment.id.asc()).all()

        for payment in pending:
            stats['reviewed'] += 1
            cart = get_or_create_cart(int(payment.user_id))
            user = User.query.get(int(payment.user_id))
            email = (getattr(user, 'email', None) or '').strip().lower()

            cart_events = event_ids_in_cart(cart)
            if args.event_id not in cart_events and not is_user_already_registered(
                args.event_id, int(payment.user_id), email
            ):
                stats['skipped_no_event'] += 1
                print(f'SKIP #{payment.id} {email or "?"}: sin evento {args.event_id}')
                continue

            if (payment.status or '').strip() == REJECTED_DUPLICATE_STATUS:
                stats['skipped_already'] += 1
                print(f'SKIP #{payment.id} {email or "?"}: ya {REJECTED_DUPLICATE_STATUS}')
                continue

            blocked, eid, msg = blocked_by_existing_registration(
                payment, cart, payer_email=email
            )
            if not blocked:
                stats['skipped_legit'] += 1
                print(f'SKIP #{payment.id} {email or "?"}: pendiente legítimo')
                continue

            print(f'REJECT #{payment.id} {email or "?"} event={eid}: {msg}')
            if args.dry_run:
                stats['rejected'] += 1
                continue

            try:
                mark_payment_rejected_duplicate(payment, reason=msg)
                db.session.commit()
                stats['rejected'] += 1
            except Exception as exc:
                db.session.rollback()
                stats['errors'] += 1
                print(f'ERROR #{payment.id}: {exc}')

    print('\n=== RESUMEN ===')
    for key, val in stats.items():
        print(f'  {key}: {val}')
    return 0 if stats['errors'] == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
