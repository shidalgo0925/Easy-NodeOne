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
    """
    Comprueba que cada manifest con lifecycle active tenga entrada en app_registry.
    """
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
