"""DTOs modelo maestro Core — Etapa 10b."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class OrgUnitDTO:
    id: int
    organization_id: int
    unit_ref: str
    name: str
    unit_type: str
    status: str
    parent_id: int | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'unit_ref': self.unit_ref,
            'name': self.name,
            'unit_type': self.unit_type,
            'status': self.status,
            'parent_id': self.parent_id,
            'notes': self.notes,
        }
