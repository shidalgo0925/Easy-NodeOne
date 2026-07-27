"""Portal ETS MVP — listado de productos del tenant (sin acceso directo a modelos).

Usa solo SubscriptionRegistry + ProductRegistry.
"""

from __future__ import annotations

from typing import Any

from nodeone.core.platform.product_registry import ProductRegistry
from nodeone.core.platform.subscription_registry import SubscriptionRegistry

# Visible en «Mis Productos» (MVP)
_PORTAL_VISIBLE_STATUSES = frozenset({'trial', 'active', 'past_due', 'suspended'})
# ADR-017 Hito 4 — productos que se pueden abrir tras login
_USABLE_SUB_STATUSES = frozenset({'trial', 'active', 'past_due'})


class PortalService:
    """API interna del Portal ETS (contrato estable para la UI)."""

    @staticmethod
    def _current_organization_id() -> int | None:
        try:
            from utils.organization import resolve_current_organization

            oid = resolve_current_organization()
            return int(oid) if oid is not None else None
        except Exception:
            return None

    @classmethod
    def list_products_for_current_tenant(cls) -> list[dict[str, Any]]:
        """Productos contratados del tenant de sesión (aislados)."""
        oid = cls._current_organization_id()
        if oid is None:
            return []
        return cls.list_products_for_tenant(oid, scope_organization_id=oid)

    @classmethod
    def list_usable_products_for_tenant(
        cls,
        organization_id: int,
        *,
        scope_organization_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Productos operables para el lanzador inteligente (ADR-017 Hito 4)."""
        items = cls.list_products_for_tenant(
            int(organization_id),
            scope_organization_id=scope_organization_id,
        )
        out: list[dict[str, Any]] = []
        for item in items:
            status = (item.get('subscription_status') or '').strip().lower()
            if status not in _USABLE_SUB_STATUSES:
                continue
            if not item.get('is_entitled'):
                continue
            code = (item.get('product_code') or '').strip().lower()
            definition = ProductRegistry.get(code)
            if definition is None:
                continue
            if definition.surface != 'product' or not definition.list_in_portal:
                continue
            if not cls._entitlement_operable(int(organization_id), code):
                continue
            out.append(item)
        return out

    @classmethod
    def list_usable_products_for_current_tenant(cls) -> list[dict[str, Any]]:
        oid = cls._current_organization_id()
        if oid is None:
            return []
        return cls.list_usable_products_for_tenant(oid, scope_organization_id=oid)

    @staticmethod
    def _entitlement_operable(organization_id: int, product_code: str) -> bool:
        """Si hay entitlement, debe ser operable; si no hay fila, basta la suscripción."""
        try:
            from nodeone.core.platform.entitlement_service import EntitlementService

            ent = EntitlementService.get_for_tenant_product(int(organization_id), product_code)
            if ent is None:
                return True
            return bool(ent.is_operable)
        except Exception:
            return True

    @classmethod
    def list_products_for_tenant(
        cls,
        organization_id: int,
        *,
        scope_organization_id: int | None = None,
    ) -> list[dict[str, Any]]:
        raw = SubscriptionRegistry.list_tenant_products(
            int(organization_id),
            scope_organization_id=scope_organization_id,
            entitled_only=False,
        )
        out: list[dict[str, Any]] = []
        for item in raw:
            status = (item.get('subscription_status') or '').strip().lower()
            if status not in _PORTAL_VISIBLE_STATUSES:
                continue
            code = item.get('product_code') or ''
            definition = ProductRegistry.get(code)
            if definition is None:
                continue
            domain = (definition.primary_domain or '').strip()
            open_url = f'https://{domain}' if domain else ''
            product = item.get('product') or {}
            out.append(
                {
                    'product_code': code,
                    'subscription_status': status,
                    'is_entitled': bool(item.get('is_entitled')),
                    'starts_at': item.get('starts_at'),
                    'ends_at': item.get('ends_at'),
                    'trial_ends_at': item.get('trial_ends_at'),
                    'name': product.get('name') or definition.name,
                    'description': definition.description or definition.tagline or '',
                    'icon': product.get('icon') or definition.icon or '',
                    'primary_domain': domain,
                    'open_url': open_url,
                    'surface': definition.surface,
                    'home_hint': definition.home_hint,
                    'app_ids': list(definition.app_ids or ()),
                }
            )
        out.sort(key=lambda p: (p.get('name') or '').lower())
        return out

    @classmethod
    def open_url_for_product(cls, product_code: str) -> str | None:
        """URL de apertura vía ProductRegistry.primary_domain (sin hardcode)."""
        definition = ProductRegistry.get(product_code)
        if definition is None:
            return None
        domain = (definition.primary_domain or '').strip()
        if not domain:
            return None
        return f'https://{domain}'
