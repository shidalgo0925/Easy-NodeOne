"""OrgUnitService — jerarquía org/sucursal/bodega/terminal (Etapa 10b/11)."""

from __future__ import annotations

from typing import Any

from nodeone.core.master.dtos import OrgUnitDTO
from nodeone.core.master.org_unit import OrgUnitService as _CoreOrgUnitService


class OrgUnitService:
    """API Core para unidades organizativas (`core_org_unit`)."""

    @staticmethod
    def list_units(
        organization_id: int,
        *,
        unit_type: str | None = None,
        status: str | None = None,
    ) -> list[OrgUnitDTO]:
        return _CoreOrgUnitService.list_units(
            int(organization_id),
            unit_type=unit_type,
            status=status,
        )

    @staticmethod
    def get_by_ref(organization_id: int, unit_ref: str) -> OrgUnitDTO | None:
        return _CoreOrgUnitService.get_by_ref(int(organization_id), unit_ref)

    @staticmethod
    def create(organization_id: int, data: dict[str, Any]) -> OrgUnitDTO:
        return _CoreOrgUnitService.create(
            int(organization_id),
            unit_ref=str(data.get('unit_ref') or ''),
            name=str(data.get('name') or ''),
            unit_type=str(data.get('unit_type') or ''),
            parent_id=data.get('parent_id'),
            notes=data.get('notes'),
            status=str(data.get('status') or 'active'),
        )
