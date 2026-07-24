"""ADR-011 — BrandContext: identidad visual resuelta (aún sin aplicar UI completa).

API pública de conveniencia (re-exporta el resolver único).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nodeone.core.platform.product_context import (
    PRODUCT_ECLASSONE,
    PRODUCT_EN1,
    PRODUCT_EPAYROLL,
    PRODUCT_EPOSONE,
    PRODUCT_ETHESIS,
    PRODUCT_IIUS,
    PRODUCT_PORTAL,
    PRODUCT_RELATIC,
    SURFACE_PLATFORM,
    SURFACE_PORTAL,
    SURFACE_PRODUCT,
)


@dataclass(frozen=True)
class BrandContext:
    """Identidad visual del producto (logo/colores/textos). Fase infra: solo resolución."""

    display_name: str
    brand_preset: str
    theme_primary: str
    theme_primary_dark: str
    theme_accent: str
    theme_background: str
    tagline: str = ''
    logo_url: str = ''
    favicon_url: str = ''

    def theme_overlay(self) -> dict[str, str]:
        """Tokens listos para fases posteriores de tema (no aplicar aún de forma agresiva)."""
        return {
            'theme_primary': self.theme_primary,
            'theme_primary_dark': self.theme_primary_dark,
            'theme_accent': self.theme_accent,
            'theme_accent_gold': self.theme_accent,
            'theme_accent_cyan': self.theme_accent,
            'theme_background_cream': self.theme_background,
            'brand_preset': self.brand_preset,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            'product_display_name': self.display_name,
            'brand_preset': self.brand_preset,
            'product_tagline': self.tagline,
            'brand_logo_url': self.logo_url,
            'brand_favicon_url': self.favicon_url,
        }


# --- Compat helpers (delegación al ContextResolver único) ---


def resolve_product_code(hostname: str | None = None) -> str:
    from nodeone.core.platform.context_resolver import ContextResolver

    return ContextResolver.resolve_product_code(hostname)


def resolve_brand_context(hostname: str | None = None) -> BrandContext:
    from nodeone.core.platform.context_resolver import ContextResolver

    return ContextResolver.resolve(hostname).brand


def brand_context_for_request() -> BrandContext:
    from nodeone.core.platform.context_resolver import current_brand_context

    return current_brand_context()


def resolve_product_context(hostname: str | None = None):
    from nodeone.core.platform.context_resolver import ContextResolver

    return ContextResolver.resolve(hostname).product


def product_context_for_request():
    from nodeone.core.platform.context_resolver import current_product_context

    return current_product_context()


__all__ = [
    'BrandContext',
    'PRODUCT_ECLASSONE',
    'PRODUCT_EN1',
    'PRODUCT_EPAYROLL',
    'PRODUCT_EPOSONE',
    'PRODUCT_ETHESIS',
    'PRODUCT_IIUS',
    'PRODUCT_PORTAL',
    'PRODUCT_RELATIC',
    'SURFACE_PLATFORM',
    'SURFACE_PORTAL',
    'SURFACE_PRODUCT',
    'brand_context_for_request',
    'product_context_for_request',
    'resolve_brand_context',
    'resolve_product_code',
    'resolve_product_context',
]
