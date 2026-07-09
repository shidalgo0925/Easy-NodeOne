"""Registro y descubrimiento de manifests de apps de plataforma (Etapa 9)."""

from __future__ import annotations

import importlib
from typing import Any

# Apps con manifest oficial (integración Etapa 5+ y nativas Etapa 6+).
PLATFORM_MANIFEST_MODULES: tuple[str, ...] = (
    'nodeone.modules.emembership.manifest',
    'nodeone.modules.ecrm.manifest',
    'nodeone.modules.eevents.manifest',
    'nodeone.modules.ecertificates.manifest',
    'nodeone.modules.eappointments.manifest',
    'nodeone.modules.eposone.manifest',
    'nodeone.modules.epayroll.manifest',
)

REQUIRED_MANIFEST_KEYS: frozenset[str] = frozenset({'id', 'name', 'saas_codes'})

LIFECYCLE_PLANNED = 'planned'
LIFECYCLE_ACTIVE = 'active'

NEW_APP_MANIFEST_TEMPLATE: dict[str, Any] = {
    'id': 'myapp',
    'name': 'MyApp',
    'saas_codes': ('myapp',),
    'nav_area_id': 'myapp',
    'depends_on': ('contacts',),
    'native_platform': True,
    'lifecycle': LIFECYCLE_PLANNED,
    'register': 'nodeone.modules.myapp.register.register_myapp_blueprints',
    'zone_blueprints': ('myapp',),
    'zone_path_prefixes': ('/admin/myapp',),
    'zone_endpoints': ('myapp.myapp_home',),
    'notes': (
        'App nativa Carril 2 — solo Core; sin importar otras apps de negocio.',
        'Publicar cambios de dominio vía bus de eventos (Etapa 8).',
    ),
}


def load_manifest(module_path: str) -> dict[str, Any]:
    mod = importlib.import_module(module_path)
    data = getattr(mod, 'MODULE', None)
    if not isinstance(data, dict):
        raise ValueError(f'{module_path}: MODULE dict ausente')
    return dict(data)


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    """Devuelve lista de errores (vacía = válido)."""
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ['manifest debe ser dict']

    missing = REQUIRED_MANIFEST_KEYS - set(manifest.keys())
    if missing:
        errors.append(f'faltan claves: {sorted(missing)}')

    app_id = (manifest.get('id') or '').strip().lower()
    if not app_id:
        errors.append('id vacío')

    saas = manifest.get('saas_codes')
    if not saas or not isinstance(saas, (tuple, list)):
        errors.append('saas_codes debe ser tupla/lista no vacía')

    lifecycle = (manifest.get('lifecycle') or LIFECYCLE_ACTIVE).strip().lower()
    if lifecycle not in (LIFECYCLE_ACTIVE, LIFECYCLE_PLANNED):
        errors.append(f'lifecycle inválido: {lifecycle}')

    if lifecycle == LIFECYCLE_ACTIVE and not manifest.get('register'):
        errors.append('apps active requieren register')

    dep = manifest.get('depends_on', ())
    if dep is not None and not isinstance(dep, (tuple, list)):
        errors.append('depends_on debe ser tupla/lista')

    return errors


def discover_platform_manifests(
    *,
    module_paths: tuple[str, ...] | None = None,
    skip_invalid: bool = False,
) -> dict[str, dict[str, Any]]:
    """
    Carga todos los manifests declarados.
    Clave: app id en minúsculas.
    """
    paths = module_paths or PLATFORM_MANIFEST_MODULES
    out: dict[str, dict[str, Any]] = {}
    for path in paths:
        manifest = load_manifest(path)
        errors = validate_manifest(manifest)
        if errors:
            if skip_invalid:
                continue
            raise ValueError(f'{path}: ' + '; '.join(errors))
        app_id = (manifest.get('id') or '').strip().lower()
        out[app_id] = manifest
    return out


def manifest_ids() -> tuple[str, ...]:
    return tuple(sorted(discover_platform_manifests().keys()))


def get_manifest(app_id: str) -> dict[str, Any] | None:
    key = (app_id or '').strip().lower()
    try:
        return discover_platform_manifests().get(key)
    except ValueError:
        return None


def registry_alignment_errors() -> list[str]:
    """Comprueba manifest active ↔ ApplicationDescriptor en app_registry."""
    from nodeone.core.platform.app_registry import get_application

    errors: list[str] = []
    for app_id, manifest in discover_platform_manifests().items():
        lifecycle = (manifest.get('lifecycle') or LIFECYCLE_ACTIVE).strip().lower()
        desc = get_application(app_id)
        if desc is None:
            if lifecycle == LIFECYCLE_PLANNED:
                continue
            errors.append(f'manifest {app_id} sin ApplicationDescriptor en app_registry')
            continue
        reg_saas = set(desc.saas_codes)
        man_saas = {str(c).strip() for c in (manifest.get('saas_codes') or ()) if str(c).strip()}
        if reg_saas != man_saas:
            errors.append(f'{app_id}: saas_codes manifest {man_saas} != registry {reg_saas}')
    return errors


def saas_catalog_code_set() -> frozenset[str]:
    from nodeone.services.saas_catalog_defaults import SAAS_CATALOG_MODULES

    return frozenset(code for code, *_rest in SAAS_CATALOG_MODULES)


