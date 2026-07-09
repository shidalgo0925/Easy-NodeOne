"""ContactService — maestro de terceros (Etapa 11)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nodeone.modules.contacts import service as _contact_svc


@dataclass(frozen=True)
class ContactDTO:
    """Vista serializable de Contact — Apps consumen esto, no el ORM."""

    id: int
    organization_id: int
    display_name: str
    email: str | None
    phone: str | None
    mobile: str | None
    contact_type: str
    identification_type: str
    tax_id: str | None
    dv: str | None
    is_customer: bool
    is_supplier: bool
    is_member: bool
    is_student: bool
    is_participant: bool
    is_instructor: bool
    is_employee: bool
    active: bool
    roles: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'display_name': self.display_name,
            'email': self.email,
            'phone': self.phone,
            'mobile': self.mobile,
            'contact_type': self.contact_type,
            'identification_type': self.identification_type,
            'tax_id': self.tax_id,
            'dv': self.dv,
            'is_customer': self.is_customer,
            'is_supplier': self.is_supplier,
            'is_member': self.is_member,
            'is_student': self.is_student,
            'is_participant': self.is_participant,
            'is_instructor': self.is_instructor,
            'is_employee': self.is_employee,
            'active': self.active,
            'roles': list(self.roles),
        }


def _to_dto(row) -> ContactDTO:
    return ContactDTO(
        id=int(row.id),
        organization_id=int(row.organization_id),
        display_name=str(row.display_name or ''),
        email=(row.email or '').strip() or None,
        phone=(row.phone or '').strip() or None,
        mobile=(row.mobile or '').strip() or None,
        contact_type=str(row.contact_type or 'person'),
        identification_type=str(row.identification_type or 'consumer_final'),
        tax_id=(row.tax_id or '').strip() or None,
        dv=(row.dv or '').strip() or None,
        is_customer=bool(row.is_customer),
        is_supplier=bool(row.is_supplier),
        is_member=bool(row.is_member),
        is_student=bool(row.is_student),
        is_participant=bool(row.is_participant),
        is_instructor=bool(row.is_instructor),
        is_employee=bool(row.is_employee),
        active=bool(row.active),
        roles=tuple(row.role_labels()),
    )


class ContactService:
    """API Core para contactos/terceros. Delega en ``nodeone.modules.contacts.service``."""

    ValidationError = _contact_svc.ContactValidationError

    @staticmethod
    def get(organization_id: int, contact_id: int) -> ContactDTO | None:
        row = _contact_svc.get_contact(int(organization_id), int(contact_id))
        return _to_dto(row) if row is not None else None

    @staticmethod
    def find_by_email(organization_id: int, email: str, *, active_only: bool = True) -> ContactDTO | None:
        key = (email or '').strip().lower()
        if not key:
            return None
        rows, _ = _contact_svc.search_contacts(
            int(organization_id),
            q=key,
            active_only=True if active_only else None,
            limit=5,
        )
        for row in rows:
            if (row.email or '').strip().lower() == key:
                return _to_dto(row)
        return None

    @staticmethod
    def find_by_tax_id(
        organization_id: int,
        tax_id: str,
        *,
        dv: str | None = None,
        active_only: bool = True,
    ) -> ContactDTO | None:
        from models.contact import Contact

        tid = (tax_id or '').strip()
        if not tid:
            return None
        q = Contact.query.filter_by(organization_id=int(organization_id), tax_id=tid)
        if active_only:
            q = q.filter(Contact.active.is_(True))
        dv_norm = (dv or '').strip()
        if dv_norm:
            q = q.filter(Contact.dv == dv_norm)
        row = q.first()
        return _to_dto(row) if row is not None else None

    @staticmethod
    def resolve_ref(organization_id: int, contact_ref: str) -> ContactDTO:
        """Resuelve contact_ref a Contact canónico activo (en1_contact)."""
        from nodeone.core.master.contact_bridge import ContactBridgeService

        ref = (contact_ref or '').strip()
        if not ref:
            raise ContactService.ValidationError('contact_ref_empty')

        oid = int(organization_id)
        lower = ref.lower()

        def _require_active(dto: ContactDTO) -> ContactDTO:
            if not dto.active:
                raise ContactService.ValidationError('contact_inactive')
            return dto

        if lower.startswith('legacy:'):
            raw = ref.split(':', 1)[1].strip()
            if not raw.isdigit():
                raise ContactService.ValidationError('invalid_contact_ref')
            resolved = ContactBridgeService.resolve(oid, int(raw))
            if resolved is None or resolved.canonical_contact_id is None:
                raise ContactService.ValidationError('invalid_contact_ref')
            canonical = ContactService.get(oid, int(resolved.canonical_contact_id))
            if canonical is None:
                raise ContactService.ValidationError('invalid_contact_ref')
            return _require_active(canonical)

        if '@' in ref:
            dto = ContactService.find_by_email(oid, ref)
            if dto is None:
                raise ContactService.ValidationError('invalid_contact_ref')
            return _require_active(dto)

        if lower.startswith('tax:'):
            tax_part = ref.split(':', 1)[1].strip()
            tax_id = tax_part
            dv = None
            if '-' in tax_part:
                tax_id, _, dv = tax_part.partition('-')
                tax_id = tax_id.strip()
                dv = (dv.strip() or None)
            dto = ContactService.find_by_tax_id(oid, tax_id, dv=dv)
            if dto is None:
                raise ContactService.ValidationError('invalid_contact_ref')
            return _require_active(dto)

        if ref.isdigit():
            cid = int(ref)
            dto = ContactService.get(oid, cid)
            if dto is not None:
                return _require_active(dto)
            resolved = ContactBridgeService.resolve(oid, cid)
            if resolved is None or resolved.canonical_contact_id is None:
                raise ContactService.ValidationError('invalid_contact_ref')
            linked = ContactService.get(oid, int(resolved.canonical_contact_id))
            if linked is None:
                raise ContactService.ValidationError('invalid_contact_ref')
            return _require_active(linked)

        raise ContactService.ValidationError('invalid_contact_ref')

    @staticmethod
    def search(
        organization_id: int,
        *,
        q: str = '',
        role: str = '',
        active_only: bool | None = True,
        contact_type: str = '',
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[ContactDTO], int]:
        rows, total = _contact_svc.search_contacts(
            int(organization_id),
            q=q,
            role=role,
            active_only=active_only,
            contact_type=contact_type,
            limit=limit,
            offset=offset,
        )
        return [_to_dto(r) for r in rows], int(total)

    @staticmethod
    def create(organization_id: int, data: dict[str, Any]) -> ContactDTO:
        row = _contact_svc.create_contact(int(organization_id), data)
        return _to_dto(row)

    @staticmethod
    def create_with_legacy_link(organization_id: int, data: dict[str, Any]) -> ContactDTO:
        """Crea contacto canónico y opcionalmente enlaza con tenant_crm_contact legacy."""
        from nodeone.core.master.contact_bridge import ContactBridgeService
        from nodeone.core.master.constants import MasterDataError

        payload = dict(data or {})
        legacy_raw = payload.pop('legacy_contact_id', None)
        dto = ContactService.create(int(organization_id), payload)
        if legacy_raw is not None:
            try:
                ContactBridgeService.link(
                    int(organization_id),
                    contact_id=int(dto.id),
                    legacy_contact_id=int(legacy_raw),
                    link_source='eposone_create',
                )
            except MasterDataError as exc:
                raise ContactService.ValidationError(str(exc)) from exc
        return dto

    @staticmethod
    def update(organization_id: int, contact_id: int, data: dict[str, Any]) -> ContactDTO:
        row = _contact_svc.update_contact(int(organization_id), int(contact_id), data)
        return _to_dto(row)

    @staticmethod
    def fiscal_api_dict(organization_id: int, contact_id: int) -> dict[str, Any] | None:
        """Bloque fiscal para facturación — sin importar invoice_integration desde Apps."""
        row = _contact_svc.get_contact(int(organization_id), int(contact_id))
        if row is None:
            return None
        from nodeone.modules.contacts.invoice_integration import contact_to_api_dict

        return contact_to_api_dict(row)

    @staticmethod
    def resolve(organization_id: int, contact_id: int):
        """Lectura dual canonical + legacy (Etapa 10c)."""
        from nodeone.core.master.contact_bridge import ContactBridgeService

        return ContactBridgeService.resolve(int(organization_id), int(contact_id))
