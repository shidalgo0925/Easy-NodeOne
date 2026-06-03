#!/usr/bin/env python3
"""Asocia el host apps.internationalinstitute.us → org IIUS (subdomain iius). Idempotente."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    from app import app, db, _organization_id_from_request_host
    from models.saas import SaasOrganization

    org_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    with app.app_context():
        org = SaasOrganization.query.get(org_id)
        if org is None:
            print(f'FAIL: org {org_id} no existe')
            return 1
        before = (org.subdomain or '').strip()
        if before.lower() not in ('', 'none', 'iius'):
            print(f'WARN: subdomain actual {before!r}; no se sobrescribe')
        else:
            org.subdomain = 'iius'
            db.session.commit()
            print(f'OK: org {org_id} subdomain → iius (antes {before!r})')
        with app.test_request_context('/', headers={'Host': 'apps.internationalinstitute.us'}):
            from flask import request

            oid = _organization_id_from_request_host(request)
            print('host resolve org_id', oid)
            if oid != org_id:
                print('FAIL: host no resuelve a org', org_id)
                return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
