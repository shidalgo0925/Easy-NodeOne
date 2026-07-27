"""UserContactLinkService — vínculo User ↔ Contact (Etapa 10e)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nodeone.core.master.constants import MasterDataError
from nodeone.core.services.contacts import ContactDTO, ContactService


@dataclass(frozen=True)
class UserContactLinkDTO:
    user_id: int
    organization_id: int
    linked_contact_id: int | None
    contact: ContactDTO | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            'user_id': self.user_id,
            'organization_id': self.organization_id,
            'linked_contact_id': self.linked_contact_id,
        }
        if self.contact is not None:
            payload['contact'] = self.contact.to_dict()
        return payload


class UserContactLinkService:
    @staticmethod
    def get(user_id: int, organization_id: int) -> UserContactLinkDTO:
        from models.users import User

        row = User.query.get(int(user_id))
        if row is None:
            raise MasterDataError('user_not_found')
        if int(row.organization_id) != int(organization_id):
            raise MasterDataError('user_org_mismatch')

        contact_id = getattr(row, 'linked_contact_id', None)
        contact_dto = None
        if contact_id is not None:
            contact_dto = ContactService.get(int(organization_id), int(contact_id))
        return UserContactLinkDTO(
            user_id=int(row.id),
            organization_id=int(organization_id),
            linked_contact_id=int(contact_id) if contact_id is not None else None,
            contact=contact_dto,
        )

    @staticmethod
    def link(user_id: int, organization_id: int, contact_id: int) -> UserContactLinkDTO:
        from app import db
        from models.users import User

        row = User.query.get(int(user_id))
        if row is None:
            raise MasterDataError('user_not_found')
        if int(row.organization_id) != int(organization_id):
            raise MasterDataError('user_org_mismatch')

        contact = ContactService.get(int(organization_id), int(contact_id))
        if contact is None:
            raise MasterDataError('contact_not_found')

        row.linked_contact_id = int(contact_id)
        db.session.commit()
        return UserContactLinkService.get(int(user_id), int(organization_id))

    @staticmethod
    def unlink(user_id: int, organization_id: int) -> UserContactLinkDTO:
        from app import db
        from models.users import User

        row = User.query.get(int(user_id))
        if row is None:
            raise MasterDataError('user_not_found')
        if int(row.organization_id) != int(organization_id):
            raise MasterDataError('user_org_mismatch')

        row.linked_contact_id = None
        db.session.commit()
        return UserContactLinkService.get(int(user_id), int(organization_id))

    @staticmethod
    def backfill_by_email(organization_id: int | None = None) -> int:
        """Vincula usuarios sin enlace cuando email coincide con en1_contact en la misma org."""
        from app import db
        from sqlalchemy import text

        params: dict[str, int] = {}
        org_filter = ''
        if organization_id is not None:
            org_filter = 'AND u.organization_id = :organization_id'
            params['organization_id'] = int(organization_id)

        result = db.session.execute(
            text(
                f"""
                UPDATE "user" u SET linked_contact_id = (
                    SELECT c.id FROM en1_contact c
                    WHERE c.organization_id = u.organization_id
                      AND c.email IS NOT NULL AND length(trim(c.email)) > 0
                      AND u.email IS NOT NULL AND length(trim(u.email)) > 0
                      AND lower(trim(c.email)) = lower(trim(u.email))
                    ORDER BY c.id ASC LIMIT 1
                )
                WHERE u.linked_contact_id IS NULL
                  {org_filter}
                  AND EXISTS (
                      SELECT 1 FROM en1_contact c2
                      WHERE c2.organization_id = u.organization_id
                        AND c2.email IS NOT NULL AND length(trim(c2.email)) > 0
                        AND u.email IS NOT NULL AND length(trim(u.email)) > 0
                        AND lower(trim(c2.email)) = lower(trim(u.email))
                      LIMIT 1
                  )
                """
            ),
            params,
        )
        db.session.commit()
        return int(result.rowcount or 0)
