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
    'eposone': 'eposone',
    'epayroll': 'epayroll',
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
    'facturacion': 'finanzas',
    'cobros': 'finanzas',
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

    if oid is not None:
        from nodeone.core.platform.app_integration import organization_has_integrated_apps

        if organization_has_integrated_apps(oid):
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


def visible_launcher_apps(ctx, organization_id: int | None = None) -> list[dict[str, Any]]:
    """Apps visibles para el usuario (mismas reglas que sidebar ERP)."""
    from flask import has_request_context

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
    if organization_id is None and has_request_context():
        try:
            from app import _org_id_for_module_visibility

            organization_id = _org_id_for_module_visibility()
        except Exception:
            organization_id = None
    if organization_id is not None:
        from nodeone.core.platform.app_integration import filter_launcher_apps_for_org

        apps = filter_launcher_apps_for_org(organization_id, apps)
    return apps


def post_login_redirect_target(*, next_page: str | None, user, session) -> str:
    """URL destino tras login / selector de org (ADR-013 + ADR-017 lanzador)."""
    from flask import url_for

    if next_page:
        return next_page

    # ADR-013 / ADR-017:
    # - Host portal → siempre Portal (Caso C)
    # - Host product + 1 usable matching → dashboard producto (Caso A)
    # - Host product + 0/N → Mis Productos (Caso B)
    try:
        from nodeone.core.platform.context_resolver import current_app_context

        app_ctx = current_app_context()
        if app_ctx.surface == 'portal':
            return url_for('ets_portal.home')
        if app_ctx.surface == 'product':
            return _product_host_post_login_target(app_ctx, session)
    except Exception:
        pass

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


def _product_host_post_login_target(app_ctx, session) -> str:
    """ADR-017 Hito 4 — lanzador inteligente en Host de producto."""
    from flask import url_for

    host_code = (app_ctx.product_code or '').strip().lower()
    usable: list[dict] = []
    try:
        from nodeone.modules.ets_portal.portal_service import PortalService

        usable = PortalService.list_usable_products_for_current_tenant()
    except Exception:
        usable = []

    if len(usable) == 1 and (usable[0].get('product_code') or '').strip().lower() == host_code:
        return _open_product_home(app_ctx, session)

    # Sesión en otra org (p. ej. last_selected) sin suscripción de este producto:
    # intentar anclar a una org operable que sí lo tenga.
    if host_code and not any(
        (p.get('product_code') or '').strip().lower() == host_code for p in usable
    ):
        if _try_session_org_with_product(host_code, session):
            try:
                usable = PortalService.list_usable_products_for_current_tenant()
            except Exception:
                usable = []
            if any((p.get('product_code') or '').strip().lower() == host_code for p in usable):
                return _open_product_home(app_ctx, session)

    # 0 o N productos, o el único no coincide con este host → Mis Productos
    try:
        return url_for('ets_portal.products')
    except Exception:
        return url_for('ets_portal.home')


def _try_session_org_with_product(product_code: str, session) -> bool:
    """Si el usuario puede usar ``product_code`` en alguna org, fija session a esa org."""
    code = (product_code or '').strip().lower()
    if not code:
        return False
    try:
        from flask_login import current_user

        from nodeone.core.platform.subscription_registry import SubscriptionRegistry
        from nodeone.modules.ets_portal.portal_service import PortalService
        from nodeone.services.post_login_organization import (
            organizations_for_session_after_login,
            save_last_selected_organization,
        )

        if not getattr(current_user, 'is_authenticated', False):
            return False
        for org in organizations_for_session_after_login(current_user):
            oid = int(org.id)
            usable = PortalService.list_usable_products_for_tenant(
                oid, scope_organization_id=oid
            )
            if any((p.get('product_code') or '').strip().lower() == code for p in usable):
                session['organization_id'] = oid
                session.pop('require_org_selection', None)
                save_last_selected_organization(current_user, oid)
                return True
            # Fallback: suscripción entitled aunque falte fila entitlement
            if SubscriptionRegistry.has_product(oid, code, scope_organization_id=oid):
                session['organization_id'] = oid
                session.pop('require_org_selection', None)
                save_last_selected_organization(current_user, oid)
                return True
    except Exception:
        return False
    return False


def _open_product_home(app_ctx, session) -> str:
    from flask import url_for

    hint = (app_ctx.product.home_hint or '').strip()
    app_ids = app_ctx.product.allowed_apps or ()
    if app_ids:
        set_active_app_id(session, app_ids[0])
    if hint and '.' in hint:
        try:
            return url_for(hint)
        except Exception:
            pass
    if app_ids:
        try:
            return url_for(f'{app_ids[0]}.{app_ids[0]}_home')
        except Exception:
            pass
    return url_for('dashboard')
