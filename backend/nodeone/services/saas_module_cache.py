"""Caché por request de flags SaaS (SaasModule / SaasOrgModule)."""

from __future__ import annotations

from typing import Any


def _enabled_cache() -> dict[tuple[int, str], bool]:
    from flask import g, has_request_context

    if not has_request_context():
        return {}
    cache = getattr(g, '_saas_module_enabled_cache', None)
    if cache is None:
        cache = {}
        g._saas_module_enabled_cache = cache
    return cache


def _catalog_cache() -> dict[str, Any]:
    """code → SaasModule | False (ausente en catálogo)."""
    from flask import g, has_request_context

    if not has_request_context():
        return {}
    cache = getattr(g, '_saas_module_catalog_cache', None)
    if cache is None:
        cache = {}
        g._saas_module_catalog_cache = cache
    return cache


def get_catalog_module(module_code: str):
    import app as M

    code = (module_code or '').strip()
    if not code:
        return None
    cache = _catalog_cache()
    if code in cache:
        row = cache[code]
        return row if row is not False else None
    mod = M.SaasModule.query.filter_by(code=code).first()
    cache[code] = mod if mod is not None else False
    return mod


def has_saas_module_enabled_cached(organization_id, module_code) -> bool:
    import app as M

    if not module_code:
        return True
    if not M._enable_multi_tenant_catalog():
        return True
    if organization_id is None:
        return False
    try:
        oid = int(organization_id)
    except (TypeError, ValueError):
        return False

    key = (oid, str(module_code).strip())
    cache = _enabled_cache()
    if key in cache:
        return cache[key]

    mod = get_catalog_module(key[1])
    if mod is None:
        result = False
    else:
        link = M.SaasOrgModule.query.filter_by(organization_id=oid, module_id=mod.id).first()
        if link is not None:
            result = bool(link.enabled)
        else:
            result = bool(mod.is_core)
    cache[key] = result
    return result


def saas_cache_stats() -> dict[str, int]:
    from flask import g, has_request_context

    if not has_request_context():
        return {'enabled_keys': 0, 'catalog_keys': 0, 'preloaded_oid': None}
    return {
        'enabled_keys': len(getattr(g, '_saas_module_enabled_cache', {}) or {}),
        'catalog_keys': len(getattr(g, '_saas_module_catalog_cache', {}) or {}),
        'preloaded_oid': getattr(g, '_saas_modules_preloaded_oid', None),
    }


def preload_saas_modules_for_org(organization_id) -> None:
    """Precarga catálogo + flags enabled para la org (2 queries vs 2×N)."""
    import app as M

    if not M._enable_multi_tenant_catalog():
        return
    try:
        oid = int(organization_id)
    except (TypeError, ValueError):
        return

    from flask import g, has_request_context

    if has_request_context() and getattr(g, '_saas_modules_preloaded_oid', None) == oid:
        return

    enabled_cache = _enabled_cache()
    catalog_cache = _catalog_cache()

    modules = M.SaasModule.query.order_by(M.SaasModule.id.asc()).all()
    links = {
        int(link.module_id): link
        for link in M.SaasOrgModule.query.filter_by(organization_id=oid).all()
    }
    for mod in modules:
        code = (mod.code or '').strip()
        if not code:
            continue
        catalog_cache[code] = mod
        link = links.get(int(mod.id))
        if link is not None:
            enabled_cache[(oid, code)] = bool(link.enabled)
        else:
            enabled_cache[(oid, code)] = bool(mod.is_core)

    if has_request_context():
        g._saas_modules_preloaded_oid = oid
