"""ADR-011/012 — ContextResolver único: Host → product_code → ProductRegistry.

Capas:
  Host map          → ¿qué product_code corresponde a este dominio?
  ProductRegistry   → ¿qué es ese producto? (Brand + Product + app_ids)
  App Registry      → capacidades técnicas (vía ProductDefinition.resolve_apps)

No dispersar ``if host == ...`` por el código.
Host map: ``data/host_product_map.json`` (override: ``NODEONE_HOST_PRODUCT_MAP``
o legado ``NODEONE_PRODUCT_CONTEXT_CONFIG``).
"""

from __future__ import annotations

import json
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nodeone.core.platform.brand_context import BrandContext
from nodeone.core.platform.product_context import PRODUCT_EN1, ProductContext
from nodeone.core.platform.product_registry import ProductRegistry, reload_product_registry

_G_KEY = '_en1_resolved_app_context'
_lock = threading.RLock()
_cached_host_map: dict[str, Any] | None = None
_cached_host_map_path: str | None = None

_DEFAULT_HOST_MAP_PATH = Path(__file__).resolve().parent / 'data' / 'host_product_map.json'


@dataclass(frozen=True)
class ResolvedAppContext:
    """Resultado del resolver: producto + marca + host que los originó."""

    hostname: str
    product: ProductContext
    brand: BrandContext

    @property
    def product_code(self) -> str:
        return self.product.code

    @property
    def surface(self) -> str:
        return self.product.surface

    @property
    def display_name(self) -> str:
        return self.brand.display_name

    @property
    def brand_preset(self) -> str:
        return self.brand.brand_preset

    def to_template_dict(self) -> dict[str, Any]:
        """Variables de plantilla / context processor (infra; sin forzar UI)."""
        out = {}
        out.update(self.product.to_dict())
        out.update(self.brand.to_dict())
        return out

    def theme_overlay(self) -> dict[str, str]:
        return self.brand.theme_overlay()


def _normalize_host(raw: str | None) -> str:
    h = (raw or '').split(',')[0].strip().lower()
    if ':' in h and not h.startswith('['):
        h = h.split(':', 1)[0]
    return h


def request_hostname() -> str:
    """Host efectivo (respeta X-Forwarded-Host detrás de nginx)."""
    try:
        from flask import has_request_context, request

        if not has_request_context():
            return ''
        xf = (request.headers.get('X-Forwarded-Host') or '').strip()
        if xf:
            return _normalize_host(xf)
        return _normalize_host(request.host)
    except Exception:
        return ''


def _host_map_path() -> Path:
    override = (
        (os.environ.get('NODEONE_HOST_PRODUCT_MAP') or '').strip()
        or (os.environ.get('NODEONE_PRODUCT_CONTEXT_CONFIG') or '').strip()
    )
    if override:
        return Path(override)
    return _DEFAULT_HOST_MAP_PATH


def _builtin_host_map() -> dict[str, Any]:
    return {
        'default_product': PRODUCT_EN1,
        'hosts': {
            'appdev.easynodeone.com': PRODUCT_EN1,
            'appprd.easynodeone.com': PRODUCT_EN1,
            'app.easytech.services': 'portal',
            'portal.easytech.services': 'portal',
            'eposone.easytech.services': 'eposone',
        },
        'host_prefixes': {
            'portal': 'portal',
            'eposone': 'eposone',
            'epayroll': 'epayroll',
            'eclassone': 'eclassone',
            'etesis': 'ethesis',
        },
    }


def _load_host_map() -> dict[str, Any]:
    global _cached_host_map, _cached_host_map_path
    path = _host_map_path()
    key = str(path)
    with _lock:
        if _cached_host_map is not None and _cached_host_map_path == key:
            return _cached_host_map
        data: dict[str, Any] = {}
        try:
            loaded = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(loaded, dict):
                data = loaded
        except Exception:
            data = {}
        if not data.get('hosts') and not data.get('default_product'):
            data = _builtin_host_map()
        _cached_host_map = data
        _cached_host_map_path = key
        return data


