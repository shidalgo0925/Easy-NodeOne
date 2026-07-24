"""ADR-011 — ContextResolver único: Host → ProductContext + BrandContext.

Único punto de resolución. No dispersar `if host == ...` por el código.
Config: ``data/host_product_map.json`` (override: ``NODEONE_PRODUCT_CONTEXT_CONFIG``).
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
from nodeone.core.platform.product_context import (
    PRODUCT_EN1,
    ProductContext,
    SURFACE_PLATFORM,
)

_G_KEY = '_en1_resolved_app_context'
_lock = threading.RLock()
_cached_config: dict[str, Any] | None = None
_cached_config_path: str | None = None

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / 'data' / 'host_product_map.json'


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


def _config_path() -> Path:
    override = (os.environ.get('NODEONE_PRODUCT_CONTEXT_CONFIG') or '').strip()
    if override:
        return Path(override)
    return _DEFAULT_CONFIG_PATH


def _load_config() -> dict[str, Any]:
    global _cached_config, _cached_config_path
    path = _config_path()
    key = str(path)
    with _lock:
        if _cached_config is not None and _cached_config_path == key:
            return _cached_config
        data: dict[str, Any] = {}
        try:
            raw = path.read_text(encoding='utf-8')
            loaded = json.loads(raw)
            if isinstance(loaded, dict):
                data = loaded
        except Exception:
            data = {}
        if not data.get('products'):
            data = _builtin_fallback_config()
        _cached_config = data
        _cached_config_path = key
        return data


def reload_config() -> None:
    """Invalida caché (tests / hot-reload admin futuro)."""
    global _cached_config, _cached_config_path
    with _lock:
        _cached_config = None
        _cached_config_path = None


def _builtin_fallback_config() -> dict[str, Any]:
    """Si falta el JSON, EN1 por defecto."""
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
        'products': {
            PRODUCT_EN1: {
                'surface': SURFACE_PLATFORM,
                'display_name': 'Easy NodeOne',
                'brand_preset': 'en1',
                'tagline': 'Plataforma del ecosistema ETS',
                'home_hint': 'dashboard',
                'allowed_apps': [],
                'theme': {
                    'primary': '#FF6B35',
                    'primary_dark': '#2D3E50',
                    'accent': '#9CA3AF',
                    'background': '#F7F9FC',
                },
            },
            'eposone': {
                'surface': 'product',
                'display_name': 'EPosOne',
                'brand_preset': 'eposone',
                'tagline': 'Punto de venta',
                'home_hint': 'eposone.eposone_home',
                'allowed_apps': ['eposone'],
                'theme': {
                    'primary': '#FF6B35',
                    'primary_dark': '#C2410C',
                    'accent': '#FDBA74',
                    'background': '#FFF7ED',
                },
            },
            'portal': {
                'surface': 'portal',
                'display_name': 'Easy Technology Services',
                'brand_preset': 'portal',
                'tagline': 'Portal del ecosistema ETS',
                'home_hint': 'portal_home',
                'allowed_apps': ['portal', 'billing', 'licenses'],
                'theme': {
                    'primary': '#0F766E',
                    'primary_dark': '#134E4A',
                    'accent': '#14B8A6',
                    'background': '#F0FDFA',
                },
            },
        },
    }


def _product_entry(code: str) -> dict[str, Any]:
    cfg = _load_config()
    products = cfg.get('products') or {}
    entry = products.get(code) or products.get(cfg.get('default_product') or PRODUCT_EN1)
    if not isinstance(entry, dict):
        entry = _builtin_fallback_config()['products'][PRODUCT_EN1]
    return entry


def _contexts_for_code(code: str) -> tuple[ProductContext, BrandContext]:
    entry = _product_entry(code)
    theme = entry.get('theme') or {}
    apps = entry.get('allowed_apps') or []
    if not isinstance(apps, (list, tuple)):
        apps = []
    product = ProductContext(
        code=code,
        surface=str(entry.get('surface') or SURFACE_PLATFORM),
        allowed_apps=tuple(str(a) for a in apps),
        home_hint=str(entry.get('home_hint') or 'dashboard'),
    )
    brand = BrandContext(
        display_name=str(entry.get('display_name') or code),
        brand_preset=str(entry.get('brand_preset') or 'en1'),
        theme_primary=str(theme.get('primary') or '#FF6B35'),
        theme_primary_dark=str(theme.get('primary_dark') or '#2D3E50'),
        theme_accent=str(theme.get('accent') or '#9CA3AF'),
        theme_background=str(theme.get('background') or '#F7F9FC'),
        tagline=str(entry.get('tagline') or ''),
        logo_url=str(entry.get('logo_url') or ''),
        favicon_url=str(entry.get('favicon_url') or ''),
    )
    return product, brand


def _product_from_force_env() -> str | None:
    forced = (os.environ.get('NODEONE_PRODUCT_FORCE') or '').strip().lower()
    if not forced:
        return None
    cfg = _load_config()
    if forced in (cfg.get('products') or {}):
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
        cfg = _load_config()
        if raw in (cfg.get('products') or {}):
            return raw
    except Exception:
        pass
    return None


_HOST_PREFIX_RE = re.compile(
    r'^(?P<pre>portal|eposone|epayroll|eclassone|etesis)(?P<sfx>|-stg|-dev|-test)?\.',
    re.I,
)


class ContextResolver:
    """Resolver único Host → ProductContext + BrandContext."""

    @classmethod
    def resolve_product_code(cls, hostname: str | None = None) -> str:
        forced = _product_from_force_env()
        if forced:
            return forced
        header = _product_from_dev_header()
        if header:
            return header

        cfg = _load_config()
        default = str(cfg.get('default_product') or PRODUCT_EN1)
        host = _normalize_host(hostname if hostname is not None else request_hostname())
        if not host:
            return default

        hosts = cfg.get('hosts') or {}
        if host in hosts:
            return str(hosts[host])

        prefixes = cfg.get('host_prefixes') or {}
        m = _HOST_PREFIX_RE.match(host)
        if m:
            pre = m.group('pre').lower()
            if pre in prefixes:
                return str(prefixes[pre])

        if host.endswith('.easynodeone.com'):
            return default

        return default

    @classmethod
    def resolve(cls, hostname: str | None = None) -> ResolvedAppContext:
        host = _normalize_host(hostname if hostname is not None else request_hostname())
        code = cls.resolve_product_code(hostname)
        product, brand = _contexts_for_code(code)
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
