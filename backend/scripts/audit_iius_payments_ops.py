#!/usr/bin/env python3
"""Auditoría operativa pagos IIUS (org 1): métodos, pendientes, Yappy manual."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ORG_ID = 1


def main() -> int:
    from app import app, db
    from models.payments import Payment, PaymentConfig
    from nodeone.services import organization_payment_methods as opm
    from nodeone.services.payment_pending_status import (
        ADMIN_YAPPY_OPEN_STATUSES,
        MEMBER_PENDING_PAYMENT_STATUSES,
    )
    from sqlalchemy import func

    issues: list[str] = []

    with app.app_context():
        print('=== IIUS pagos (org 1) ===\n')

        enabled = [m.method_key for m in opm.list_methods_for_org(ORG_ID, enabled_only=True)]
        print('Métodos habilitados checkout:', ', '.join(enabled) or '(ninguno)')
        if 'yappy_manual' in enabled and 'international' in str(enabled):
            pass
        if 'yappy_manual' not in enabled:
            print('  (Yappy manual deshabilitado en matriz — perfil internacional OK)')

        cfg = PaymentConfig.query.filter_by(organization_id=ORG_ID).first()
        if cfg:
            print(
                f'PaymentConfig: yappy_manual_enabled={getattr(cfg, "yappy_manual_enabled", None)} '
                f'admin_emails={(getattr(cfg, "yappy_manual_admin_emails", None) or "")[:60]}'
            )
            if getattr(cfg, 'yappy_manual_enabled', False) and not (
                getattr(cfg, 'yappy_manual_admin_emails', None) or ''
            ).strip():
                issues.append('yappy_manual_enabled sin correos admin en PaymentConfig')

        print('\nPagos por status:')
        q = Payment.query
        if hasattr(Payment, 'organization_id'):
            q = q.filter_by(organization_id=ORG_ID)
        for st, cnt in q.with_entities(Payment.status, func.count(Payment.id)).group_by(Payment.status).all():
            print(f'  {st}: {cnt}')

        yappy_open = (
            Payment.query.filter(
                Payment.payment_method == 'yappy_manual',
                Payment.status.in_(tuple(ADMIN_YAPPY_OPEN_STATUSES)),
            )
            .order_by(Payment.id.desc())
            .all()
        )
        print(f'\nYappy manual cola abierta: {len(yappy_open)}')
        for p in yappy_open:
            print(f'  id={p.id} status={p.status} amount={p.amount} user={p.user_id}')

        stale_generic = Payment.query.filter(
            Payment.status.in_(('pending', 'awaiting_confirmation')),
        )
        if hasattr(Payment, 'organization_id'):
            stale_generic = stale_generic.filter_by(organization_id=ORG_ID)
        stale_generic = stale_generic.count()
        if stale_generic:
            print(f'\nIntegraciones pending/awaiting: {stale_generic}')

        member_pending = Payment.query.filter(
            Payment.status.in_(tuple(MEMBER_PENDING_PAYMENT_STATUSES)),
        )
        if hasattr(Payment, 'organization_id'):
            member_pending = member_pending.filter_by(organization_id=ORG_ID)
        print(f'Visible al miembro (todos estados pendientes): {member_pending.count()}')

        if issues:
            print('\n=== ISSUES ===')
            for i in issues:
                print(' -', i)
            return 1
        print('\nResumen: sin issues críticos de auditoría')
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
