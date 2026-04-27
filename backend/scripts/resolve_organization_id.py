#!/usr/bin/env python3
"""
Imprime organization_id para un subdominio saas (p. ej. relatic → apps.relatic.org).

Uso (desde app/backend, con DATABASE_URL y venv):
  python3 scripts/resolve_organization_id.py relatic
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python3 scripts/resolve_organization_id.py <subdomain>", file=sys.stderr)
        return 2
    sub = (sys.argv[1] or "").strip().lower()
    if not sub:
        return 2
    from app import app, db
    from models.saas import SaasOrganization

    with app.app_context():
        org = (
            SaasOrganization.query.filter_by(is_active=True)
            .filter(SaasOrganization.subdomain.isnot(None))
            .filter(db.func.lower(SaasOrganization.subdomain) == sub)
            .first()
        )
        if org is None:
            print(f"No hay organización activa con subdomain={sub!r}", file=sys.stderr)
            return 1
        print(org.id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
