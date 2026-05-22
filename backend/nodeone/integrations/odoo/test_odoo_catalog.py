#!/usr/bin/env python3
"""
Prueba Fase 1: descarga catálogo vía en1_connector (HTTP), sin XML-RPC.

Uso:
  export ODOO_CATALOG_API_KEY='...'
  export ODOO_DB=modecosa
  python3 nodeone/integrations/odoo/test_odoo_catalog.py

Opcional:
  ODOO_CATALOG_URL=https://erp.modecosa.com/api/en1/v1/security-catalog
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[3]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

try:
    from dotenv import load_dotenv

    for _env in (
        _BACKEND.parent / '.env',
        Path('/opt/easynodeone/dev/.env'),
        Path('/opt/easynodeone/relatic/.env'),
    ):
        if _env.is_file():
            load_dotenv(_env)
            break
except ImportError:
    pass

from nodeone.integrations.odoo.catalog_client import (  # noqa: E402
    OdooCatalogError,
    catalog_config_from_env,
    catalog_summary,
    fetch_security_catalog,
)


def main() -> int:
    print('=' * 60)
    print('EN1 — prueba catálogo Odoo (en1_connector Fase 1)')
    print('=' * 60)

    try:
        url, _, database = catalog_config_from_env()
    except OdooCatalogError as e:
        print(f'ERROR: {e}')
        print('Definí en .env del silo (canal seguro, no git):')
        print('  ODOO_CATALOG_API_KEY=<key desde Ajustes → EN1 Connector>')
        print('  ODOO_DB=modecosa')
        print('  ODOO_CATALOG_URL=https://erp.modecosa.com/api/en1/v1/security-catalog')
        return 2

    print(f'URL:  {url}')
    print(f'BD:   {database} (header X-Odoo-Database)')
    print('Auth: Bearer ODOO_CATALOG_API_KEY')
    print()

    try:
        data = fetch_security_catalog()
    except OdooCatalogError as e:
        print(f'ERROR: {e}')
        return 1

    print('OK:', catalog_summary(data))
    meta = data.get('meta') or {}
    print('Generado:', meta.get('generated_at'))
    print()

    groups_with_xml = sum(1 for g in data['groups'] if g.get('xml_id'))
    print(f'Grupos con xml_id: {groups_with_xml}/{len(data["groups"])}')
    print('Muestra grupo:', json.dumps(data['groups'][0], ensure_ascii=False))
    print('Muestra usuario:', json.dumps(data['users'][0], ensure_ascii=False))
    if data['memberships']:
        print('Muestra membresía:', json.dumps(data['memberships'][0], ensure_ascii=False))
    if data['critical_groups']:
        print('Grupos críticos:', len(data['critical_groups']))

    print()
    print('=' * 60)
    print('OK: catálogo recibido y validado (solo lectura, sin XML-RPC).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
