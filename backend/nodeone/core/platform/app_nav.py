"""Contrato de navegación por aplicación — UX V3.2."""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from typing import Any, Callable

from flask import has_request_context, request
from werkzeug.routing import BuildError

from nodeone.core.nav_menu import NavContext

NATIVE_APP_NAV_AREA_IDS: frozenset[str] = frozenset({'eposone'})

NATIVE_APP_NAV_BUILDERS: dict[str, str] = {
    'eposone': 'nodeone.modules.eposone.nav.build_nav_tree',
}


@dataclass(frozen=True)
class AppNavItem:
    id: str
    label: str
    icon: str
    url: str | None = None
    children: tuple[AppNavItem, ...] = ()
    visible: Callable[[NavContext], bool] | None = None
    active_endpoints: tuple[str, ...] = ()
    active_blueprints: tuple[str, ...] = ()
    active_path_prefixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class AppNavTree:
    app_id: str
    nav_area_id: str
    label: str
    icon: str
    home_url: str
    domains: tuple[AppNavItem, ...]


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


def request_in_native_app_zone(nav_area_id: str) -> bool:
    """True si el request HTTP pertenece al shell de la app (no módulos Core compuestos)."""
    if not has_request_context():
        return False
    bp = getattr(request, 'blueprint', None) or ''
    path = request.path or ''
    if nav_area_id == 'eposone':
        return bp == 'eposone' or path.startswith('/admin/eposone')
    return False


def native_app_nav_enabled(organization_id: int | None, nav_area_id: str | None) -> bool:
    """True si la zona activa usa navegación nativa de app (UX V3.2)."""
    if not nav_area_id or nav_area_id not in NATIVE_APP_NAV_AREA_IDS:
        return False
    if not request_in_native_app_zone(nav_area_id):
        return False
    oid = None
    if organization_id is not None:
        try:
            oid = int(organization_id)
        except (TypeError, ValueError):
            oid = None
    classic = _parse_org_id_list('NODEONE_LAUNCHER_CLASSIC_ORG_IDS') or set()
    if oid is not None and oid in classic:
        return False
    from nodeone.core.platform.launcher import launcher_mode_for_organization

    if launcher_mode_for_organization(oid) == 'apps':
        return True
    if os.environ.get('NODEONE_EPOSONE_NATIVE_NAV', '').strip() == '1':
        return True
    if nav_area_id == 'eposone' and oid is not None:
        try:
            from nodeone.services.saas_module_cache import has_saas_module_enabled_cached

            if has_saas_module_enabled_cached(oid, 'eposone'):
                return True
        except Exception:
            pass
    seed = _parse_org_id_list('NODEONE_PLATFORM_SEED_EPOSONE_ORG_IDS')
    if nav_area_id == 'eposone' and oid is not None and seed and oid in seed:
        return True
    return False


def build_app_nav_tree(nav_area_id: str, ctx: NavContext) -> AppNavTree | None:
    provider = NATIVE_APP_NAV_BUILDERS.get(str(nav_area_id or '').strip())
    if not provider:
        return None
    module_path, _, func_name = provider.rpartition('.')
    if not module_path:
        return None
    mod = importlib.import_module(module_path)
    builder = getattr(mod, func_name, None)
    if builder is None:
        return None
    tree = builder(ctx)
    return tree if isinstance(tree, AppNavTree) else None


def _item_visible(item: AppNavItem, ctx: NavContext) -> bool:
    if item.visible is not None and not item.visible(ctx):
        return False
    if item.children:
        return any(_item_visible(child, ctx) for child in item.children)
    return bool(item.url)


def _endpoint_active(item: AppNavItem) -> bool:
    if not has_request_context():
        return False
    ep = getattr(request, 'endpoint', None) or ''
    bp = getattr(request, 'blueprint', None) or ''
    path = request.path or ''
    if item.active_endpoints and ep in item.active_endpoints:
        return True
    if item.active_blueprints and bp in item.active_blueprints:
        return True
    for prefix in item.active_path_prefixes:
        if prefix and path.startswith(prefix):
            return True
    for child in item.children:
        if _endpoint_active(child):
            return True
    return False


def _serialize_item(item: AppNavItem, ctx: NavContext) -> dict[str, Any] | None:
    if not _item_visible(item, ctx):
        return None
    children: list[dict[str, Any]] = []
    for child in item.children:
        row = _serialize_item(child, ctx)
        if row is not None:
            children.append(row)
    if item.children and not children:
        return None
    active = _endpoint_active(item)
    if children:
        active = active or any(c.get('active') for c in children)
    row: dict[str, Any] = {
        'id': item.id,
        'label': item.label,
        'icon': item.icon,
        'url': item.url,
        'active': active and not children,
        'children': children,
        'is_group': bool(children),
        'group_active': active,
    }
    return row


def serialize_nav_sidebar(tree: AppNavTree, ctx: NavContext) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for domain in tree.domains:
        row = _serialize_item(domain, ctx)
        if row is not None:
            rows.append(row)
    return rows


def _flatten_visible_items(
    items: tuple[AppNavItem, ...],
    ctx: NavContext,
    *,
    ancestors: list[AppNavItem] | None = None,
) -> list[tuple[list[AppNavItem], AppNavItem]]:
    chain: list[tuple[list[AppNavItem], AppNavItem]] = []
    parent_chain = ancestors or []
    for item in items:
        if not _item_visible(item, ctx):
            continue
        current_chain = [*parent_chain, item]
        if _endpoint_active(item) and item.url:
            chain.append((parent_chain, item))
        if item.children:
            chain.extend(_flatten_visible_items(item.children, ctx, ancestors=current_chain))
    return chain


def resolve_breadcrumbs(tree: AppNavTree, ctx: NavContext) -> list[dict[str, str]]:
    crumbs: list[dict[str, str]] = [{'label': tree.label, 'url': tree.home_url}]
    matches = _flatten_visible_items(tree.domains, ctx)
    active_match: tuple[list[AppNavItem], AppNavItem] | None = None
    best_depth = -1
    for ancestors, leaf in matches:
        depth = len(ancestors) + 1
        if _endpoint_active(leaf) and depth >= best_depth:
            active_match = (ancestors, leaf)
            best_depth = depth
    if active_match is None:
        return crumbs
    ancestors, leaf = active_match
    for node in ancestors:
        if node.url:
            crumbs.append({'label': node.label, 'url': node.url})
        else:
            crumbs.append({'label': node.label, 'url': ''})
    crumbs.append({'label': leaf.label, 'url': leaf.url or ''})
    return crumbs


def safe_url_for(endpoint: str, **kwargs: Any) -> str:
    from flask import url_for

    try:
        return url_for(endpoint, **kwargs)
    except BuildError:
        return '#'
