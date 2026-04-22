#!/usr/bin/env python3
"""
Atajo legado: mismas columnas que el primer parche manual tras restore.

**Preferí** `sync_sqlite_columns_from_models.py` → usa `nodeone.services.sqlite_schema_sync`
y cubre todo el esquema según los modelos.

Uso (desde backend/):
  ../venv/bin/python3 patch_sqlite_schema_after_legacy_restore.py
  NODEONE_SQLITE=/ruta/NodeOne.db ../venv/bin/python3 patch_sqlite_schema_after_legacy_restore.py
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_DB = ROOT / 'instance' / 'NodeOne.db'


def main() -> int:
    p = Path(os.environ.get('NODEONE_SQLITE') or str(DEFAULT_DB)).resolve()
    if not p.is_file():
        print('No existe:', p, file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(p))
    cur = conn.cursor()

    def ensure_col(table: str, col: str, ddl_suffix: str) -> None:
        cur.execute(f'PRAGMA table_info({table})')
        cols = [r[1] for r in cur.fetchall()]
        if col not in cols:
            cur.execute(f'ALTER TABLE {table} ADD COLUMN {col} {ddl_suffix}')
            print(f'+ {table}.{col}')

    # user (marketing + multi-tenant)
    ensure_col('user', 'email_marketing_status', "VARCHAR(20) DEFAULT 'subscribed'")
    ensure_col('user', 'organization_id', 'INTEGER NOT NULL DEFAULT 1')

    # smtp por tenant + marketing
    ensure_col('email_config', 'organization_id', 'INTEGER')
    ensure_col('email_config', 'use_for_marketing', 'BOOLEAN DEFAULT 0')
    cur.execute('UPDATE email_config SET organization_id = 1 WHERE organization_id IS NULL')

    # citas
    ensure_col('appointment', 'organization_id', 'INTEGER NOT NULL DEFAULT 1')
    ensure_col('appointment', 'reminder_24h_sent_at', 'DATETIME')
    ensure_col('appointment', 'reminder_1h_sent_at', 'DATETIME')

    # plantillas correo por tenant
    ensure_col('email_template', 'organization_id', 'INTEGER NOT NULL DEFAULT 1')

    conn.commit()
    conn.close()
    print('OK', p)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
