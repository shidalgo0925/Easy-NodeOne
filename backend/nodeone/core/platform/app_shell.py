"""Shell por aplicación — layout y navegación aislados (Etapa 4)."""

from __future__ import annotations

from typing import Any

from nodeone.core.platform.launcher import (
    build_nav_context_for_user,
    get_active_app_id,
    launcher_mode_for_organization,
    set_active_app_id,
    visible_launcher_apps,
)

# Zonas que usan shell de aplicación (no módulos Core del sidebar ERP).
PLATFORM_APP_SHELL_AREA_IDS: frozenset[str] = frozenset(
    {
        'eposone',
        'crm',
        'membresias',
        'eventos',
        'certificados',
        'agenda',
        'epayroll',
        'educacion',
        'taller',
        'contador',
        'efactura',
        'comunicacion',
        'analitica',
    }
)


def product_surface_primary_app_id() -> str | None:
    """En Host surface=product, app_id primario del Product Registry (p. ej. eposone)."""
    try:
        from nodeone.core.platform.context_resolver import current_app_context

        ctx = current_app_context()
        if ctx.surface != 'product':
            return None
        apps = ctx.product.allowed_apps or ()
        return apps[0] if apps else (ctx.product_code if ctx.product_code != 'en1' else None)
    except Exception:
        return None


def is_product_surface_shell() -> bool:
    return product_surface_primary_app_id() is not None


def is_app_shell_enabled(organization_id: int | None, session) -> bool:
    """True si el tenant usa launcher apps y hay app activa en sesión.

    Surface product (Host EPosOne): siempre shell del producto, sin depender de
    NODEONE_LAUNCHER_MODE.
    """
    primary = product_surface_primary_app_id()
    if primary:
        if get_active_app_id(session) != primary:
            set_active_app_id(session, primary)
        return True
    if launcher_mode_for_organization(organization_id) != 'apps':
        return False
    return bool(get_active_app_id(session))


def sync_active_app_from_request(session, user) -> str | None:
    """
    Alinea ``platform_active_app_id`` con la zona de navegación del request actual.
    """
    from flask import request

    primary = product_surface_primary_app_id()
    if primary:
        set_active_app_id(session, primary)
        return primary

    if getattr(request, 'blueprint', None) == 'platform_launcher':
        return get_active_app_id(session)

    from app import _org_id_for_module_visibility
    from nodeone.core.template_context_gates import user_can_see_tenant_admin_menu

    if not user_can_see_tenant_admin_menu(user):
        return get_active_app_id(session)

    org_id = _org_id_for_module_visibility()
    if launcher_mode_for_organization(org_id) != 'apps':
        return get_active_app_id(session)

    ctx = build_nav_context_for_user(user)
    from nodeone.core.nav_menu import resolve_active_area_id

    area_id = resolve_active_area_id(ctx)
    if not area_id:
        return get_active_app_id(session)

    visible_ids = {a['id'] for a in visible_launcher_apps(ctx)}
    if area_id in visible_ids:
        set_active_app_id(session, area_id)
        return area_id
    return get_active_app_id(session)


def _apps_return_payload(*, hide: bool = False) -> dict[str, Any]:
    """Retorno al launcher (UX-T1). En surface product se oculta (no hay launcher EN1)."""
    if hide:
        return {
            'platform_apps_return_url': None,
            'platform_apps_return_label': None,
            'platform_shell_show_apps_return': False,
        }
    from flask import url_for

    try:
        return_url = url_for('platform_launcher.apps_home')
    except Exception:
        return_url = '/platform/apps'
    return {
        'platform_apps_return_url': return_url,
        'platform_apps_return_label': '← Mis aplicaciones',
        'platform_shell_show_apps_return': True,
    }


def _app_identity_payload(app_id: str) -> dict[str, Any]:
    """Identidad visual por app (chrome / CSS)."""
    accents = {
        'eposone': {
            'platform_shell_app_accent': 'eposone',
            'platform_shell_app_product_name': 'EPosOne',
            'platform_shell_app_tagline': 'Punto de venta',
        },
    }
    base = {
        'platform_shell_app_accent': app_id or '',
        'platform_shell_app_product_name': None,
        'platform_shell_app_tagline': None,
    }
    base.update(accents.get(app_id, {}))
    return base


def build_app_shell_nav_payload(active_area_id: str, ctx, *, hide_apps_return: bool = False) -> dict[str, Any]:
    """Navegación restringida a una sola app (subnav horizontal + metadatos)."""
    from nodeone.core.nav_menu import (
        _active_child_label,
        _area_by_id,
        active_area_label,
        area_default_url,
        sidebar_highlight_area_id,
        visible_area_children,
    )

    area = _area_by_id(active_area_id)
    sidebar_id = sidebar_highlight_area_id(active_area_id)
    children = visible_area_children(active_area_id, ctx)
    active_child_label = _active_child_label(children)
    label = active_area_label(active_area_id) or active_area_id
    icon = area.icon if area is not None else 'fas fa-th'
    home_url = area_default_url(area, ctx) if area is not None else '#'

    payload = {
        'platform_app_shell_active': True,
        'platform_shell_app_id': active_area_id,
        'platform_shell_app_label': label,
        'platform_shell_app_icon': icon,
        'platform_shell_app_home_url': home_url,
        'nav_app_areas': [],
        'nav_sidebar_top_areas': [],
        'nav_sidebar_groups': [],
        'nav_active_area_id': active_area_id,
        'nav_sidebar_area_id': sidebar_id,
        'nav_active_area_label': label,
        'nav_area_children': children,
        'nav_single_area_mode': True,
        'nav_show_module_bar': bool(children),
        'nav_active_child_label': active_child_label,
    }
    payload.update(_apps_return_payload(hide=hide_apps_return))
    payload.update(_app_identity_payload(active_area_id))
    return payload


