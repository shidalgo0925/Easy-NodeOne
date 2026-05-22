#!/usr/bin/env python3
"""
Prueba mínima de lectura Odoo vía XML-RPC (solo lectura, sin modificar datos).

LEGACY / diagnóstico: en producción usar en1_connector + test_odoo_catalog.py
(ODOO_CATALOG_API_KEY, sin XML-RPC).

Uso (desde backend/):
  python3 nodeone/integrations/odoo/test_odoo_connection.py

Variables de entorno requeridas:
  ODOO_URL       — base, ej. https://odoo.ejemplo.com (sin barra final)
  ODOO_DB        — nombre de la base
  ODOO_USERNAME  — usuario API (lectura)
  ODOO_PASSWORD  — contraseña o API key del usuario
"""
from __future__ import annotations

import os
import sys
import xmlrpc.client
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


def _require_env(name: str) -> str:
    val = (os.environ.get(name) or '').strip()
    if not val:
        print(f'ERROR: falta variable de entorno {name}')
        print('Definí en .env del silo (ej. /opt/easynodeone/dev/.env):')
        print('  ODOO_URL=https://dominio-odoo.com')
        print('  ODOO_DB=nombre_base_datos')
        print('  ODOO_USERNAME=usuario_api')
        print('  ODOO_PASSWORD=clave_o_api_key')
        sys.exit(2)
    return val


def _normalize_url(url: str) -> str:
    url = url.rstrip('/')
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url


_PLACEHOLDER_PASSWORDS = frozenset({
    '…', '...', '****', '*****', '<tu clave>', 'tu clave', 'changeme', 'password',
})


def _probe_http(url: str) -> None:
    """Comprueba que el host responde vía XML-RPC version() (no autentica)."""
    probe = f'{url}/xmlrpc/2/common'
    try:
        common = xmlrpc.client.ServerProxy(probe, allow_none=True)
        common.version()
    except Exception as e:
        print(f'AVISO: no se pudo contactar {probe} ({e})')
        print('       Si Odoo está detrás de VPN/firewall, probá desde el mismo host que EN1.')


def _search_read(models, db, uid, password, model, domain, fields, limit=5):
    return models.execute_kw(
        db,
        uid,
        password,
        model,
        'search_read',
        [domain],
        {'fields': fields, 'limit': limit},
    )


def main() -> int:
    url = _normalize_url(_require_env('ODOO_URL'))
    db = _require_env('ODOO_DB')
    username = _require_env('ODOO_USERNAME')
    password = _require_env('ODOO_PASSWORD')

    print('=' * 60)
    print('EN1 — prueba Odoo XML-RPC (solo lectura)')
    print('=' * 60)
    print(f'URL:      {url}')
    print(f'DB:       {db}')
    print(f'Usuario:  {username}')
    print()

    _probe_http(url)

    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', allow_none=True)
    try:
        version_info = common.version()
        print('VERSION:', version_info)
    except Exception as e:
        print(f'ERROR leyendo version(): {e}')
        return 1

    if password.lower() in _PLACEHOLDER_PASSWORDS or password in _PLACEHOLDER_PASSWORDS:
        print('ERROR: ODOO_PASSWORD parece un marcador del ejemplo (…, <tu clave>, etc.), no la clave real.')
        return 1

    uid = common.authenticate(db, username, password, {})
    if not uid:
        print('ERROR: autenticación fallida (uid vacío).')
        print('  • Contraseña o API key incorrecta (la más frecuente).')
        print('  • Base de datos distinta (ODOO_DB).')
        print('  • Usuario desactivado o login distinto al de Odoo.')
        return 1
    print('UID:', uid)
    print()

    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', allow_none=True)

    # Dominio vacío = [] (Odoo 19 rechaza [[]] — "invalid item in domain: []")
    checks = [
        ('res.users', [['active', '=', True]], ['id', 'name', 'login']),
        # Odoo 19: sin category_id en res.groups; categoría la exportará el módulo en1_connector
        ('res.groups', [], ['id', 'name']),
        ('ir.module.module', [['state', '=', 'installed']], ['id', 'name', 'shortdesc', 'state']),
        ('ir.ui.menu', [], ['id', 'name', 'parent_id']),
        ('ir.model.access', [], ['id', 'name', 'model_id', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink']),
        ('ir.rule', [], ['id', 'name', 'model_id', 'active']),
    ]

    failed = []
    for model, domain, fields in checks:
        label = model.upper().replace('.', '_')
        try:
            rows = _search_read(models, db, uid, password, model, domain, fields, limit=5)
            print(f'{label} ({len(rows)} filas, muestra):')
            for row in rows:
                print(' ', row)
            print()
        except Exception as e:
            err = str(e)
            print(f'{label}: ERROR — {err[:500]}' + ('…' if len(err) > 500 else ''))
            if 'invalid item in domain' in err:
                print('       (dominio XML-RPC inválido; en Odoo 19 usar [] no [[]])')
            elif "KeyError: 'category_id'" in err or 'Invalid field' in err:
                print('       (campo inexistente en esta versión de Odoo; ajustar lista fields del script)')
            print()
            failed.append(model)

    print('=' * 60)
    if failed:
        print('PARCIAL: falló lectura en:', ', '.join(failed))
        print('Revisá permisos del usuario o campos del modelo en esta versión de Odoo.')
        return 1

    print('OK: autenticación y lectura básica de seguridad confirmadas.')
    print('No se creó, modificó ni borró nada en Odoo.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
