#!/usr/bin/env python3
"""
Unifica Ventas (SaaS): ver nodeone.services.saas_catalog_defaults.

Ejecutar desde backend/:  python3 migrate_sales_saas_unified.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from nodeone.services.saas_catalog_defaults import ensure_saas_catalog_full


def main() -> None:
    with app.app_context():
        uri = app.config.get('SQLALCHEMY_DATABASE_URI') or ''
        print('DB:', uri.replace('sqlite:///', '') if uri.startswith('sqlite:///') else uri)
        ensure_saas_catalog_full(printfn=print)
        print('Listo.')


if __name__ == '__main__':
    main()
