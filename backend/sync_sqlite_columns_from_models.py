#!/usr/bin/env python3
"""
CLI: añade columnas SQLite faltantes respecto a los modelos ORM.

Implementación: `nodeone.services.sqlite_schema_sync`.

  ../venv/bin/python3 sync_sqlite_columns_from_models.py
  ../venv/bin/python3 sync_sqlite_columns_from_models.py --dry-run
  ../venv/bin/python3 sync_sqlite_columns_from_models.py --no-backfill
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    parser = argparse.ArgumentParser(description='Sincronizar columnas SQLite con modelos SQLAlchemy.')
    parser.add_argument('--dry-run', action='store_true', help='Solo listar ALTER; no escribe la BD')
    parser.add_argument(
        '--no-backfill',
        action='store_true',
        help='No ejecutar UPDATE organization_id = 1 donde sea NULL (email_config, appointment_type, payment_config)',
    )
    args = parser.parse_args()

    from app import app, db
    from nodeone.services.sqlite_schema_sync import collect_missing_sqlite_columns, run_sqlite_schema_sync

    with app.app_context():
        if args.dry_run:
            planned = collect_missing_sqlite_columns(db)
            for table_name, _col, ddl in planned:
                print(f'ALTER TABLE {table_name} ADD COLUMN {ddl};')
            print(f'-- {len(planned)} columnas')
            return 0

        report = run_sqlite_schema_sync(db, dry_run=False, backfill_org_ids=not args.no_backfill)
        for table_name, col in report.applied_columns:
            print(f'+ {table_name}.{col}')
        for sql, err in report.errors:
            print(f'X {sql[:70]}... -> {err}', file=sys.stderr)
        if report.backfill_statements_run:
            print(f'backfill org_id filas afectadas (aprox.): {report.backfill_statements_run}')
        print(f'OK ({report.applied} columnas nuevas, {len(report.errors)} errores)')
        return 1 if report.errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
