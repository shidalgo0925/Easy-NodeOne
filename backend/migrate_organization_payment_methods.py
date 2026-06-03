#!/usr/bin/env python3
"""Crea organization_payment_methods y siembra filas por tenant desde PaymentConfig."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app import app, db
from nodeone.services import organization_payment_methods as opm
from models.saas import SaasOrganization


def main() -> int:
    with app.app_context():
        opm.ensure_organization_payment_methods_schema()
        total = 0
        for org in SaasOrganization.query.order_by(SaasOrganization.id).all():
            n = opm.seed_organization_payment_methods(
                org.id, inherit_enabled_from_config=True
            )
            total += n
            print(f'org {org.id} ({org.name}): +{n} métodos')
        db.session.commit()
        print(f'Listo. Filas nuevas: {total}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
