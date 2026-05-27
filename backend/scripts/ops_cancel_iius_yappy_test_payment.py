#!/usr/bin/env python3
"""Cancela pagos Yappy manual de prueba/smoke (monto bajo, sin comprobante).

Uso:
  python scripts/ops_cancel_iius_yappy_test_payment.py           # dry-run
  python scripts/ops_cancel_iius_yappy_test_payment.py --apply
  python scripts/ops_cancel_iius_yappy_test_payment.py --apply --payment-id 9
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MAX_TEST_AMOUNT_CENTS = 100  # <= $1.00 USD


def main() -> int:
    parser = argparse.ArgumentParser(description='Cancelar Yappy manual de prueba en cola abierta.')
    parser.add_argument('--apply', action='store_true', help='Persistir en BD')
    parser.add_argument('--payment-id', type=int, default=None, help='Solo este id')
    parser.add_argument('--org-id', type=int, default=1)
    args = parser.parse_args()

    from app import app, db
    from models.payments import Payment
    from nodeone.services.payment_pending_status import ADMIN_YAPPY_OPEN_STATUSES
    from nodeone.services.yappy_manual import append_yappy_manual_audit
    from nodeone.services.yappy_manual_status import is_pending_receipt

    with app.app_context():
        q = Payment.query.filter(
            Payment.payment_method == 'yappy_manual',
            Payment.status.in_(tuple(ADMIN_YAPPY_OPEN_STATUSES)),
        )
        if hasattr(Payment, 'organization_id'):
            q = q.filter_by(organization_id=int(args.org_id))
        if args.payment_id:
            q = q.filter_by(id=int(args.payment_id))

        candidates = []
        for p in q.all():
            amt = int(p.amount or 0)
            if args.payment_id or amt <= MAX_TEST_AMOUNT_CENTS:
                if is_pending_receipt(p.status) and not (getattr(p, 'receipt_disk_path', None) or '').strip():
                    candidates.append(p)

        if not candidates:
            print('Nada que cancelar (criterio: yappy_manual abierto, <=$1, sin comprobante).')
            return 0

        for p in candidates:
            print(
                f'{"APPLY" if args.apply else "DRY"} cancel id={p.id} '
                f'status={p.status} amount_cents={p.amount} user={p.user_id}'
            )
            if not args.apply:
                continue
            p.status = 'cancelled'
            p.validation_observations = (p.validation_observations or '') or 'Cancelado: pago de prueba/smoke.'
            append_yappy_manual_audit(
                p,
                {
                    'event': 'ops_cancel_test_payment',
                    'reason': 'stale_smoke_or_test_amount',
                    'max_test_amount_cents': MAX_TEST_AMOUNT_CENTS,
                },
            )
        if args.apply:
            db.session.commit()
            print(f'Cancelados: {len(candidates)}')
        else:
            print(f'Dry-run: {len(candidates)} pago(s). Re-ejecuta con --apply.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
