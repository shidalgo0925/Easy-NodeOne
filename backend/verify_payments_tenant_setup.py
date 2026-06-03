#!/usr/bin/env python3
"""Comprueba matriz, configs dedicados y coherencia checkout (DEV)."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app import app
from models.saas import SaasOrganization
from nodeone.services import organization_payment_methods as opm
from nodeone.services.payment_config_provision import dedicated_active_config


def main() -> int:
    errors: list[str] = []
    with app.app_context():
        for org in SaasOrganization.query.order_by(SaasOrganization.id).all():
            oid = int(org.id)
            rows = opm.list_methods_for_org(oid, enabled_only=False)
            if len(rows) < len(opm.METHOD_CATALOG):
                errors.append(f'org {oid}: matriz incompleta ({len(rows)} filas)')
            enabled_keys = {
                r.method_key for r in opm.list_methods_for_org(oid, enabled_only=True)
            }
            ctx_keys = set((opm.build_checkout_payment_context(oid).get('payment_methods') or {}).keys())
            if enabled_keys != ctx_keys:
                errors.append(
                    f'org {oid}: checkout {ctx_keys} != matriz enabled {enabled_keys}'
                )
            cfg = dedicated_active_config(oid)
            if cfg is None:
                errors.append(f'org {oid}: sin PaymentConfig dedicado')
                continue
            if int(cfg.organization_id) != oid:
                errors.append(f'org {oid}: cfg#{cfg.id} organization_id={cfg.organization_id}')
            ym = opm.get_method_row(oid, 'yappy_manual')
            iw = opm.get_method_row(oid, 'wire_international')
            if ym and bool(cfg.yappy_manual_enabled) != bool(ym.enabled):
                errors.append(f'org {oid}: yappy flag legacy != matriz')
            if iw and bool(cfg.intl_wire_enabled) != bool(iw.enabled):
                errors.append(f'org {oid}: wire flag legacy != matriz')
            if not opm.is_method_enabled(oid, 'wire_international') and 'wire_international' in ctx_keys:
                errors.append(f'org {oid}: SWIFT en checkout pero disabled en matriz')
            if opm.is_method_enabled(oid, 'wire_international') and 'wire_international' not in ctx_keys:
                errors.append(f'org {oid}: SWIFT en matriz pero no en checkout')

        if not opm.is_known_method_key('wire_international'):
            errors.append('catálogo sin wire_international')
        # IIUS / perfil internacional: PayPal + SWIFT activos es correcto (no exigir wire off en org 1).
        preset = (os.environ.get('NODEONE_BRAND_PRESET') or '').strip().lower()
        if preset not in ('iius', 'internationalinstitute') and opm.is_method_enabled(1, 'wire_international'):
            errors.append('org1: wire on — revisar si no es perfil internacional')

    if errors:
        print('FALLOS:')
        for e in errors:
            print(' ', e)
        return 1
    print('OK — pagos multi-tenant: matriz, checkout y configs dedicados coherentes.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
