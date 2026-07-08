"""Integración de apps — runtime por org (Etapa 5)."""

from __future__ import annotations

import os

from nodeone.core.platform.launcher import NAV_AREA_TO_PLATFORM_APP

# platform app id → nav_menu area id
PLATFORM_APP_NAV_AREA: dict[str, str] = {
    app_id: nav_id for nav_id, app_id in NAV_AREA_TO_PLATFORM_APP.items()
}
# alias registry id
PLATFORM_APP_NAV_AREA['emembership'] = 'membresias'
PLATFORM_APP_NAV_AREA['econtador'] = 'contador'
PLATFORM_APP_NAV_AREA['eworkshop'] = 'taller'
PLATFORM_APP_NAV_AREA['esales'] = 'ventas'
PLATFORM_APP_NAV_AREA['ecommunications'] = 'comunicacion'
PLATFORM_APP_NAV_AREA['eanalytics'] = 'analitica'
PLATFORM_APP_NAV_AREA['eposone'] = 'eposone'
PLATFORM_APP_NAV_AREA['epayroll'] = 'epayroll'


def nav_area_to_platform_app_id(nav_area_id: str) -> str:
    return NAV_AREA_TO_PLATFORM_APP.get((nav_area_id or '').strip(), (nav_area_id or '').strip())


def platform_app_to_nav_area(app_id: str) -> str:
    key = (app_id or '').strip().lower()
    return PLATFORM_APP_NAV_AREA.get(key, key)


def _env_runtime_for_app(app_id: str, organization_id: int) -> str | None:
    """Override por env: NODEONE_APP_RUNTIME_EMEMBERSHIP_ORG_IDS=1,2 + NODEONE_APP_RUNTIME_EMEMBERSHIP=plataforma"""
    key = (app_id or '').strip().lower().replace('-', '_')
    env_key = f'NODEONE_APP_RUNTIME_{key.upper()}_ORG_IDS'
    raw_ids = (os.environ.get(env_key) or '').strip()
    if not raw_ids:
        return None
    try:
        allowed = {int(x.strip()) for x in raw_ids.split(',') if x.strip()}
    except ValueError:
        return None
    if int(organization_id) not in allowed:
        return None
    runtime = (os.environ.get(f'NODEONE_APP_RUNTIME_{key.upper()}') or 'plataforma').strip().lower()
    if runtime not in ('legacy', 'en_migracion', 'plataforma'):
        runtime = 'plataforma'
    return runtime


def get_app_runtime(organization_id: int | None, app_id: str) -> str:
    from flask import has_app_context

    from models.platform_app import APP_RUNTIME_LEGACY, APP_RUNTIME_VALUES, PlatformOrgAppRuntime

    if organization_id is None:
        return APP_RUNTIME_LEGACY
    try:
        oid = int(organization_id)
    except (TypeError, ValueError):
        return APP_RUNTIME_LEGACY

    env_rt = _env_runtime_for_app(app_id, oid)
    if env_rt is not None:
        return env_rt

    if not has_app_context():
        return APP_RUNTIME_LEGACY

    try:
        row = PlatformOrgAppRuntime.query.filter_by(
            organization_id=oid, app_id=(app_id or '').strip().lower()
        ).first()
    except Exception:
        return APP_RUNTIME_LEGACY
    if row is None:
        return APP_RUNTIME_LEGACY
    rt = (row.runtime or APP_RUNTIME_LEGACY).strip().lower()
    return rt if rt in APP_RUNTIME_VALUES else APP_RUNTIME_LEGACY


def organization_has_integrated_apps(organization_id: int | None) -> bool:
    """True si al menos una app está en en_migracion o plataforma."""
    from nodeone.core.platform.app_registry import APPLICATIONS

    for app in APPLICATIONS:
        if app.is_shared_service:
            continue
        rt = get_app_runtime(organization_id, app.id)
        if rt in ('en_migracion', 'plataforma'):
            return True
    return False


def is_app_integrated_for_launcher(organization_id: int | None, platform_app_id: str) -> bool:
    rt = get_app_runtime(organization_id, platform_app_id)
    return rt in ('en_migracion', 'plataforma')


def app_dependencies_satisfied(organization_id: int | None, platform_app_id: str) -> bool:
    """True si las apps declaradas en ``depends_on`` están integradas (plataforma/en_migracion)."""
    from nodeone.core.platform.app_registry import get_application

    desc = get_application(platform_app_id)
    if desc is None or not desc.depends_on:
        return True
    for dep_id in desc.depends_on:
        dep_desc = get_application(dep_id)
        if dep_desc is not None and dep_desc.is_shared_service:
            continue
        if not is_app_integrated_for_launcher(organization_id, dep_id):
            return False
    return True


def filter_launcher_apps_for_org(organization_id: int | None, apps: list) -> list:
    """
    Si la org tiene apps integradas, el launcher solo muestra esas.
    Si no, devuelve la lista completa (modo apps forzado por env Etapa 3).
    """
    if not organization_has_integrated_apps(organization_id):
        return apps
    out = []
    for row in apps:
        nav_id = row.get('id')
        app_id = nav_area_to_platform_app_id(nav_id)
        if is_app_integrated_for_launcher(organization_id, app_id) and app_dependencies_satisfied(
            organization_id, app_id
        ):
            out.append(row)
    return out


def set_app_runtime(organization_id: int, app_id: str, runtime: str) -> None:
    from models.platform_app import APP_RUNTIME_VALUES, PlatformOrgAppRuntime

    from app import db

    rt = (runtime or 'legacy').strip().lower()
    if rt not in APP_RUNTIME_VALUES:
        raise ValueError(f'runtime inválido: {runtime}')
    oid = int(organization_id)
    aid = (app_id or '').strip().lower()
    row = PlatformOrgAppRuntime.query.filter_by(organization_id=oid, app_id=aid).first()
    if row is None:
        row = PlatformOrgAppRuntime(organization_id=oid, app_id=aid, runtime=rt)
        db.session.add(row)
    else:
        row.runtime = rt
    db.session.commit()
