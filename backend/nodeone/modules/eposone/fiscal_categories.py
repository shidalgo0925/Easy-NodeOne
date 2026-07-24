"""Categorías fiscales Panamá (ITBMS) — seed y resolución de tasa.

Base legal: Código Fiscal art. 1057-V / DGI — ITBMS 7% general,
10% bebidas alcohólicas y hospedaje, 15% tabaco, exentos 0%.

Modo precio default POS: **tax-inclusive** (precio de menú incluye ITBMS;
el motor desglosa para recibo y no vuelve a sumar el impuesto al total cobrable).
Override: EPOSONE_PRICES_INCLUDE_TAX=0 → tax-exclusive.

ISC (selectivo) es impuesto distinto (fabricación/importación); no se
mezcla aquí como tasa de venta POS por defecto.
"""

from __future__ import annotations

from typing import Any

# Códigos estables usados en core_product.fiscal_category
FISCAL_CATEGORY_ITBMS_7 = 'ITBMS_7'
FISCAL_CATEGORY_ITBMS_10 = 'ITBMS_10'
FISCAL_CATEGORY_ITBMS_15 = 'ITBMS_15'
FISCAL_CATEGORY_EXENTO = 'EXENTO'
FISCAL_CATEGORY_DEFAULT = FISCAL_CATEGORY_ITBMS_7

POLICY_CODE_PA_ITBMS = 'PA-ITBMS-V1'

FISCAL_CATEGORIES_PA: dict[str, dict[str, Any]] = {
    FISCAL_CATEGORY_ITBMS_7: {
        'code': FISCAL_CATEGORY_ITBMS_7,
        'name': 'ITBMS 7% (general)',
        'type': 'vat_like',
        'percent': 7.0,
        'description': 'Tasa general de bienes y servicios',
    },
    FISCAL_CATEGORY_ITBMS_10: {
        'code': FISCAL_CATEGORY_ITBMS_10,
        'name': 'ITBMS 10% (alcohol / hospedaje)',
        'type': 'vat_like',
        'percent': 10.0,
        'description': (
            'Importación y venta de bebidas alcohólicas; '
            'servicio de hospedaje (DGI / art. 1057-V)'
        ),
    },
    FISCAL_CATEGORY_ITBMS_15: {
        'code': FISCAL_CATEGORY_ITBMS_15,
        'name': 'ITBMS 15% (tabaco)',
        'type': 'vat_like',
        'percent': 15.0,
        'description': 'Productos derivados del tabaco',
    },
    FISCAL_CATEGORY_EXENTO: {
        'code': FISCAL_CATEGORY_EXENTO,
        'name': 'Exento',
        'type': 'exempt',
        'percent': 0.0,
        'description': 'Bienes/servicios no gravados con ITBMS',
    },
}


def normalize_fiscal_category(raw: str | None) -> str | None:
    code = str(raw or '').strip().upper()
    if not code:
        return None
    # aliases
    aliases = {
        'ALCOHOL': FISCAL_CATEGORY_ITBMS_10,
        'LICOR': FISCAL_CATEGORY_ITBMS_10,
        'BEBIDAS_ALCOHOLICAS': FISCAL_CATEGORY_ITBMS_10,
        'TABACO': FISCAL_CATEGORY_ITBMS_15,
        'GENERAL': FISCAL_CATEGORY_ITBMS_7,
        '7': FISCAL_CATEGORY_ITBMS_7,
        '10': FISCAL_CATEGORY_ITBMS_10,
        '15': FISCAL_CATEGORY_ITBMS_15,
        '0': FISCAL_CATEGORY_EXENTO,
        'EXEMPT': FISCAL_CATEGORY_EXENTO,
    }
    code = aliases.get(code, code)
    if code not in FISCAL_CATEGORIES_PA:
        return None
    return code


def tax_percent_for_category(fiscal_category: str | None) -> float:
    code = normalize_fiscal_category(fiscal_category) or FISCAL_CATEGORY_DEFAULT
    return float(FISCAL_CATEGORIES_PA[code]['percent'])


