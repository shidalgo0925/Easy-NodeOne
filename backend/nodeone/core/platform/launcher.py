"""Launcher v2 — Mis aplicaciones (Etapa 3)."""

from __future__ import annotations

import os
from typing import Any

SESSION_ACTIVE_APP_KEY = 'platform_active_app_id'

# nav_menu area id → platform app registry id
NAV_AREA_TO_PLATFORM_APP: dict[str, str] = {
    'crm': 'ecrm',
    'membresias': 'emembership',
    'eventos': 'eevents',
    'certificados': 'ecertificates',
    'agenda': 'eappointments',
    'educacion': 'academic',
    'ventas': 'esales',
    'efactura': 'efactura',
    'comunicacion': 'ecommunications',
    'analitica': 'eanalytics',
    'taller': 'eworkshop',
    'contador': 'econtador',
    'contactos': 'contacts',
    'tienda': 'tienda',
    'finanzas': 'finanzas',
    'config': 'config',
    'plataforma': 'plataforma',
    'matriz_odoo': 'security_matrix',
    'permisologia': 'rbac_matrix',
}


def _parse_org_id_list(env_name: str) -> set[int] | None:
    raw = (os.environ.get(env_name) or '').strip()
    if not raw:
        return None
    out: set[int] = set()
    for part in raw.split(','):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(int(part))
        except ValueError:
            continue
    return out or None


def launcher_mode_for_organization(organization_id: int | None) -> str:
    """
    ``classic`` — sidebar ERP actual (IIUS/Relatic por defecto).
    ``apps`` — pantalla Mis aplicaciones + sesión ``platform_active_app_id``.

    Env:
    - ``NODEONE_LAUNCHER_MODE`` = classic | apps (default classic)
    - ``NODEONE_LAUNCHER_APPS_ORG_IDS`` = 1,2 — fuerza apps en esas orgs
    - ``NODEONE_LAUNCHER_CLASSIC_ORG_IDS`` = 3,4 — fuerza classic aunque mode global sea apps
    """
    mode = (os.environ.get('NODEONE_LAUNCHER_MODE') or 'classic').strip().lower()
    if mode not in ('classic', 'apps'):
        mode = 'classic'
    oid = None
    if organization_id is not None:
        try:
            oid = int(organization_id)
        except (TypeError, ValueError):
            oid = None

    classic_orgs = _parse_org_id_list('NODEONE_LAUNCHER_CLASSIC_ORG_IDS')
    if oid is not None and classic_orgs and oid in classic_orgs:
        return 'classic'

    apps_orgs = _parse_org_id_list('NODEONE_LAUNCHER_APPS_ORG_IDS')
    if oid is not None and apps_orgs and oid in apps_orgs:
        return 'apps'

    return mode


def get_active_app_id(session) -> str | None:
    raw = session.get(SESSION_ACTIVE_APP_KEY)
    if not raw:
        return None
    return str(raw).strip() or None


def set_active_app_id(session, area_id: str | None) -> None:
    if not area_id:
        session.pop(SESSION_ACTIVE_APP_KEY, None)
        return
    session[SESSION_ACTIVE_APP_KEY] = str(area_id).strip()


def build_nav_context_for_user(user):
    """NavContext con las mismas reglas que inject_admin_nav_context."""
    from flask import current_app

    from app import (
        _nav_can_permission,
        _org_id_for_module_visibility,
        has_view_endpoint,
        saas_module_enabled,
        saas_module_enabled_chain,
    )
    from nodeone.core.nav_menu import build_nav_context
    from nodeone.core.template_context_gates import user_can_see_tenant_admin_menu
    from nodeone.services.academic_module import is_academic_module_enabled_for_org
    from nodeone.services.office365_module import is_office365_module_enabled_for_org

    show_tenant_admin = user_can_see_tenant_admin_menu(user)
    is_platform_admin = bool(getattr(user, 'is_admin', False))
    org_id = _org_id_for_module_visibility()
    show_academic = (
        'academic_admin' in current_app.blueprints
        and is_academic_module_enabled_for_org(org_id)
    )
    return build_nav_context(
        nav_can=_nav_can_permission,
        saas_module_enabled=saas_module_enabled,
        saas_module_enabled_chain=saas_module_enabled_chain,
        has_view_endpoint=has_view_endpoint,
        show_academic_admin_nav=show_academic,
        office365_module_enabled=is_office365_module_enabled_for_org(org_id),
        show_platform_admin_nav=is_platform_admin,
        is_platform_admin=is_platform_admin,
        is_advisor=False,
        show_tenant_admin_menu=show_tenant_admin,
    )


def visible_launcher_apps(ctx) -> list[dict[str, Any]]:
    """Apps visibles para el usuario (mismas reglas que sidebar ERP)."""
    from nodeone.core.nav_menu import visible_areas

    apps: list[dict[str, Any]] = []
    for area in visible_areas(ctx):
        area_id = area.get('id')
        if not area_id:
            continue
        platform_app_id = NAV_AREA_TO_PLATFORM_APP.get(area_id, area_id)
        apps.append(
            {
                'id': area_id,
                'platform_app_id': platform_app_id,
                'label': area.get('label') or area_id,
                'icon': area.get('icon') or 'fas fa-th',
                'url': area.get('url') or '#',
            }
        )
    return apps


def post_login_redirect_target(*, next_page: str | None, user, session) -> str:
    """URL destino tras login / selector de org (respeta launcher v2)."""
    from flask import url_for

    if next_page:
        return next_page

    from nodeone.core.template_context_gates import user_can_see_tenant_admin_menu

    if not user_can_see_tenant_admin_menu(user):
        return url_for('dashboard')

    from app import _org_id_for_module_visibility

    org_id = _org_id_for_module_visibility()
    if launcher_mode_for_organization(org_id) != 'apps':
        try:
            return url_for('admin_dashboard')
        except Exception:
            return url_for('dashboard')

    ctx = build_nav_context_for_user(user)
    apps = visible_launcher_apps(ctx)
    if not apps:
        try:
            return url_for('admin_dashboard')
        except Exception:
            return url_for('dashboard')
    if len(apps) == 1:
        set_active_app_id(session, apps[0]['id'])
        return apps[0]['url']
    return url_for('platform_launcher.apps_home')
