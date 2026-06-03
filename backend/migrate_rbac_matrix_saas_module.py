#!/usr/bin/env python3
"""Catálogo SaaS rbac_matrix (Permisología EN1) + vínculos por org."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db  # noqa: E402
from nodeone.services.saas_catalog_defaults import (  # noqa: E402
    ensure_saas_module_catalog,
    ensure_toggleable_tenant_module_links,
)


def main():
    with app.app_context():
        from app import SaasModule, SaasOrgModule

        ensure_saas_module_catalog(printfn=print)
        ensure_toggleable_tenant_module_links(printfn=print)
        mod = SaasModule.query.filter_by(code='rbac_matrix').first()
        if mod is not None:
            for oid in (1,):
                link = SaasOrgModule.query.filter_by(organization_id=oid, module_id=mod.id).first()
                if link is not None and not link.enabled:
                    link.enabled = True
                    print(f'* saas_org_module: org={oid} rbac_matrix → on (tenant demo)')
        db.session.commit()
        print('✅ rbac_matrix en catálogo SaaS y vínculos org')


if __name__ == '__main__':
    main()
