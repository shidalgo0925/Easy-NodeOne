"""Constantes modelo maestro Core — Etapa 10b."""

from __future__ import annotations

ORG_UNIT_TYPE_COMPANY = 'company'
ORG_UNIT_TYPE_BRANCH = 'branch'
ORG_UNIT_TYPE_WAREHOUSE = 'warehouse'
ORG_UNIT_TYPE_POS_TERMINAL = 'pos_terminal'

ORG_UNIT_TYPES = frozenset(
    {
        ORG_UNIT_TYPE_COMPANY,
        ORG_UNIT_TYPE_BRANCH,
        ORG_UNIT_TYPE_WAREHOUSE,
        ORG_UNIT_TYPE_POS_TERMINAL,
    }
)

ORG_UNIT_STATUS_ACTIVE = 'active'
ORG_UNIT_STATUS_INACTIVE = 'inactive'

ORG_UNIT_STATUSES = frozenset({ORG_UNIT_STATUS_ACTIVE, ORG_UNIT_STATUS_INACTIVE})

ADDRESS_OWNER_ORGANIZATION = 'organization'
ADDRESS_OWNER_ORG_UNIT = 'org_unit'
ADDRESS_OWNER_CONTACT = 'contact'

ADDRESS_OWNER_TYPES = frozenset({ADDRESS_OWNER_ORGANIZATION, ADDRESS_OWNER_ORG_UNIT, ADDRESS_OWNER_CONTACT})

ADDRESS_KIND_FISCAL = 'fiscal'
ADDRESS_KIND_DELIVERY = 'delivery'
ADDRESS_KIND_VENUE = 'venue'

ADDRESS_KINDS = frozenset({ADDRESS_KIND_FISCAL, ADDRESS_KIND_DELIVERY, ADDRESS_KIND_VENUE})

PRODUCT_TYPE_GOOD = 'good'
PRODUCT_TYPE_SERVICE = 'service'
PRODUCT_TYPE_PLAN = 'plan'
PRODUCT_TYPE_EVENT_SKU = 'event_sku'
PRODUCT_TYPE_KIT = 'kit'

PRODUCT_TYPES = frozenset(
    {
        PRODUCT_TYPE_GOOD,
        PRODUCT_TYPE_SERVICE,
        PRODUCT_TYPE_PLAN,
        PRODUCT_TYPE_EVENT_SKU,
        PRODUCT_TYPE_KIT,
    }
)

PRODUCT_STATUS_ACTIVE = 'active'
PRODUCT_STATUS_INACTIVE = 'inactive'

PRODUCT_STATUSES = frozenset({PRODUCT_STATUS_ACTIVE, PRODUCT_STATUS_INACTIVE})

# Mapa referencia — catálogos legacy por app (sin migración en Etapa 10d).
LEGACY_CATALOG_SOURCES: dict[str, str] = {
    'service': 'catalog.service',
    'plan': 'benefits.membership_plan',
    'event_sku': 'events.event',
    'appointment_sku': 'appointments.appointment_type',
    'academic_sku': 'academic.academic_program',
    'contador_sku': 'contador.contador_product',
    'quotation_line': 'accounting.quotation_lines',
    'invoice_line': 'accounting.invoice_lines',
}


class MasterDataError(ValueError):
    """Error de validación en entidades maestras Core."""
