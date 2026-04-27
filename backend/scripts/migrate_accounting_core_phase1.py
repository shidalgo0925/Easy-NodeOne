"""
Migración progresiva Fase 1 (motor contable ERP).

Uso (desde backend con entorno cargado):
  python3 scripts/migrate_accounting_core_phase1.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    from app import app
    from nodeone.modules.accounting_core.service import ensure_accounting_core_schema

    with app.app_context():
        ensure_accounting_core_schema()
        print('OK: tablas núcleo contable verificadas/creadas (account, journal, journal_entry, journal_item).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
