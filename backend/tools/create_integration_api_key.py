#!/usr/bin/env python3
"""Crear Integration API Key (Sprint A — sin UI).

Uso (Dev EN1):
  cd backend && set -a && source /opt/easynodeone/dev/.env && set +a
  /opt/easynodeone/dev/venv/bin/python tools/create_integration_api_key.py \\
      --org 1 --name "Odoo Producción" --description "Integración Odoo"

La raw key se imprime una sola vez.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--org', type=int, required=True, help='organization_id')
    parser.add_argument('--name', required=True)
    parser.add_argument('--description', default='')
    args = parser.parse_args()

    from app import app
    from nodeone.services.integration_api_keys import (
        create_api_key,
        ensure_api_manager_permission,
        ensure_integration_api_tables,
    )

    with app.app_context():
        ensure_integration_api_tables()
        ensure_api_manager_permission()
        row, raw = create_api_key(
            organization_id=args.org,
            name=args.name,
            description=args.description or None,
        )
        print('id=', row.id)
        print('prefix=', row.key_prefix)
        print('organization_id=', row.organization_id)
        print('RAW_KEY (guardar ahora)=', raw)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
