#!/usr/bin/env python3
"""Corrige columnas boolean de payment_config tras migración SQLite→PostgreSQL (pgloader → bigint).

Uso (IIUS prod):
  cd backend && source ../.venv/bin/activate
  export NODEONE_BRAND_PRESET=iius
  python scripts/fix_iius_payment_config_pg_booleans.py
  python scripts/fix_iius_payment_config_pg_booleans.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from app import app, db

# Columnas que deben ser BOOLEAN según models.payments.PaymentConfig
_BOOLEAN_COLUMNS: dict[str, bool] = {
    'yappy_manual_enabled': False,
    'yappy_requires_receipt': True,
    'yappy_admin_validation_required': True,
    'intl_wire_enabled': True,
}


def _pg_type(name: str) -> str | None:
    insp = inspect(db.engine)
    for col in insp.get_columns('payment_config'):
        if col['name'] == name:
            return str(col['type']).lower()
    return None


def fix_boolean_columns(*, apply: bool) -> list[str]:
    if db.engine.dialect.name != 'postgresql':
        print('SKIP: solo PostgreSQL')
        return []

    changes: list[str] = []
    for name, default in _BOOLEAN_COLUMNS.items():
        pg_type = _pg_type(name)
        if pg_type is None:
            print(f'  {name}: columna ausente')
            continue
        if 'bool' in pg_type:
            print(f'  {name}: ya boolean')
            continue
        changes.append(name)
        print(f'  {name}: {pg_type} -> boolean (default={default})')
        if apply:
            db.session.execute(text(f'ALTER TABLE payment_config ALTER COLUMN {name} DROP DEFAULT'))
            db.session.execute(
                text(
                    f'ALTER TABLE payment_config ALTER COLUMN {name} TYPE boolean '
                    f'USING (CASE WHEN {name} IS NULL THEN false ELSE ({name}::int <> 0) END)'
                )
            )
            db.session.execute(
                text(f'ALTER TABLE payment_config ALTER COLUMN {name} SET DEFAULT {str(default).lower()}')
            )
            db.session.commit()
    return changes


def enable_iius_wire(*, apply: bool) -> None:
    """Perfil internacional IIUS: PayPal + wire_international en checkout."""
    from nodeone.services.organization_payment_methods import (
        get_method_row,
        sync_legacy_payment_config_flags,
    )

    row = get_method_row(1, 'wire_international')
    if not row:
        print('  wire_international: fila no encontrada')
        return
    if row.enabled:
        print('  wire_international org 1: ya enabled')
    else:
        print('  wire_international org 1: enabled=false -> true')
        if apply:
            row.enabled = True
            db.session.add(row)
            db.session.commit()

    ym = get_method_row(1, 'yappy_manual')
    if ym and ym.enabled:
        print('  yappy_manual org 1: dejando disabled (perfil internacional)')
        if apply:
            ym.enabled = False
            db.session.add(ym)
            db.session.commit()
    else:
        print('  yappy_manual org 1: disabled (OK internacional)')

    if apply:
        sync_legacy_payment_config_flags(1)
        print('  sync_legacy_payment_config_flags(1): OK')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Ejecutar cambios (default: dry-run)')
    args = parser.parse_args()
    mode = 'APPLY' if args.apply else 'DRY-RUN'
    print(f'=== fix_iius_payment_config_pg_booleans ({mode}) ===')

    with app.app_context():
        cols = fix_boolean_columns(apply=args.apply)
        enable_iius_wire(apply=args.apply)

    if not args.apply and cols:
        print('\nRe-ejecutar con --apply para aplicar.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
