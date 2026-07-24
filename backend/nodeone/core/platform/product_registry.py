"""ADR-012 — Product Registry: catálogo oficial de productos ETS.

Responde: «¿qué productos existen?» (no «qué tiene contratado este tenant»).

V1: JSON declarativo (``data/product_registry.json``).
V2 (futuro): persistencia en BD + administración desde Portal ETS,
sin cambiar el contrato público de ``ProductRegistry``.

``app_ids`` referencian ``ApplicationDescriptor.id`` del App Registry
(no duplicar metadatos técnicos aquí).
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from nodeone.core.platform.brand_context import BrandContext
from nodeone.core.platform.product_context import (
    PRODUCT_EN1,
    ProductContext,
    SURFACE_PLATFORM,
)

_lock = threading.RLock()
_cached_defs: dict[str, ProductDefinition] | None = None
_cached_path: str | None = None

_DEFAULT_PATH = Path(__file__).resolve().parent / 'data' / 'product_registry.json'

STATUS_ACTIVE = 'active'
STATUS_PLANNED = 'planned'
STATUS_LEGACY = 'legacy'
STATUS_RETIRED = 'retired'


@dataclass(frozen=True)
class ProductDefinition:
    """Definición de un producto ETS (catálogo)."""

    code: str
    name: str
    description: str = ''
    primary_domain: str = ''
    icon: str = ''
    status: str = STATUS_ACTIVE
    version: str = '1.0'
    surface: str = SURFACE_PLATFORM
    brand_preset: str = 'en1'
    tagline: str = ''
    home_hint: str = 'dashboard'
    app_ids: tuple[str, ...] = field(default_factory=tuple)
    list_in_portal: bool = False
    logo_url: str = ''
    favicon_url: str = ''
    licensing: dict[str, Any] = field(default_factory=dict)
    theme: dict[str, str] = field(default_factory=dict)

    def to_product_context(self) -> ProductContext:
        return ProductContext(
            code=self.code,
            surface=self.surface,
            allowed_apps=self.app_ids,
            home_hint=self.home_hint,
        )

    def to_brand_context(self) -> BrandContext:
        theme = self.theme or {}
        return BrandContext(
            display_name=self.name,
            brand_preset=self.brand_preset or 'en1',
            theme_primary=str(theme.get('primary') or '#FF6B35'),
            theme_primary_dark=str(theme.get('primary_dark') or '#2D3E50'),
            theme_accent=str(theme.get('accent') or '#9CA3AF'),
            theme_background=str(theme.get('background') or '#F7F9FC'),
            tagline=self.tagline,
            logo_url=self.logo_url,
            favicon_url=self.favicon_url,
        )

    def resolve_apps(self):
        """Apps técnicas del App Registry referenciadas por este producto."""
        from nodeone.core.platform.app_registry import get_application

        out = []
        for app_id in self.app_ids:
            desc = get_application(app_id)
            if desc is not None:
                out.append(desc)
        return tuple(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'primary_domain': self.primary_domain,
            'icon': self.icon,
            'status': self.status,
            'version': self.version,
            'surface': self.surface,
            'brand_preset': self.brand_preset,
            'tagline': self.tagline,
            'home_hint': self.home_hint,
            'app_ids': list(self.app_ids),
            'list_in_portal': self.list_in_portal,
            'logo_url': self.logo_url,
            'favicon_url': self.favicon_url,
            'licensing': dict(self.licensing),
            'theme': dict(self.theme),
        }


def _registry_path() -> Path:
    override = (os.environ.get('NODEONE_PRODUCT_REGISTRY_CONFIG') or '').strip()
    if override:
        return Path(override)
    return _DEFAULT_PATH


def _parse_entry(code: str, raw: dict[str, Any]) -> ProductDefinition:
    apps = raw.get('app_ids') or raw.get('allowed_apps') or []
    if not isinstance(apps, (list, tuple)):
        apps = []
    theme = raw.get('theme') or {}
    if not isinstance(theme, dict):
        theme = {}
    licensing = raw.get('licensing') or {}
    if not isinstance(licensing, dict):
        licensing = {}
    return ProductDefinition(
        code=str(raw.get('code') or code).strip().lower() or code,
        name=str(raw.get('name') or raw.get('display_name') or code),
        description=str(raw.get('description') or ''),
        primary_domain=str(raw.get('primary_domain') or ''),
        icon=str(raw.get('icon') or ''),
        status=str(raw.get('status') or STATUS_ACTIVE).strip().lower(),
        version=str(raw.get('version') or '1.0'),
        surface=str(raw.get('surface') or SURFACE_PLATFORM),
        brand_preset=str(raw.get('brand_preset') or 'en1'),
        tagline=str(raw.get('tagline') or ''),
        home_hint=str(raw.get('home_hint') or 'dashboard'),
        app_ids=tuple(str(a).strip() for a in apps if str(a).strip()),
        list_in_portal=bool(raw.get('list_in_portal', False)),
        logo_url=str(raw.get('logo_url') or ''),
        favicon_url=str(raw.get('favicon_url') or ''),
        licensing={str(k): v for k, v in licensing.items()},
        theme={str(k): str(v) for k, v in theme.items()},
    )


def _builtin_en1() -> ProductDefinition:
    return ProductDefinition(
        code=PRODUCT_EN1,
        name='Easy NodeOne',
        description='Plataforma tecnológica compartida del ecosistema ETS.',
        primary_domain='appdev.easynodeone.com',
        surface=SURFACE_PLATFORM,
        brand_preset='en1',
        tagline='Plataforma del ecosistema ETS',
        list_in_portal=False,
        theme={
            'primary': '#FF6B35',
            'primary_dark': '#2D3E50',
            'accent': '#9CA3AF',
            'background': '#F7F9FC',
        },
    )


def _load_defs() -> dict[str, ProductDefinition]:
    global _cached_defs, _cached_path
    path = _registry_path()
    key = str(path)
    with _lock:
        if _cached_defs is not None and _cached_path == key:
            return _cached_defs
        defs: dict[str, ProductDefinition] = {}
        try:
            loaded = json.loads(path.read_text(encoding='utf-8'))
            products = (loaded or {}).get('products') if isinstance(loaded, dict) else None
            if isinstance(products, dict):
                for code, raw in products.items():
                    if isinstance(raw, dict):
                        c = str(code).strip().lower()
                        defs[c] = _parse_entry(c, raw)
        except Exception:
            defs = {}
        if not defs:
            defs = {PRODUCT_EN1: _builtin_en1()}
        _cached_defs = defs
        _cached_path = key
        return defs


def reload_product_registry() -> None:
    """Invalida caché del registry (tests / futuro hot-reload)."""
    global _cached_defs, _cached_path
    with _lock:
        _cached_defs = None
        _cached_path = None


class ProductRegistry:
    """Servicio único del catálogo de productos ETS (contrato estable V1→V2)."""

    @classmethod
    def get(cls, code: str | None) -> ProductDefinition | None:
        key = (code or '').strip().lower()
        if not key:
            return None
        return _load_defs().get(key)

    @classmethod
    def get_or_default(cls, code: str | None = None) -> ProductDefinition:
        found = cls.get(code)
        if found is not None:
            return found
        return cls.get(PRODUCT_EN1) or _builtin_en1()

    @classmethod
    def exists(cls, code: str | None) -> bool:
        return cls.get(code) is not None

    @classmethod
    def codes(cls) -> tuple[str, ...]:
        return tuple(sorted(_load_defs().keys()))

    @classmethod
    def list(
        cls,
        *,
        surface: str | None = None,
        status: str | None = None,
        list_in_portal: bool | None = None,
    ) -> Sequence[ProductDefinition]:
        items = list(_load_defs().values())
        if surface is not None:
            s = surface.strip().lower()
            items = [p for p in items if p.surface == s]
        if status is not None:
            st = status.strip().lower()
            items = [p for p in items if p.status == st]
        if list_in_portal is not None:
            items = [p for p in items if p.list_in_portal is list_in_portal]
        items.sort(key=lambda p: (p.surface, p.name.lower()))
        return tuple(items)

    @classmethod
    def list_for_portal(cls) -> Sequence[ProductDefinition]:
        """Catálogo visible en Portal ETS (futuro «Mis productos» / Marketplace).

        No filtra por suscripción de tenant — solo productos publicados en el registry.
        """
        return cls.list(list_in_portal=True, status=STATUS_ACTIVE)

    @classmethod
    def to_contexts(cls, code: str | None) -> tuple[ProductContext, BrandContext]:
        definition = cls.get_or_default(code)
        return definition.to_product_context(), definition.to_brand_context()
