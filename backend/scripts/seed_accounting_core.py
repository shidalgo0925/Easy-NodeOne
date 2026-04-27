"""
Seed base para motor contable Fase 1.

Uso:
  python3 scripts/seed_accounting_core.py <organization_id>
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    if len(sys.argv) < 2:
        print('Uso: python3 scripts/seed_accounting_core.py <organization_id>', file=sys.stderr)
        return 2
    org_id = int(sys.argv[1])

    from app import app, db
    from models.accounting_core import Account, Journal
    from models.saas import SaasOrganization
    from nodeone.modules.accounting_core.service import ensure_accounting_core_schema

    accounts_seed = [
        ('1100', 'Caja', 'asset'),
        ('1110', 'Banco', 'asset'),
        ('1200', 'Cuentas por cobrar', 'asset'),
        ('2100', 'Cuentas por pagar', 'liability'),
        ('3100', 'Patrimonio', 'equity'),
        ('4100', 'Ingresos por servicios', 'income'),
        ('5100', 'Gastos administrativos', 'expense'),
    ]
    journals_seed = [
        ('GEN', 'General', 'general'),
        ('SAL', 'Ventas', 'sale'),
        ('PUR', 'Compras', 'purchase'),
        ('BNK', 'Banco', 'bank'),
        ('CSH', 'Caja', 'cash'),
    ]

    with app.app_context():
        ensure_accounting_core_schema()
        org = SaasOrganization.query.get(org_id)
        if org is None:
            raise SystemExit(f'organization_id={org_id} no existe.')
        for code, name, acc_type in accounts_seed:
            row = Account.query.filter_by(organization_id=org_id, code=code).first()
            if row is None:
                row = Account(organization_id=org_id, code=code, name=name, type=acc_type, is_active=True)
                db.session.add(row)
            else:
                row.name = name
                row.type = acc_type
                row.is_active = True
        db.session.flush()
        default_by_type = {
            'general': Account.query.filter_by(organization_id=org_id, code='1100').first(),
            'sale': Account.query.filter_by(organization_id=org_id, code='1200').first(),
            'purchase': Account.query.filter_by(organization_id=org_id, code='2100').first(),
            'bank': Account.query.filter_by(organization_id=org_id, code='1110').first(),
            'cash': Account.query.filter_by(organization_id=org_id, code='1100').first(),
        }
        for code, name, j_type in journals_seed:
            row = Journal.query.filter_by(organization_id=org_id, code=code).first()
            default_acc = default_by_type.get(j_type)
            if row is None:
                row = Journal(
                    organization_id=org_id,
                    code=code,
                    name=name,
                    type=j_type,
                    default_account_id=(default_acc.id if default_acc else None),
                    is_active=True,
                )
                db.session.add(row)
            else:
                row.name = name
                row.type = j_type
                row.default_account_id = default_acc.id if default_acc else row.default_account_id
                row.is_active = True
        db.session.commit()
        print(f'OK: seed accounting_core para org={org_id} ({org.name})')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
