#!/usr/bin/env python3
"""Inserta impuestos 0% y 7% para cada empresa (idempotente). Uso desde backend/:

  ../venv/bin/python3 tools/ensure_default_taxes_all_orgs.py
  ../venv/bin/python3 tools/ensure_default_taxes_all_orgs.py --org 3
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    backend = os.path.dirname(here)
    os.chdir(backend)
    if backend not in sys.path:
        sys.path.insert(0, backend)
    try:
        from dotenv import load_dotenv

        app_dir = Path(backend).resolve().parent
        load_dotenv(app_dir / '.env')
        # Silo (p. ej. /opt/easynodeone/dev/.env vía systemd EnvironmentFile)
        silo_env = app_dir.parent / '.env'
        if silo_env.is_file():
            load_dotenv(silo_env, override=True)
    except ImportError:
        pass

    parser = argparse.ArgumentParser(description='Asegurar impuestos 0% y 7% por organización.')
    parser.add_argument('--org', type=int, default=None, help='Solo esta organization_id (opcional)')
    args = parser.parse_args()

    import app as app_module
    from nodeone.services.default_taxes import ensure_default_percent_taxes

    uri = app_module.app.config.get('SQLALCHEMY_DATABASE_URI') or ''
    safe = uri
    if 'postgresql' in safe.lower() and '@' in safe:
        safe = safe.split('@')[-1]
    print('DB:', safe[:120] + ('…' if len(safe) > 120 else ''))

    with app_module.app.app_context():
        n = ensure_default_percent_taxes(
            printfn=lambda m: print(m),
            organization_id=args.org,
        )
    print(f'Listo. Filas nuevas: {n}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
