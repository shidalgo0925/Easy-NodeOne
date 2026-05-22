#!/usr/bin/env python3
"""Marca matrículas paid/confirmed si el pago del carrito académico ya está completado."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    from app import app, db
    from models.academic_program import AcademicProgramEnrollment
    from models.payments import Payment

    _PAID_STATUSES = frozenset({'completed', 'paid', 'success', 'succeeded'})

    updated = 0
    with app.app_context():
        for en in AcademicProgramEnrollment.query.filter_by(status='pending_payment').all():
            if en.payment_id:
                pay = Payment.query.get(int(en.payment_id))
                if pay and (pay.status or '').lower() in _PAID_STATUSES:
                    en.status = 'confirmed'
                    en.payment_status = 'paid'
                    if not en.confirmed_at:
                        from datetime import datetime
                        en.confirmed_at = pay.paid_at or datetime.utcnow()
                    updated += 1
                    continue
            pay = (
                Payment.query.filter_by(user_id=en.user_id)
                .filter(Payment.status.in_(tuple(_PAID_STATUSES)))
                .order_by(Payment.id.desc())
                .first()
            )
            if pay:
                en.status = 'confirmed'
                en.payment_status = 'paid'
                en.payment_id = pay.id
                if not en.confirmed_at:
                    from datetime import datetime
                    en.confirmed_at = pay.paid_at or datetime.utcnow()
                updated += 1

        from app import CartItem

        for item in CartItem.query.filter_by(product_type='academic_program').all():
            if not item.item_metadata:
                continue
            try:
                meta = json.loads(item.item_metadata) if isinstance(item.item_metadata, str) else item.item_metadata
            except Exception:
                continue
            eid = meta.get('enrollment_id')
            if not eid:
                continue
            en = AcademicProgramEnrollment.query.get(int(eid))
            if not en or en.status != 'pending_payment':
                continue
            cart = item.cart
            if not cart:
                continue
            for pay in Payment.query.filter_by(user_id=cart.user_id).order_by(Payment.id.desc()).limit(20):
                if (pay.status or '').lower() in _PAID_STATUSES:
                    en.status = 'confirmed'
                    en.payment_status = 'paid'
                    en.payment_id = pay.id
                    if not en.confirmed_at:
                        from datetime import datetime
                        en.confirmed_at = pay.paid_at or datetime.utcnow()
                    updated += 1
                    break
        if updated:
            db.session.commit()
        print(f'OK: {updated} matrícula(s) actualizada(s)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
