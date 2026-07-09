"""Puente lectura dual tenant_crm_contact → Contact (Etapa 10c)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from models.core_master import CoreContactLegacyLink
from models.saas import TenantCrmContact
from nodeone.core.master.constants import MasterDataError
from nodeone.core.services.contacts import ContactDTO, ContactService


CONTACT_SOURCE_CANONICAL = 'canonical'
CONTACT_SOURCE_LINKED = 'linked'
CONTACT_SOURCE_LEGACY = 'legacy'


@dataclass(frozen=True)
class ResolvedContactDTO:
    contact: ContactDTO
    source: str
    canonical_contact_id: int | None = None
    legacy_crm_contact_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'source': self.source,
            'canonical_contact_id': self.canonical_contact_id,
            'legacy_crm_contact_id': self.legacy_crm_contact_id,
            'contact': self.contact.to_dict(),
        }


def _legacy_display_name(row: TenantCrmContact) -> str:
    return (
        (row.legal_name or '').strip()
        or (row.trade_name or '').strip()
        or (row.name or '').strip()
        or (row.company or '').strip()
        or f'Contacto #{row.id}'
    )


def _legacy_contact_type(row: TenantCrmContact) -> str:
    person_type = (row.person_type or 'natural').strip().lower()
    if person_type == 'juridica':
        return 'company'
    if person_type == 'final_consumer':
        return 'consumer_final'
    return 'person'


def _legacy_identification_type(row: TenantCrmContact) -> str:
    if (row.person_type or '').strip().lower() == 'final_consumer':
        return 'consumer_final'
    id_type = (row.id_type or '').strip().lower()
    if id_type in ('ruc', 'cedula', 'passport'):
        return id_type
    if (row.tax_id or '').strip():
        return 'ruc'
    return 'consumer_final'


def legacy_contact_to_dto(row: TenantCrmContact) -> ContactDTO:
    email = ((row.fiscal_email or row.email or '').strip().lower() or None)
    contact_type = _legacy_contact_type(row)
    return ContactDTO(
        id=int(row.id),
        organization_id=int(row.organization_id),
        display_name=_legacy_display_name(row)[:300],
        email=email,
        phone=((row.fiscal_phone or row.phone or '').strip() or None),
        mobile=None,
        contact_type=contact_type,
        identification_type=_legacy_identification_type(row),
        tax_id=((row.tax_id or '').strip() or None),
        dv=((row.tax_dv or '').strip() or None),
        is_customer=bool(row.is_customer),
        is_supplier=bool(row.is_supplier),
        is_member=False,
        is_student=False,
        is_participant=False,
        is_instructor=False,
        is_employee=bool(getattr(row, 'is_salesperson', False)),
        active=bool(row.is_active),
        roles=tuple(
            label
            for label, flag in (
                ('Cliente', row.is_customer),
                ('Proveedor', row.is_supplier),
                ('Vendedor', getattr(row, 'is_salesperson', False)),
            )
            if flag
        ),
    )


class ContactBridgeService:
    @staticmethod
    def get_legacy(organization_id: int, legacy_contact_id: int) -> TenantCrmContact | None:
        return TenantCrmContact.query.filter_by(
            organization_id=int(organization_id),
            id=int(legacy_contact_id),
        ).first()

    @staticmethod
    def get_link_by_legacy(organization_id: int, legacy_contact_id: int) -> CoreContactLegacyLink | None:
        return CoreContactLegacyLink.query.filter_by(
            organization_id=int(organization_id),
            legacy_contact_id=int(legacy_contact_id),
        ).first()

    @staticmethod
    def get_link_by_canonical(organization_id: int, contact_id: int) -> CoreContactLegacyLink | None:
        return CoreContactLegacyLink.query.filter_by(
            organization_id=int(organization_id),
            contact_id=int(contact_id),
        ).first()

    @staticmethod
    def resolve(organization_id: int, contact_id: int) -> ResolvedContactDTO | None:
        oid = int(organization_id)
        cid = int(contact_id)

        canonical = ContactService.get(oid, cid)
        if canonical is not None:
            link = ContactBridgeService.get_link_by_canonical(oid, cid)
            return ResolvedContactDTO(
                contact=canonical,
                source=CONTACT_SOURCE_LINKED if link is not None else CONTACT_SOURCE_CANONICAL,
                canonical_contact_id=cid,
                legacy_crm_contact_id=int(link.legacy_contact_id) if link is not None else None,
            )

        link = ContactBridgeService.get_link_by_legacy(oid, cid)
        if link is not None:
            linked = ContactService.get(oid, int(link.contact_id))
            if linked is not None:
                return ResolvedContactDTO(
                    contact=linked,
                    source=CONTACT_SOURCE_LINKED,
                    canonical_contact_id=int(link.contact_id),
                    legacy_crm_contact_id=cid,
                )

        legacy = ContactBridgeService.get_legacy(oid, cid)
        if legacy is None or not legacy.is_active:
            return None
        return ResolvedContactDTO(
            contact=legacy_contact_to_dto(legacy),
            source=CONTACT_SOURCE_LEGACY,
            canonical_contact_id=None,
            legacy_crm_contact_id=cid,
        )

    @staticmethod
    def link(organization_id: int, *, contact_id: int, legacy_contact_id: int, link_source: str = 'manual') -> None:
        from app import db

        oid = int(organization_id)
        canonical = ContactService.get(oid, int(contact_id))
        if canonical is None:
            raise MasterDataError('contact_not_found')
        legacy = ContactBridgeService.get_legacy(oid, int(legacy_contact_id))
        if legacy is None:
            raise MasterDataError('legacy_contact_not_found')

        if ContactBridgeService.get_link_by_canonical(oid, int(contact_id)):
            raise MasterDataError('canonical_already_linked')
        if ContactBridgeService.get_link_by_legacy(oid, int(legacy_contact_id)):
            raise MasterDataError('legacy_already_linked')

        row = CoreContactLegacyLink(
            organization_id=oid,
            contact_id=int(contact_id),
            legacy_contact_id=int(legacy_contact_id),
            link_source=(link_source or 'manual')[:32],
        )
        db.session.add(row)
        db.session.commit()
