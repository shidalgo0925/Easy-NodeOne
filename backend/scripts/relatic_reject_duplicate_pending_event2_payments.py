#!/usr/bin/env python3
"""Sacar de Pendientes los pagos duplicados (usuario ya inscrito pagado en evento 2)."""

from __future__ import annotations

import argparse
import os
import sys

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--event-id', type=int, default=2)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    from app import app
    from nodeone.services.event_registration_guard import (
        DEFAULT_RELATIC_EVENT_ID,
        purge_duplicate_pending_registrations,
    )

    with app.app_context():
        if args.dry_run:
            from app import Payment, User
            from nodeone.services.event_registration_guard import (
                PENDING_ADMIN_STATUSES,
                REJECTED_DUPLICATE_REASON,
                is_user_already_registered,
                mark_payment_rejected_duplicate,
            )

            n = 0
            for payment in Payment.query.filter(Payment.status.in_(PENDING_ADMIN_STATUSES)).all():
                user = User.query.get(int(payment.user_id))
                email = (getattr(user, 'email', None) or '').strip().lower() or None
                if is_user_already_registered(args.event_id, int(payment.user_id), email):
                    print(f'WOULD REJECT #{payment.id} {email}')
                    n += 1
            print(f'dry-run: {n} pagos')
            return 0

        stats = purge_duplicate_pending_registrations(
            event_id=args.event_id or DEFAULT_RELATIC_EVENT_ID
        )
        print(stats)
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
