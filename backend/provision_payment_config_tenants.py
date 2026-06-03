#!/usr/bin/env python3
"""CLI: matriz + PaymentConfig por tenant + resumen."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app import app
from models.saas import SaasOrganization
from nodeone.services import organization_payment_methods as opm
from nodeone.services.payment_config_provision import (
    bootstrap_tenant_payment_setup,
    dedicated_active_config,
    provision_missing_payment_configs,
)


def main() -> int:
    with app.app_context():
        bootstrap_tenant_payment_setup()
        created = provision_missing_payment_configs()
        for org in SaasOrganization.query.order_by(SaasOrganization.id).all():
            cfg = dedicated_active_config(org.id)
            ctx = opm.build_checkout_payment_context(org.id)
            methods = list((ctx.get('payment_methods') or {}).keys())
            if cfg:
                print(
                    f'org {org.id} ({org.name}): cfg#{cfg.id} | checkout={methods} | '
                    f'yappy_en={cfg.yappy_manual_enabled} wire_en={cfg.intl_wire_enabled}'
                )
            else:
                print(f'org {org.id} ({org.name}): sin cfg dedicado | checkout={methods}')
        print(f'Configs nuevos en esta pasada: {created or "ninguno"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
