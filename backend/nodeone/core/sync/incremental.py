"""Descarga incremental de eventos — Etapa 13."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from models.platform_events import PlatformDomainEvent


@dataclass(frozen=True)
class SyncEventDTO:
    id: int
    organization_id: int
    event_type: str
    source_app_id: str
    payload: dict[str, Any]
    status: str
    created_at: datetime | None

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'event_type': self.event_type,
            'source_app_id': self.source_app_id,
            'payload': self.payload,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class IncrementalSyncService:
    @staticmethod
    def fetch_events(
        organization_id: int,
        *,
        since_id: int = 0,
        limit: int = 100,
        event_type_prefix: str | None = None,
    ) -> tuple[list[SyncEventDTO], str]:
        """Devuelve eventos con id > since_id y el cursor sugerido (último id)."""
        q = PlatformDomainEvent.query.filter(
            PlatformDomainEvent.organization_id == int(organization_id),
            PlatformDomainEvent.id > int(since_id),
        ).order_by(PlatformDomainEvent.id.asc())
        if event_type_prefix:
            prefix = event_type_prefix.strip()
            q = q.filter(PlatformDomainEvent.event_type.like(f'{prefix}%'))
        rows = q.limit(max(1, min(int(limit), 500))).all()
        items = [
            SyncEventDTO(
                id=int(row.id),
                organization_id=int(row.organization_id),
                event_type=str(row.event_type),
                source_app_id=str(row.source_app_id or 'core'),
                payload=dict(row.payload or {}),
                status=str(row.status or 'pending'),
                created_at=row.created_at,
            )
            for row in rows
        ]
        cursor = str(items[-1].id) if items else str(int(since_id))
        return items, cursor
