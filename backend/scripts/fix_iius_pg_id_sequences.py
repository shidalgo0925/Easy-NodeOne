#!/usr/bin/env python3
"""Crea/sincroniza secuencias PostgreSQL en columnas id tras migración SQLite (pgloader).

Sin secuencia, INSERT falla: null value in column "id" violates not-null constraint.

Uso:
  cd backend && source ../.venv/bin/activate
  export NODEONE_BRAND_PRESET=iius
  python scripts/fix_iius_pg_id_sequences.py
  python scripts/fix_iius_pg_id_sequences.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from app import app, db


def _tables_missing_id_sequence() -> list[tuple[str, int]]:
    if db.engine.dialect.name != 'postgresql':
        return []
    insp = inspect(db.engine)
    out: list[tuple[str, int]] = []
    for table in sorted(insp.get_table_names()):
        cols = {c['name']: c for c in insp.get_columns(table)}
        if 'id' not in cols:
            continue
        typ = str(cols['id']['type']).upper()
        if 'INT' not in typ and 'SERIAL' not in typ:
            continue
        seq = db.session.execute(
            text('SELECT pg_get_serial_sequence(:t, :c)'),
            {'t': table, 'c': 'id'},
        ).scalar()
        if seq:
            continue
        mx = db.session.execute(text(f'SELECT COALESCE(MAX(id), 0) FROM "{table}"')).scalar()
        out.append((table, int(mx or 0)))
    return out


def fix_sequences(*, apply: bool) -> list[str]:
    fixed: list[str] = []
    for table, max_id in _tables_missing_id_sequence():
        seq_name = f'{table}_id_seq'
        print(f'  {table}: max_id={max_id} -> {seq_name}')
        if not apply:
            fixed.append(table)
            continue
        db.session.execute(text(f'CREATE SEQUENCE IF NOT EXISTS "{seq_name}"'))
        db.session.execute(
            text(f'ALTER TABLE "{table}" ALTER COLUMN id SET DEFAULT nextval(\'"{seq_name}"\')')
        )
        if max_id <= 0:
            db.session.execute(text(f"SELECT setval('\"{seq_name}\"', 1, false)"))
        else:
            db.session.execute(
                text(f"SELECT setval('\"{seq_name}\"', :mx, true)"),
                {'mx': max_id},
            )
        db.session.commit()
        fixed.append(table)
    return fixed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    mode = 'APPLY' if args.apply else 'DRY-RUN'
    print(f'=== fix_iius_pg_id_sequences ({mode}) ===')

    with app.app_context():
        tables = fix_sequences(apply=args.apply)

    print(f'\nTablas sin secuencia: {len(tables)}')
    if not args.apply and tables:
        print('Re-ejecutar con --apply para corregir.')
    elif args.apply and tables:
        print('OK — secuencias creadas/sincronizadas.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
