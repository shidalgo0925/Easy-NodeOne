"""EP1 — permisos efectivos para navegación (identidad × rol × licencia).

La licencia (EntitlementService) es la autoridad funcional del producto;
el rol/RBAC decide quién puede usar lo habilitado. El host no decide el menú.
"""

from __future__ import annotations

from typing import Any


def is_system_administrator(user: Any) -> bool:
    """SA ETS — administrador de plataforma EN1 (User.is_admin)."""
    return bool(getattr(user, 'is_admin', False))


def current_nav_organization_id() -> int | None:
    try:
        from app import _org_id_for_module_visibility

        oid = _org_id_for_module_visibility()
        return int(oid) if oid is not None else None
    except Exception:
        return None


def product_entitlement_operable(organization_id: int | None, product_code: str) -> bool:
    if organization_id is None:
        return False
    code = (product_code or '').strip().lower()
    if not code:
        return False
    try:
        from nodeone.core.platform.entitlement_service import EntitlementService

        rec = EntitlementService.get_for_tenant_product(
            int(organization_id),
            code,
            scope_organization_id=int(organization_id),
        )
        if rec is not None:
            return bool(rec.is_operable)
        # Sin fila entitlement: degradar a suscripción activa (compat).
        from nodeone.core.platform.subscription_registry import SubscriptionRegistry

        return bool(
            SubscriptionRegistry.has_product(
                int(organization_id),
                code,
                scope_organization_id=int(organization_id),
            )
        )
    except Exception:
        return False


def product_has_feature(
    organization_id: int | None,
    product_code: str,
    feature: str,
    *,
    default_if_no_entitlement: bool = True,
) -> bool:
    """Feature del plan/entitlement. Si no hay entitlement, ``default_if_no_entitlement``."""
    if organization_id is None:
        return False
    code = (product_code or '').strip().lower()
    feat = (feature or '').strip().lower()
    if not code or not feat:
        return False
    try:
        from nodeone.core.platform.entitlement_service import EntitlementService

        rec = EntitlementService.get_for_tenant_product(
            int(organization_id),
            code,
            scope_organization_id=int(organization_id),
        )
        if rec is None:
            return bool(default_if_no_entitlement)
        if not rec.is_operable:
            return False
        return bool(
            EntitlementService.has_feature(
                int(organization_id),
                code,
                feat,
                scope_organization_id=int(organization_id),
            )
        )
    except Exception:
        return bool(default_if_no_entitlement)


def eposone_feature(feature: str, *, default_if_no_entitlement: bool = True) -> bool:
    return product_has_feature(
        current_nav_organization_id(),
        'eposone',
        feature,
        default_if_no_entitlement=default_if_no_entitlement,
    )
