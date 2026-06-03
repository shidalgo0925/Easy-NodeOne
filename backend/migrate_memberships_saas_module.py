#!/usr/bin/env python3
"""Catálogo SaaS memberships (Membresías) + vínculos por org."""

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
        ensure_saas_module_catalog(printfn=print)
        ensure_toggleable_tenant_module_links(printfn=print)
        db.session.commit()
        print('✅ memberships en catálogo SaaS y vínculos org')


if __name__ == '__main__':
    main()
