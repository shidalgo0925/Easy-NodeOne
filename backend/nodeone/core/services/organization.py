"""OrganizationService — tenant activo (Etapa 11)."""

from __future__ import annotations

from dataclasses import dataclass

from nodeone.core.platform.runtime import resolve_organization_id


@dataclass(frozen=True)
class OrganizationDTO:
    id: int
    name: str
    subdomain: str | None
    is_active: bool

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'subdomain': self.subdomain,
            'is_active': self.is_active,
        }


class OrganizationService:
    @staticmethod
    def resolve_active_id() -> int | None:
        return resolve_organization_id()

    @staticmethod
    def get(organization_id: int) -> OrganizationDTO | None:
        from models.saas import SaasOrganization

        row = SaasOrganization.query.get(int(organization_id))
        if row is None:
            return None
        return OrganizationDTO(
            id=int(row.id),
            name=str(row.name or ''),
            subdomain=(row.subdomain or '').strip() or None,
            is_active=bool(row.is_active),
        )