# Panamá retail/restaurant: el precio de lista del menú ya incluye ITBMS.
# El motor desglosa base+impuesto para recibo; el total cobrable NO vuelve a sumar tax.
DEFAULT_PRICES_INCLUDE_TAX = True


def prices_include_tax_enabled() -> bool:
    import os

    raw = (os.environ.get('EPOSONE_PRICES_INCLUDE_TAX') or '').strip().lower()
    if raw in {'0', 'false', 'no', 'exclusive', 'neto'}:
        return False
    if raw in {'1', 'true', 'yes', 'inclusive', 'incluido'}:
        return True
    return DEFAULT_PRICES_INCLUDE_TAX


def line_tax_amount(
    *,
    qty: float,
    unit_price: float,
    fiscal_category: str | None,
    discount: float = 0.0,
    prices_include_tax: bool | None = None,
) -> float:
    """ITBMS de línea.

    - Inclusive (default PA): desglose desde precio con impuesto → base × r/(1+r)
    - Exclusive: (qty×precio − desc) × tasa
    """
    base = max(0.0, float(qty or 0) * float(unit_price or 0) - float(discount or 0))
    rate = tax_percent_for_category(fiscal_category) / 100.0
    if rate <= 0:
        return 0.0
    inclusive = (
        prices_include_tax_enabled()
        if prices_include_tax is None
        else bool(prices_include_tax)
    )
    if inclusive:
        return round(base * rate / (1.0 + rate), 4)
    return round(base * rate, 4)


def order_payable_total(
    *,
    subtotal: float,
    tax: float,
    discount: float,
    tip: float,
    prices_include_tax: bool | None = None,
) -> float:
    """Total a cobrar (centavos). Inclusive: tax ya va en subtotal."""
    inclusive = (
        prices_include_tax_enabled()
        if prices_include_tax is None
        else bool(prices_include_tax)
    )
    sub = float(subtotal or 0)
    disc = float(discount or 0)
    tip_v = float(tip or 0)
    if inclusive:
        return round(sub - disc + tip_v + 1e-12, 2)
    return round(sub + float(tax or 0) - disc + tip_v + 1e-12, 2)


def panama_fiscal_policy_payload() -> dict[str, Any]:
    return {
        'country': 'PA',
        'legal_basis': 'Codigo Fiscal art. 1057-V / DGI ITBMS',
        'default_category': FISCAL_CATEGORY_DEFAULT,
        'categories': FISCAL_CATEGORIES_PA,
        'rules': [
            {
                'code': c['code'],
                'name': c['name'],
                'type': c['type'],
                'percent': c['percent'],
                'priority': 10,
                'accumulates': False,
            }
            for c in FISCAL_CATEGORIES_PA.values()
        ],
    }


def ensure_panama_fiscal_seed(organization_id: int) -> dict[str, Any]:
    """Crea/publica política fiscal PA si no existe (idempotente)."""
    from models.eposone_commercial_policy import EposoneCommercialPolicy
    from nodeone.modules.eposone.commercial_policy_service import (
        CommercialPolicyService,
        CommercialPolicyValidationError,
    )

    oid = int(organization_id)
    existing = EposoneCommercialPolicy.query.filter_by(
        organization_id=oid,
        policy_type='fiscal',
        code=POLICY_CODE_PA_ITBMS,
    ).first()
    payload = panama_fiscal_policy_payload()
    if existing is None:
        return CommercialPolicyService.create_policy(
            oid,
            policy_type='fiscal',
            code=POLICY_CODE_PA_ITBMS,
            name='Panamá — ITBMS (7/10/15/Exento)',
            payload=payload,
            assign_organization_scope=True,
            publish=True,
        )
    # Ya existe: republicar payload canónico si está draft o actualizar versión
    from models.eposone_commercial_policy import EposoneCommercialPolicyVersion

    active = EposoneCommercialPolicyVersion.query.filter_by(
        policy_id=int(existing.id), publication_status='active'
    ).first()
    if active is not None:
        return CommercialPolicyService.policy_to_dict(existing, active)
    try:
        return CommercialPolicyService.publish_version(
            oid, int(existing.id), payload=payload
        )
    except CommercialPolicyValidationError:
        return CommercialPolicyService.policy_to_dict(existing)
