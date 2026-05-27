#!/usr/bin/env python3
"""Smoke operativo pagos IIUS: métodos checkout, Yappy manual, estados pendientes."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HOST = {'Host': 'apps.internationalinstitute.us', 'User-Agent': 'Mozilla/5.0'}
ORG_ID = 1


def main() -> int:
    from app import app, User
    from flask_login.utils import _create_identifier
    from models.payments import Payment
    from nodeone.services import organization_payment_methods as opm
    from nodeone.services.payment_pending_status import (
        ADMIN_YAPPY_OPEN_STATUSES,
        is_member_pending_payment,
        member_pending_action_url,
    )
    from user_status_checker import UserStatusChecker

    fails: list[str] = []
    oks: list[str] = []

    def ok(m):
        oks.append(m)
        print(f'  OK  {m}')

    def fail(m):
        fails.append(m)
        print(f' FAIL {m}')

    with app.app_context():
        with app.test_request_context('/dashboard', headers=HOST):
            session_ident = _create_identifier()

        enabled = {m.method_key for m in opm.list_methods_for_org(ORG_ID, enabled_only=True)}
        if enabled == {'paypal', 'wire_international'}:
            ok('checkout IIUS: PayPal + SWIFT')
        else:
            fail(f'checkout métodos inesperados: {enabled}')

        if 'yappy_manual' not in enabled:
            ok('yappy_manual no ofrecido en checkout (perfil internacional)')
        else:
            fail('yappy_manual habilitado en checkout IIUS')

        yappy = (
            Payment.query.filter_by(payment_method='yappy_manual')
            .order_by(Payment.id.desc())
            .first()
        )
        if yappy:
            if is_member_pending_payment(yappy.status, yappy.payment_method):
                ok(f'yappy id={yappy.id} status={yappy.status} cuenta como pendiente miembro')
            else:
                fail(f'yappy id={yappy.id} no detectado como pendiente')

            with app.test_request_context('/dashboard', headers=HOST):
                url = member_pending_action_url(yappy.id, yappy.payment_method, yappy.status)
            if 'yappy-manual' in url:
                ok(f'action_url yappy → {url.split("?")[0]}')
            else:
                fail(f'action_url inesperada: {url}')

            owner_client = app.test_client()
            with owner_client.session_transaction() as s:
                s['_user_id'] = str(yappy.user_id)
                s['_fresh'] = True
                s['_id'] = session_ident
                s['organization_id'] = ORG_ID
            r = owner_client.get(
                f'/payment/yappy-manual/{yappy.id}',
                follow_redirects=False,
            )
            if r.status_code == 200:
                ok(f'página Yappy manual usuario → {r.status_code}')
            else:
                fail(f'página Yappy manual status={r.status_code}')

            st = UserStatusChecker.check_user_status(yappy.user_id, None)
            found = any(p.get('id') == yappy.id for p in st.get('pending_payments', []))
            if found:
                ok('UserStatusChecker lista pago yappy pendiente')
            else:
                fail('UserStatusChecker no lista yappy pendiente')
        else:
            ok('sin pagos yappy_manual en BD (skip flujo)')

        admin = User.query.filter_by(is_admin=True, is_active=True).first()
        if admin:
            c = app.test_client()
            with c.session_transaction() as s:
                s['_user_id'] = str(admin.id)
                s['_fresh'] = True
                s['_id'] = session_ident
                s['organization_id'] = ORG_ID
            r = c.get('/admin/payments/yappy-manual', follow_redirects=False)
            if r.status_code == 200:
                ok('admin lista Yappy manual 200')
            else:
                fail(f'admin yappy-manual status={r.status_code}')

            if yappy and yappy.status in ('pending_receipt', 'pending_payment'):
                r2 = c.post(
                    f'/api/admin/payments/{yappy.id}/yappy-manual/validate',
                    json={'decision': 'paid', 'amount_received_cents': int(yappy.amount or 0)},
                )
                body = r2.get_json() if r2.is_json else {}
                if r2.status_code == 400 and 'revisión' in (body.get('error') or '').lower():
                    ok('validate bloquea paid directo en pending_receipt')
                else:
                    fail(f'validate pending_receipt status={r2.status_code} err={body.get("error")}')
        else:
            fail('sin usuario admin para smoke')

        open_n = Payment.query.filter(
            Payment.payment_method == 'yappy_manual',
            Payment.status.in_(tuple(ADMIN_YAPPY_OPEN_STATUSES)),
        ).count()
        ok(f'cola Yappy abierta en BD: {open_n}')

    print(f'\nResumen: {len(oks)} OK, {len(fails)} FAIL')
    for f in fails:
        print(f'  - {f}')
    return 1 if fails else 0


if __name__ == '__main__':
    raise SystemExit(main())
