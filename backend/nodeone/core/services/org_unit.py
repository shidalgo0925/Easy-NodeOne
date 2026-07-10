"""OrgUnitService — jerarquía org/sucursal/POS/caja (Etapa 10b/11 + ADR-005)."""

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
        parent_id: int | None = None,
    ) -> list[OrgUnitDTO]:
        return _CoreOrgUnitService.list_units(
            int(organization_id),
            unit_type=unit_type,
            status=status,
            parent_id=parent_id,
        )

    @staticmethod
    def get(organization_id: int, unit_id: int) -> OrgUnitDTO | None:
        return _CoreOrgUnitService.get(int(organization_id), int(unit_id))

    @staticmethod
    def get_by_ref(organization_id: int, unit_ref: str) -> OrgUnitDTO | None:
        return _CoreOrgUnitService.get_by_ref(int(organization_id), unit_ref)

    @staticmethod
    def create(organization_id: int, data: dict[str, Any]) -> OrgUnitDTO:
        return _CoreOrgUnitService.create(
            int(organization_id),
            unit_ref=str(data.get('unit_ref') or data.get('code') or ''),
            name=str(data.get('name') or ''),
            unit_type=str(data.get('unit_type') or ''),
            parent_id=data.get('parent_id') or data.get('branch_id'),
            notes=data.get('notes') or data.get('description'),
            status=str(data.get('status') or 'active'),
        )

    @staticmethod
    def update(organization_id: int, unit_id: int, data: dict[str, Any]) -> OrgUnitDTO:
        return _CoreOrgUnitService.update(
            int(organization_id),
            int(unit_id),
            name=data.get('name'),
            notes=data.get('notes') if 'notes' in data else data.get('description'),
            parent_id=data.get('parent_id'),
            status=data.get('status'),
        )

    @staticmethod
    def deactivate(organization_id: int, unit_id: int) -> OrgUnitDTO:
        return _CoreOrgUnitService.deactivate(int(organization_id), int(unit_id))
