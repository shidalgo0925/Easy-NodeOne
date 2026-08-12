"""Plantillas de plan → entitlement (ADR-016).

Fuente de verdad comercial: ``commercial_plans``.
Este módulo solo adapta al shape que consume EntitlementService.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from nodeone.core.platform.commercial_plans import (
    entitlement_template_from_commercial,
    list_commercial_plan_codes,
    normalize_commercial_plan_code,
)
from nodeone.core.platform.esecurebroker_commercial_plans import (
    esb_entitlement_template,
    list_esb_plan_codes,
    normalize_esb_plan_code,
)

# Fallback genérico para otros productos ETS
_DEFAULT_PLAN: dict[str, Any] = {
    'resource_limits': {},
    'features': {},
}


def normalize_plan_code(plan_code: str | None) -> str:
    return normalize_commercial_plan_code(plan_code)


def list_plan_codes(product_code: str) -> list[str]:
    product = (product_code or '').strip().lower()
    if product == 'eposone':
        return list_commercial_plan_codes()
    if product == 'esecurebroker':
        return list_esb_plan_codes()
    return ['starter']


def get_plan_template(product_code: str, plan_code: str | None) -> dict[str, Any]:
    """Devuelve ``{resource_limits, features}`` del plan (copia profunda)."""
    product = (product_code or '').strip().lower()
    if product == 'eposone':
        return entitlement_template_from_commercial(plan_code)
    if product == 'esecurebroker':
        # Si llega código legado/ inválido, template vacío (no inventar EPosOne).
        if plan_code and normalize_esb_plan_code(plan_code) is None:
            return deepcopy(_DEFAULT_PLAN)
        return esb_entitlement_template(plan_code)
    return deepcopy(_DEFAULT_PLAN)


def merge_limits_with_overrides(
    plan_limits: dict[str, Any],
    overrides: dict[str, Any] | None,
) -> dict[str, Any]:
    """Límites efectivos = defaults del plan + overrides comerciales."""
    effective = dict(plan_limits or {})
    if overrides:
        for key, value in overrides.items():
            effective[key] = value
    return effective
