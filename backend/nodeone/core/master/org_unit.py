"""OrgUnitService — jerarquía org/sucursal/POS/caja (Etapa 10b + ADR-005)."""

from __future__ import annotations

from models.core_master import CoreOrgUnit
from nodeone.core.license.policy import policy_for_organization
from nodeone.core.master.constants import (
    ORG_UNIT_POS_TYPES,
    ORG_UNIT_STATUS_ACTIVE,
    ORG_UNIT_STATUS_INACTIVE,
    ORG_UNIT_STATUSES,
    ORG_UNIT_TYPE_BRANCH,
    ORG_UNIT_TYPE_POS,
    ORG_UNIT_TYPE_POS_TERMINAL,
    ORG_UNIT_TYPE_REGISTER,
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


def _license_resource_for_unit_type(unit_type: str) -> str | None:
    ut = (unit_type or '').strip().lower()
    if ut == ORG_UNIT_TYPE_BRANCH:
        return 'branch'
    if ut in ORG_UNIT_POS_TYPES:
        return 'pos'
    if ut == ORG_UNIT_TYPE_REGISTER:
        return 'register'
    return None


def _is_pos_type(unit_type: str) -> bool:
    return (unit_type or '').strip().lower() in ORG_UNIT_POS_TYPES


class OrgUnitService:
    @staticmethod
    def list_units(
        organization_id: int,
        *,
        unit_type: str | None = None,
        status: str | None = None,
        parent_id: int | None = None,
    ) -> list[OrgUnitDTO]:
        q = CoreOrgUnit.query.filter_by(organization_id=int(organization_id))
        if unit_type:
            ut = (unit_type or '').strip().lower()
            if ut == ORG_UNIT_TYPE_POS:
                from sqlalchemy import or_

                q = q.filter(
                    or_(
                        CoreOrgUnit.unit_type == ORG_UNIT_TYPE_POS,
                        CoreOrgUnit.unit_type == ORG_UNIT_TYPE_POS_TERMINAL,
                    )
                )
            else:
                q = q.filter_by(unit_type=ut)
        if status:
            q = q.filter_by(status=(status or '').strip().lower())
        if parent_id is not None:
            q = q.filter_by(parent_id=int(parent_id))
        rows = q.order_by(CoreOrgUnit.name.asc(), CoreOrgUnit.id.asc()).all()
        return [org_unit_to_dto(row) for row in rows]

    @staticmethod
    def get(organization_id: int, unit_id: int) -> OrgUnitDTO | None:
        row = CoreOrgUnit.query.filter_by(
            organization_id=int(organization_id),
            id=int(unit_id),
        ).first()
        return org_unit_to_dto(row) if row is not None else None

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
        # POS nuevos como 'pos'; aceptar legado pos_terminal en entrada
        if utype == ORG_UNIT_TYPE_POS_TERMINAL:
            utype = ORG_UNIT_TYPE_POS
        st = (status or ORG_UNIT_STATUS_ACTIVE).strip().lower()
        if not ref:
            raise MasterDataError('unit_ref_required')
        if not label:
            raise MasterDataError('name_required')
        if utype not in ORG_UNIT_TYPES:
            raise MasterDataError(f'invalid_unit_type:{utype}')
        if st not in ORG_UNIT_STATUSES:
            raise MasterDataError(f'invalid_status:{st}')

        resource = _license_resource_for_unit_type(utype)
        if resource:
            policy_for_organization(int(organization_id)).assert_can_create(resource)

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

    @staticmethod
    def update(
        organization_id: int,
        unit_id: int,
        *,
        name: str | None = None,
        notes: str | None = None,
        parent_id: int | None = None,
        status: str | None = None,
    ) -> OrgUnitDTO:
        from app import db

        row = CoreOrgUnit.query.filter_by(
            organization_id=int(organization_id),
            id=int(unit_id),
        ).first()
        if row is None:
            raise MasterDataError('unit_not_found')
        if name is not None:
            label = name.strip()
            if not label:
                raise MasterDataError('name_required')
            row.name = label
        if notes is not None:
            row.notes = notes.strip() or None
        if status is not None:
            st = status.strip().lower()
            if st not in ORG_UNIT_STATUSES:
                raise MasterDataError(f'invalid_status:{st}')
            row.status = st
        if parent_id is not None:
            if int(parent_id) == int(row.id):
                raise MasterDataError('invalid_parent')
            parent = CoreOrgUnit.query.filter_by(
                organization_id=int(organization_id),
                id=int(parent_id),
            ).first()
            if parent is None:
                raise MasterDataError('parent_not_found')
            row.parent_id = int(parent_id)
        db.session.commit()
        return org_unit_to_dto(row)

    @staticmethod
    def deactivate(organization_id: int, unit_id: int) -> OrgUnitDTO:
        return OrgUnitService.update(
            int(organization_id),
            int(unit_id),
            status=ORG_UNIT_STATUS_INACTIVE,
        )

    @staticmethod
    def matches_pos_type(unit_type: str) -> bool:
        return _is_pos_type(unit_type)
