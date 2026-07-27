"""Plantillas de plan → entitlement (ADR-016). Configuración, no lógica de app.

Cupo ``-1`` = ilimitado.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

# Vocabulario EPosOne (extensible por producto)
_EPOSONE_PLANS: dict[str, dict[str, Any]] = {
    'starter': {
        'resource_limits': {
            'pos': 1,
            'registers': 1,
            'tablets': 1,
            'cashiers': 2,
        },
        'features': {
            'offline': True,
            'kds': False,
            'api': False,
            'dashboard': 'basic',
            'fiscal': False,
            'advanced_reports': False,
        },
    },
    'professional': {
        'resource_limits': {
            'pos': 3,
            'registers': 10,
            'tablets': 10,
            'cashiers': 30,
        },
        'features': {
            'offline': True,
            'kds': True,
            'api': False,
            'dashboard': 'full',
            'fiscal': True,
            'advanced_reports': True,
        },
    },
    'enterprise': {
        'resource_limits': {
            'pos': -1,
            'registers': -1,
            'tablets': -1,
            'cashiers': -1,
        },
        'features': {
            'offline': True,
            'kds': True,
            'api': True,
            'dashboard': 'full',
            'fiscal': True,
            'advanced_reports': True,
        },
    },
}

# Fallback genérico para otros productos ETS
_DEFAULT_PLAN: dict[str, Any] = {
    'resource_limits': {},
    'features': {},
}

_PRODUCT_PLANS: dict[str, dict[str, dict[str, Any]]] = {
    'eposone': _EPOSONE_PLANS,
}


def normalize_plan_code(plan_code: str | None) -> str:
    code = (plan_code or 'starter').strip().lower()
    return code or 'starter'


def list_plan_codes(product_code: str) -> list[str]:
    product = (product_code or '').strip().lower()
    plans = _PRODUCT_PLANS.get(product) or {'starter': _DEFAULT_PLAN}
    return sorted(plans.keys())


def get_plan_template(product_code: str, plan_code: str | None) -> dict[str, Any]:
    """Devuelve ``{resource_limits, features}`` del plan (copia profunda)."""
    product = (product_code or '').strip().lower()
    plan = normalize_plan_code(plan_code)
    catalog = _PRODUCT_PLANS.get(product)
    if catalog and plan in catalog:
        return deepcopy(catalog[plan])
    if catalog and 'starter' in catalog:
        return deepcopy(catalog['starter'])
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
