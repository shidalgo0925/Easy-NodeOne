"""
Cliente HTTP para catálogo de seguridad Odoo (módulo en1_connector, Fase 1).

Variables de entorno:
  ODOO_CATALOG_URL   — default: .../api/en1/v1/security-catalog
  ODOO_CATALOG_API_KEY — Bearer, solo lectura
  ODOO_DB            — BD Odoo (header X-Odoo-Database), ej. modecosa
"""
from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_CATALOG_URL = 'https://erp.modecosa.com/api/en1/v1/security-catalog'
SCHEMA_VERSION = '1.0'
REQUIRED_ROOT_KEYS = frozenset({
    'meta', 'users', 'groups', 'memberships', 'critical_groups',
})


class OdooCatalogError(Exception):
    """Error al obtener o validar el catálogo EN1."""


def catalog_config_from_env() -> tuple[str, str, str]:
    url = (os.environ.get('ODOO_CATALOG_URL') or DEFAULT_CATALOG_URL).strip().rstrip('/')
    api_key = (os.environ.get('ODOO_CATALOG_API_KEY') or '').strip()
    database = (os.environ.get('ODOO_DB') or os.environ.get('ODOO_CATALOG_DB') or 'modecosa').strip()
    if not api_key:
        raise OdooCatalogError(
            'Falta ODOO_CATALOG_API_KEY (generar en Odoo: Ajustes → EN1 Connector).'
        )
    return url, api_key, database


def catalog_timeout_seconds() -> int:
    raw = (os.environ.get('ODOO_CATALOG_TIMEOUT') or '30').strip()
    try:
        t = int(raw)
    except ValueError:
        t = 30
    return max(5, min(t, 120))


def fetch_security_catalog(
    url: str | None = None,
    api_key: str | None = None,
    database: str | None = None,
    *,
    timeout: int | None = None,
    include: str | None = None,
) -> dict[str, Any]:
    """
    GET security-catalog. Retorna el JSON parseado.
    """
    if url is None or api_key is None or database is None:
        env_url, env_key, env_db = catalog_config_from_env()
        url = url or env_url
        api_key = api_key or env_key
        database = database or env_db
    if timeout is None:
        timeout = catalog_timeout_seconds()

    fetch_url = url
    if include:
        sep = '&' if '?' in fetch_url else '?'
        fetch_url = f'{fetch_url}{sep}include={include}'

    headers = {
        'Authorization': f'Bearer {api_key}',
        'X-Odoo-Database': database,
        'Accept': 'application/json',
    }
    req = Request(fetch_url, headers=headers, method='GET')

    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            status = getattr(resp, 'status', 200)
    except HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')[:500]
        raise OdooCatalogError(f'HTTP {e.code} al obtener catálogo: {body}') from e
    except URLError as e:
        raise OdooCatalogError(f'Error de red: {e}') from e

    if status != 200:
        raise OdooCatalogError(f'HTTP {status} inesperado')

    try:
        data = json.loads(raw.decode('utf-8'))
    except json.JSONDecodeError as e:
        raise OdooCatalogError(f'Respuesta no es JSON válido: {e}') from e

    if not isinstance(data, dict):
        raise OdooCatalogError('El catálogo debe ser un objeto JSON')

    data = normalize_security_catalog(data)
    validate_security_catalog(data)
    return data


def normalize_security_catalog(data: dict[str, Any]) -> dict[str, Any]:
    """
    Acepta JSON plano de en1_connector (schema/version en raíz) o spec con bloque meta.
    """
    if 'meta' in data and isinstance(data.get('meta'), dict):
        return data

    version = str(data.get('version') or SCHEMA_VERSION)
    counts = data.get('counts') or data.get('record_counts') or {}
    if not isinstance(counts, dict):
        counts = {}

    return {
        'meta': {
            'schema_version': version,
            'export_type': 'security_catalog',
            'generated_at': data.get('generated_at', ''),
            'database': data.get('database', ''),
            'odoo_version': data.get('odoo_version', ''),
            'exporter': data.get('exporter') or 'en1_connector',
            'exporter_version': str(data.get('exporter_version') or data.get('schema') or ''),
            'record_counts': counts,
        },
        'users': data.get('users') or [],
        'groups': data.get('groups') or [],
        'memberships': data.get('memberships') or [],
        'critical_groups': data.get('critical_groups') or [],
    }


def validate_security_catalog(data: dict[str, Any]) -> None:
    """Validación mínima alineada a en1_security_catalog_v1 (sin dependencia jsonschema)."""
    missing = REQUIRED_ROOT_KEYS - set(data.keys())
    if missing:
        raise OdooCatalogError(f'Faltan claves en el catálogo: {sorted(missing)}')

    meta = data.get('meta') or {}
    if meta.get('schema_version') != SCHEMA_VERSION:
        raise OdooCatalogError(
            f"schema_version esperado {SCHEMA_VERSION!r}, recibido {meta.get('schema_version')!r}"
        )
    if meta.get('export_type') != 'security_catalog':
        raise OdooCatalogError('meta.export_type debe ser security_catalog')

    for key in ('users', 'groups', 'memberships', 'critical_groups'):
        if not isinstance(data[key], list):
            raise OdooCatalogError(f'{key} debe ser una lista')

    groups = data['groups']
    without_xml = [g for g in groups if isinstance(g, dict) and not (g.get('xml_id') or '').strip()]
    if without_xml and len(without_xml) == len(groups):
        raise OdooCatalogError('Ningún grupo trae xml_id; revisar export en1_connector')

    for i, u in enumerate(data['users'][:3]):
        if not isinstance(u, dict) or not u.get('login'):
            raise OdooCatalogError(f'users[{i}] inválido: falta login')

    counts = meta.get('record_counts') or {}
    for name, arr in (
        ('users', data['users']),
        ('groups', data['groups']),
        ('memberships', data['memberships']),
    ):
        expected = counts.get(name)
        if expected is not None and expected != len(arr):
            raise OdooCatalogError(
                f'record_counts.{name}={expected} pero len({name})={len(arr)}'
            )


def catalog_summary(data: dict[str, Any]) -> str:
    meta = data.get('meta') or {}
    rc = meta.get('record_counts') or {}
    return (
        f"BD={meta.get('database')} Odoo={meta.get('odoo_version')} "
        f"exporter={meta.get('exporter')} {meta.get('exporter_version')} | "
        f"users={len(data.get('users', []))} groups={len(data.get('groups', []))} "
        f"memberships={len(data.get('memberships', []))} "
        f"critical_groups={len(data.get('critical_groups', []))}"
    )
