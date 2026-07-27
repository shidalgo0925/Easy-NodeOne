#!/usr/bin/env python3
"""Genera scaffold de app nativa de plataforma (Etapa 9).

Uso:
  python scripts/scaffold_platform_app.py myapp --name "My App"
  python scripts/scaffold_platform_app.py myapp --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
APP_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))


def main() -> int:
    parser = argparse.ArgumentParser(description='Scaffold app nativa EasyNodeOne Platform')
    parser.add_argument('app_id', help='Identificador (ej. myapp, eposone)')
    parser.add_argument('--name', help='Nombre visible')
    parser.add_argument('--saas-code', help='Código SaaS (default: app_id)')
    parser.add_argument('--nav-area-id', help='nav_menu area id (default: app_id)')
    parser.add_argument('--lifecycle', choices=('planned', 'active'), default='planned')
    parser.add_argument('--depends-on', default='contacts', help='CSV de app ids Core')
    parser.add_argument('--dry-run', action='store_true', help='Solo listar archivos')
    parser.add_argument('--force', action='store_true', help='Sobrescribir si existen')
    args = parser.parse_args()

    from nodeone.core.platform.app_scaffold import build_scaffold_spec, write_scaffold

    dep = tuple(x.strip() for x in (args.depends_on or '').split(',') if x.strip())
    try:
        spec = build_scaffold_spec(
            app_id=args.app_id,
            name=args.name,
            saas_code=args.saas_code,
            nav_area_id=args.nav_area_id,
            lifecycle=args.lifecycle,
            depends_on=dep or ('contacts',),
        )
        result = write_scaffold(
            spec,
            app_root=APP_ROOT,
            force=args.force,
            dry_run=args.dry_run,
        )
    except (ValueError, FileExistsError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1

    mode = 'DRY-RUN' if result['dry_run'] else 'OK'
    print(f'[{mode}] App {result["app_id"]} — {len(result["files"])} archivos:')
    for path in result['files']:
        print(f'  - {path}')
    print('\nPasos manuales restantes:')
    for line in result['instructions']:
        print(f'  {line}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
