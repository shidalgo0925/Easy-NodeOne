"""OrgUnitService — jerarquía org/sucursal/bodega/terminal (Etapa 10b)."""

from __future__ import annotations

from models.core_master import CoreOrgUnit
from nodeone.core.master.constants import (
    ORG_UNIT_STATUS_ACTIVE,
    ORG_UNIT_STATUSES,
    ORG_UNIT_TYPES,
    MasterDataError,
)
from nodeone.core.master.dtos import OrgUnitDTO


def org_unit_to_dto(row: CoreOrgUnit) -> OrgUnitDTO:
    return OrgUnitDTO(
        id=int(row.id),
        organization_id=int(row.organization_id),
        unit_ref=str(row.unit_ref),
        name=str(row.name),
        unit_type=str(row.unit_type),
        status=str(row.status),
        parent_id=int(row.parent_id) if row.parent_id is not None else None,
        notes=str(row.notes) if row.notes else None,
    )


class OrgUnitService:
    @staticmethod
    def list_units(
        organization_id: int,
        *,
        unit_type: str | None = None,
        status: str | None = None,
    ) -> list[OrgUnitDTO]:
        q = CoreOrgUnit.query.filter_by(organization_id=int(organization_id))
        if unit_type:
            q = q.filter_by(unit_type=(unit_type or '').strip().lower())
        if status:
            q = q.filter_by(status=(status or '').strip().lower())
        rows = q.order_by(CoreOrgUnit.name.asc(), CoreOrgUnit.id.asc()).all()
        return [org_unit_to_dto(row) for row in rows]

    @staticmethod
    def get_by_ref(organization_id: int, unit_ref: str) -> OrgUnitDTO | None:
        ref = (unit_ref or '').strip()
        if not ref:
            return None
        row = CoreOrgUnit.query.filter_by(organization_id=int(organization_id), unit_ref=ref).first()
        return org_unit_to_dto(row) if row is not None else None

    @staticmethod
    def create(
        organization_id: int,
        *,
        unit_ref: str,
        name: str,
        unit_type: str,
        parent_id: int | None = None,
        notes: str | None = None,
        status: str = ORG_UNIT_STATUS_ACTIVE,
    ) -> OrgUnitDTO:
        from app import db

        ref = (unit_ref or '').strip()
        label = (name or '').strip()
        utype = (unit_type or '').strip().lower()
        st = (status or ORG_UNIT_STATUS_ACTIVE).strip().lower()
        if not ref:
            raise MasterDataError('unit_ref_required')
        if not label:
            raise MasterDataError('name_required')
        if utype not in ORG_UNIT_TYPES:
            raise MasterDataError(f'invalid_unit_type:{utype}')
        if st not in ORG_UNIT_STATUSES:
            raise MasterDataError(f'invalid_status:{st}')

        existing = CoreOrgUnit.query.filter_by(organization_id=int(organization_id), unit_ref=ref).first()
        if existing is not None:
            raise MasterDataError('unit_ref_exists')

        if parent_id is not None:
            parent = CoreOrgUnit.query.filter_by(
                organization_id=int(organization_id),
                id=int(parent_id),
            ).first()
            if parent is None:
                raise MasterDataError('parent_not_found')

        row = CoreOrgUnit(
            organization_id=int(organization_id),
            parent_id=int(parent_id) if parent_id is not None else None,
            unit_ref=ref,
            name=label,
            unit_type=utype,
            status=st,
            notes=(notes or None),
        )
        db.session.add(row)
        db.session.commit()
        return org_unit_to_dto(row)
