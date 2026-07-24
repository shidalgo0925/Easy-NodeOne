"""ADR-011 — ProductContext: qué producto ETS está activo en la request."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Superficies ADR-011
SURFACE_PLATFORM = 'platform'  # EN1 hub / ops (appprd, appdev)
SURFACE_PORTAL = 'portal'  # Portal ETS comercial
SURFACE_PRODUCT = 'product'  # Producto vertical (EPosOne, …)

PRODUCT_EN1 = 'en1'
PRODUCT_PORTAL = 'portal'
PRODUCT_EPOSONE = 'eposone'
PRODUCT_EPAYROLL = 'epayroll'
PRODUCT_ECLASSONE = 'eclassone'
PRODUCT_ETHESIS = 'ethesis'
PRODUCT_IIUS = 'iius'
PRODUCT_RELATIC = 'relatic'


@dataclass(frozen=True)
class ProductContext:
    """Producto activo (código + superficie + hints de módulos). Sin UI."""

    code: str
    surface: str
    # Apps/módulos sugeridos (filtro blando — fases posteriores)
    allowed_apps: tuple[str, ...] = field(default_factory=tuple)
    home_hint: str = 'dashboard'

    @property
    def product_code(self) -> str:
        """Alias estable para plantillas / callers legacy."""
        return self.code

    def is_platform(self) -> bool:
        return self.surface == SURFACE_PLATFORM

    def is_portal(self) -> bool:
        return self.surface == SURFACE_PORTAL

    def is_product(self) -> bool:
        return self.surface == SURFACE_PRODUCT

    def to_dict(self) -> dict[str, Any]:
        return {
            'product_code': self.code,
            'product_surface': self.surface,
            'product_home_hint': self.home_hint,
            'product_allowed_apps': list(self.allowed_apps),
        }
