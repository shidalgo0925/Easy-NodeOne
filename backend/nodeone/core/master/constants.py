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


class MasterDataError(ValueError):
    """Error de validación en entidades maestras Core."""
