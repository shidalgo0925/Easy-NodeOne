#!/usr/bin/env python3
"""
Elimina todo el catálogo de servicios en la BD actual (PostgreSQL dev):
  appointment.service_id → NULL, luego service_pricing_rule, service, service_category.

No borra usuarios, organizaciones ni citas (solo desvincula service_id).

Uso (desde backend/, con .env del silo cargado):
  python tools/wipe_service_catalog_pg.py
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from sqlalchemy import text


def main() -> int:
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    repo_root = os.path.abspath(os.path.join(backend_dir, '..'))
    sys.path.insert(0, backend_dir)
    os.chdir(backend_dir)
    load_dotenv(os.path.join(repo_root, '..', '.env'))

    import app as M

    with M.app.app_context():
        M.db.session.execute(
            text('UPDATE appointment SET service_id = NULL WHERE service_id IS NOT NULL')
        )
        M.db.session.execute(text('DELETE FROM service_pricing_rule'))
        M.db.session.execute(text('DELETE FROM service'))
        M.db.session.execute(text('DELETE FROM service_category'))
        M.db.session.commit()
        print('OK: catálogo de servicios vaciado (citas conservadas, service_id anulado).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
