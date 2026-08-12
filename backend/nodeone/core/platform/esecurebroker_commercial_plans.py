"""Catálogo comercial ESecureBroker (producto ``esecurebroker``).

Separado de ``commercial_plans`` (EPosOne). No reutiliza códigos
``starter`` / ``business`` de EPosOne.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

PRODUCT_CODE = 'esecurebroker'

# Códigos definitivos ESB (Slice C1)
PLAN_INDIVIDUAL = 'individual'
PLAN_OFFICE = 'office'
PLAN_BROKER = 'broker'
PLAN_ENTERPRISE = 'enterprise'

_PLAN_ORDER = (PLAN_INDIVIDUAL, PLAN_OFFICE, PLAN_BROKER, PLAN_ENTERPRISE)

# Checkout self-serve solo para planes con precio mensual fijo.
# enterprise = cotización / contrato especial (no checkout automático).
ESB_COMMERCIAL_PLANS: dict[str, dict[str, Any]] = {
    PLAN_INDIVIDUAL: {
        'code': PLAN_INDIVIDUAL,
        'name': 'Individual',
        'description': 'Plan individual ESecureBroker.',
        'price_monthly': 55.0,
        'currency': 'USD',
        'status': 'active',
        'checkout_mode': 'self_serve',
        'resource_limits': {
            # Capacidad contratada (no inferir por precio).
            'internal_seats': 1,
            # Productores adicionales: no aprobados comercialmente → null.
            'producer_seats': None,
        },
        'features': {
            'corredor_core': True,
            'producers_network': False,
            'custom_contract': False,
        },
    },
    PLAN_OFFICE: {
        'code': PLAN_OFFICE,
        'name': 'Oficina',
        'description': 'Plan oficina ESecureBroker.',
        'price_monthly': 129.0,
        'currency': 'USD',
        'status': 'active',
        'checkout_mode': 'self_serve',
        'resource_limits': {
            'internal_seats': 15,
            'producer_seats': None,
        },
        'features': {
            'corredor_core': True,
            'producers_network': False,
            'custom_contract': False,
        },
    },
    PLAN_BROKER: {
        'code': PLAN_BROKER,
        'name': 'Broker / Red',
        'description': 'Plan broker/red ESecureBroker.',
        'price_monthly': 229.0,
        'currency': 'USD',
        'status': 'active',
        'checkout_mode': 'self_serve',
        'resource_limits': {
            # Cantidades incluidas aún no cerradas comercialmente.
            'internal_seats': None,
            'producer_seats': None,
        },
        'features': {
            'corredor_core': True,
            # Capacidad de productores extensible; cupo incluido = TBD.
            'producers_network': True,
            'custom_contract': False,
        },
    },
    PLAN_ENTERPRISE: {
        'code': PLAN_ENTERPRISE,
        'name': 'Enterprise',
        'description': 'Plan enterprise ESecureBroker (cotización).',
        'price_monthly': None,
        'currency': 'USD',
        'status': 'active',
        'checkout_mode': 'quote',
        'resource_limits': {
            'internal_seats': None,
            'producer_seats': None,
        },
        'features': {
            'corredor_core': True,
            'producers_network': True,
            'custom_contract': True,
        },
    },
}


def list_esb_plan_codes() -> list[str]:
    return list(_PLAN_ORDER)


def normalize_esb_plan_code(plan_code: str | None) -> str | None:
    raw = (plan_code or '').strip().lower()
    if not raw:
        return None
    if raw in ESB_COMMERCIAL_PLANS:
        return raw
    return None


def get_esb_plan(plan_code: str | None) -> dict[str, Any] | None:
    code = normalize_esb_plan_code(plan_code)
    if code is None:
        return None
    return deepcopy(ESB_COMMERCIAL_PLANS[code])


def get_esb_list_price(plan_code: str | None) -> float | None:
    """Precio mensual self-serve; None si cotización / desconocido."""
    plan = get_esb_plan(plan_code)
    if plan is None:
        return None
    if plan.get('checkout_mode') != 'self_serve':
        return None
    price = plan.get('price_monthly')
    if price is None:
        return None
    return float(price)


def esb_entitlement_template(plan_code: str | None) -> dict[str, Any]:
    plan = get_esb_plan(plan_code)
    if plan is None:
        return {'resource_limits': {}, 'features': {}}
    return {
        'resource_limits': deepcopy(plan.get('resource_limits') or {}),
        'features': deepcopy(plan.get('features') or {}),
    }


def list_esb_commercial_plans() -> list[dict[str, Any]]:
    return [deepcopy(ESB_COMMERCIAL_PLANS[c]) for c in _PLAN_ORDER]