def reload_config() -> None:
    """Invalida caché de host map + Product Registry (tests)."""
    global _cached_host_map, _cached_host_map_path
    with _lock:
        _cached_host_map = None
        _cached_host_map_path = None
    reload_product_registry()


def _product_from_force_env() -> str | None:
    forced = (os.environ.get('NODEONE_PRODUCT_FORCE') or '').strip().lower()
    if forced and ProductRegistry.exists(forced):
        return forced
    return None


def _product_from_dev_header() -> str | None:
    """Solo Dev/Staging: header ``X-EN1-Product: eposone``."""
    allow = (os.environ.get('NODEONE_ALLOW_PRODUCT_HEADER') or '').strip().lower() in (
        '1',
        'true',
        'yes',
        'on',
    )
    flask_env = (os.environ.get('FLASK_ENV') or '').strip().lower()
    if not allow and flask_env not in ('development', 'dev', 'staging'):
        return None
    try:
        from flask import has_request_context, request

        if not has_request_context():
            return None
        raw = (request.headers.get('X-EN1-Product') or '').strip().lower()
        if ProductRegistry.exists(raw):
            return raw
    except Exception:
        pass
    return None


_HOST_PREFIX_RE = re.compile(
    r'^(?P<pre>portal|eposone|epayroll|eclassone|etesis)(?P<sfx>|-stg|-dev|-test)?\.',
    re.I,
)


class ContextResolver:
    """Resolver único Host → ProductContext + BrandContext (vía ProductRegistry)."""

    @classmethod
    def resolve_product_code(cls, hostname: str | None = None) -> str:
        forced = _product_from_force_env()
        if forced:
            return forced
        header = _product_from_dev_header()
        if header:
            return header

        cfg = _load_host_map()
        default = str(cfg.get('default_product') or PRODUCT_EN1)
        host = _normalize_host(hostname if hostname is not None else request_hostname())
        if not host:
            return default

        hosts = cfg.get('hosts') or {}
        if host in hosts:
            code = str(hosts[host]).strip().lower()
            return code if ProductRegistry.exists(code) else default

        prefixes = cfg.get('host_prefixes') or {}
        m = _HOST_PREFIX_RE.match(host)
        if m:
            pre = m.group('pre').lower()
            if pre in prefixes:
                code = str(prefixes[pre]).strip().lower()
                return code if ProductRegistry.exists(code) else default

        if host.endswith('.easynodeone.com'):
            return default

        return default

    @classmethod
    def resolve(cls, hostname: str | None = None) -> ResolvedAppContext:
        host = _normalize_host(hostname if hostname is not None else request_hostname())
        code = cls.resolve_product_code(hostname)
        product, brand = ProductRegistry.to_contexts(code)
        return ResolvedAppContext(hostname=host, product=product, brand=brand)

    @classmethod
    def resolve_product(cls, hostname: str | None = None) -> ProductContext:
        return cls.resolve(hostname).product

    @classmethod
    def resolve_brand(cls, hostname: str | None = None) -> BrandContext:
        return cls.resolve(hostname).brand


def current_app_context() -> ResolvedAppContext:
    """Contexto de la request actual (cache en ``flask.g``)."""
    try:
        from flask import g, has_request_context

        if has_request_context():
            cached = getattr(g, _G_KEY, None)
            if isinstance(cached, ResolvedAppContext):
                return cached
            resolved = ContextResolver.resolve()
            setattr(g, _G_KEY, resolved)
            return resolved
    except Exception:
        pass
    return ContextResolver.resolve()


def current_product_context() -> ProductContext:
    return current_app_context().product


def current_brand_context() -> BrandContext:
    return current_app_context().brand


# Alias cortos para imports desde cualquier módulo
resolve_context = ContextResolver.resolve
resolve_product_context = ContextResolver.resolve_product
resolve_brand_context = ContextResolver.resolve_brand
resolve_product_code = ContextResolver.resolve_product_code