def merge_app_shell_nav_context(out: dict[str, Any], user, session) -> dict[str, Any]:
    """Fusiona payload de shell en el contexto admin si aplica."""
    from flask import request

    if getattr(request, 'blueprint', None) == 'platform_launcher' and not is_product_surface_shell():
        out.setdefault('platform_app_shell_active', False)
        return out

    from app import _org_id_for_module_visibility
    from nodeone.core.nav_menu import resolve_active_area_id

    org_id = _org_id_for_module_visibility()
    product_primary = product_surface_primary_app_id()
    hide_return = bool(product_primary)

    if not is_app_shell_enabled(org_id, session):
        out.setdefault('platform_app_shell_active', False)
        return out

    ctx = build_nav_context_for_user(user)
    request_area = resolve_active_area_id(ctx)
    active_id = sync_active_app_from_request(session, user)
    if not active_id:
        out.setdefault('platform_app_shell_active', False)
        return out

    # Surface product: siempre shell del producto (ignora zonas Core EN1).
    if product_primary:
        out.update(
            build_app_shell_nav_payload(product_primary, ctx, hide_apps_return=True)
        )
        out['show_platform_admin_nav'] = False
        return out

    # Módulos Core (Contactos, Ventas, Finanzas…) no usan shell de app.
    if request_area and request_area not in PLATFORM_APP_SHELL_AREA_IDS:
        out.setdefault('platform_app_shell_active', False)
        return out

    from nodeone.core.platform.app_nav import NATIVE_APP_NAV_AREA_IDS, request_in_native_app_zone

    # UX V3.2: no forzar shell EPosOne (u otra app nativa) fuera de sus rutas.
    if active_id in NATIVE_APP_NAV_AREA_IDS and not request_in_native_app_zone(active_id):
        out.setdefault('platform_app_shell_active', False)
        return out
    if (
        request_area
        and request_area != active_id
        and request_area not in NATIVE_APP_NAV_AREA_IDS
        and active_id not in PLATFORM_APP_SHELL_AREA_IDS
    ):
        out.setdefault('platform_app_shell_active', False)
        return out

    shell_area = active_id
    if request_area in NATIVE_APP_NAV_AREA_IDS and request_in_native_app_zone(request_area):
        shell_area = request_area

    out.update(build_app_shell_nav_payload(shell_area, ctx, hide_apps_return=hide_return))
    return out


def merge_native_app_nav_context(out: dict[str, Any], user, session) -> dict[str, Any]:
    """UX V3.2 — nav nativa por app (sidebar único + context bar, sin menú horizontal)."""
    from flask import request

    if getattr(request, 'blueprint', None) == 'platform_launcher' and not is_product_surface_shell():
        out.setdefault('app_nav_native_active', False)
        return out

    from app import _org_id_for_module_visibility
    from nodeone.core.platform.app_nav import (
        build_app_nav_tree,
        native_app_nav_enabled,
        resolve_breadcrumbs,
        serialize_nav_sidebar,
    )

    org_id = _org_id_for_module_visibility()
    product_primary = product_surface_primary_app_id()
    area_id = product_primary or out.get('nav_active_area_id')

    if product_primary:
        # Surface product: forzar nav nativa aunque launcher sea classic
        pass
    elif not native_app_nav_enabled(org_id, area_id):
        out.setdefault('app_nav_native_active', False)
        return out

    ctx = build_nav_context_for_user(user)
    tree = build_app_nav_tree(str(area_id), ctx)
    if tree is None:
        out.setdefault('app_nav_native_active', False)
        return out

    sidebar = serialize_nav_sidebar(tree, ctx)
    breadcrumbs = resolve_breadcrumbs(tree, ctx)
    out.update(
        {
            'app_nav_native_active': True,
            'platform_app_shell_active': True,
            'platform_shell_app_id': tree.nav_area_id,
            'platform_shell_app_label': tree.label,
            'platform_shell_app_icon': tree.icon,
            'platform_shell_app_home_url': tree.home_url,
            'nav_app_areas': [],
            'nav_sidebar_top_areas': [],
            'nav_sidebar_groups': [],
            'nav_area_children': [],
            'nav_show_module_bar': False,
            'nav_use_context_bar': True,
            'app_nav_sidebar': sidebar,
            'app_breadcrumbs': breadcrumbs,
            'nav_active_area_label': tree.label,
            'nav_active_area_id': tree.nav_area_id,
        }
    )
    out.update(_apps_return_payload(hide=bool(product_primary)))
    out.update(_app_identity_payload(tree.nav_area_id))
    if product_primary:
        out['show_platform_admin_nav'] = False
    return out