def saas_catalog_alignment_errors() -> list[str]:
    """Cada saas_code de manifest active debe existir en SAAS_CATALOG_MODULES."""
    catalog = saas_catalog_code_set()
    errors: list[str] = []
    for app_id, manifest in discover_platform_manifests().items():
        lifecycle = (manifest.get('lifecycle') or LIFECYCLE_ACTIVE).strip().lower()
        if lifecycle == LIFECYCLE_PLANNED:
            continue
        for code in manifest.get('saas_codes') or ():
            c = str(code).strip()
            if c and c not in catalog:
                errors.append(f'{app_id}: saas_code {c!r} ausente en saas_catalog_defaults')
    return errors


def _manifest_module_listed(app_id: str) -> bool:
    needle = f'.{app_id.strip().lower()}.manifest'
    return any(needle in path for path in PLATFORM_MANIFEST_MODULES)


def platform_app_checklist(app_id: str) -> dict[str, Any]:
    """Checklist Etapa 9 para registrar una app de plataforma."""
    key = (app_id or '').strip().lower()
    manifest = get_manifest(key)
    if manifest is None:
        return {
            'app_id': key,
            'found': False,
            'checklist': {},
            'errors': ['manifest_not_found'],
            'ready': False,
        }

    from nodeone.core.platform.app_registry import get_application
    from nodeone.core.platform.launcher import NAV_AREA_TO_PLATFORM_APP

    validation_errors = validate_manifest(manifest)
    registry_desc = get_application(key)
    saas_codes = {str(c).strip() for c in (manifest.get('saas_codes') or ()) if str(c).strip()}
    catalog = saas_catalog_code_set()
    nav_id = (manifest.get('nav_area_id') or '').strip()
    lifecycle = (manifest.get('lifecycle') or LIFECYCLE_ACTIVE).strip().lower()

    checklist = {
        'manifest_valid': len(validation_errors) == 0,
        'listed_in_platform_manifest_modules': _manifest_module_listed(key),
        'app_registry_descriptor': registry_desc is not None or lifecycle == LIFECYCLE_PLANNED,
        'saas_catalog_codes': all(c in catalog for c in saas_codes) if saas_codes else False,
        'launcher_nav_mapping': not nav_id or NAV_AREA_TO_PLATFORM_APP.get(nav_id) == key,
        'register_hook': bool(manifest.get('register')) or lifecycle == LIFECYCLE_PLANNED,
    }

    errors: list[str] = list(validation_errors)
    if not checklist['listed_in_platform_manifest_modules']:
        errors.append('no listada en PLATFORM_MANIFEST_MODULES')
    if lifecycle != LIFECYCLE_PLANNED and registry_desc is None:
        errors.append('sin ApplicationDescriptor en app_registry')
    if lifecycle != LIFECYCLE_PLANNED:
        missing_saas = sorted(s for s in saas_codes if s not in catalog)
        if missing_saas:
            errors.append(f'saas_codes ausentes en catálogo: {missing_saas}')
    if nav_id and NAV_AREA_TO_PLATFORM_APP.get(nav_id) != key:
        errors.append(f'nav_area_id {nav_id!r} no mapea a {key} en launcher')

    return {
        'app_id': key,
        'found': True,
        'lifecycle': lifecycle,
        'checklist': checklist,
        'errors': errors,
        'ready': len(errors) == 0,
    }


def manifest_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    """Vista resumida para listados API (Etapa 9)."""
    lifecycle = (manifest.get('lifecycle') or LIFECYCLE_ACTIVE).strip().lower()
    return {
        'id': (manifest.get('id') or '').strip().lower(),
        'name': manifest.get('name'),
        'saas_codes': list(manifest.get('saas_codes') or ()),
        'lifecycle': lifecycle,
        'native_platform': bool(manifest.get('native_platform')),
        'depends_on': list(manifest.get('depends_on') or ()),
        'nav_area_id': manifest.get('nav_area_id'),
        'integration_order': manifest.get('integration_order'),
        'has_register': bool(manifest.get('register')),
    }


def platform_apps_health() -> dict[str, Any]:
    """Estado de alineación manifest ↔ registry ↔ saas_catalog (Etapa 9)."""
    registry_errors = registry_alignment_errors()
    saas_errors = saas_catalog_alignment_errors()
    errors = registry_errors + saas_errors
    manifests = discover_platform_manifests()
    return {
        'alignment_ok': len(errors) == 0,
        'registry_ok': len(registry_errors) == 0,
        'saas_catalog_ok': len(saas_errors) == 0,
        'errors': errors,
        'registry_errors': registry_errors,
        'saas_catalog_errors': saas_errors,
        'manifest_count': len(manifests),
        'app_ids': sorted(manifests.keys()),
    }


def warn_registry_misalignment() -> None:
    """Log no fatal al arrancar si manifest, registry o saas_catalog divergen."""
    try:
        for err in registry_alignment_errors():
            print(f'⚠️ platform manifest alignment: {err}')
        for err in saas_catalog_alignment_errors():
            print(f'⚠️ platform saas catalog alignment: {err}')
    except Exception as exc:
        print(f'⚠️ platform manifest alignment check: {exc}')
