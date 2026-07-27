"""SyncOperationService — cola de escritura offline (Etapa 13)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from models.platform_sync import (
    SYNC_OP_STATUS_APPLIED,
    SYNC_OP_STATUS_CONFLICT,
    SYNC_OP_STATUS_FAILED,
    SYNC_OP_STATUS_PENDING,
    PlatformSyncOperation,
)
from nodeone.core.sync.conflicts import detect_version_conflict
from nodeone.core.sync.retry import compute_next_retry_at, is_ready_for_retry, max_sync_operation_retries


@dataclass(frozen=True)
class SyncOperationDTO:
    id: int
    organization_id: int
    client_id: str
    idempotency_key: str
    operation_type: str
    status: str
    entity_type: str | None
    entity_ref: str | None
    payload: dict[str, Any]
    base_version: int | None
    retry_count: int
    conflict_reason: str | None
    created_at: datetime | None
    applied_at: datetime | None

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'client_id': self.client_id,
            'idempotency_key': self.idempotency_key,
            'operation_type': self.operation_type,
            'status': self.status,
            'entity_type': self.entity_type,
            'entity_ref': self.entity_ref,
            'payload': self.payload,
            'base_version': self.base_version,
            'retry_count': self.retry_count,
            'conflict_reason': self.conflict_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
        }


def _to_dto(row: PlatformSyncOperation) -> SyncOperationDTO:
    return SyncOperationDTO(
        id=int(row.id),
        organization_id=int(row.organization_id),
        client_id=str(row.client_id),
        idempotency_key=str(row.idempotency_key),
        operation_type=str(row.operation_type),
        status=str(row.status),
        entity_type=(row.entity_type or None),
        entity_ref=(row.entity_ref or None),
        payload=dict(row.payload or {}),
        base_version=int(row.base_version) if row.base_version is not None else None,
        retry_count=int(row.retry_count or 0),
        conflict_reason=(row.conflict_reason or None),
        created_at=row.created_at,
        applied_at=row.applied_at,
    )


class SyncOperationService:
    @staticmethod
    def enqueue(
        organization_id: int,
        *,
        idempotency_key: str,
        operation_type: str,
        payload: dict[str, Any] | None = None,
        client_id: str = 'default',
        entity_type: str | None = None,
        entity_ref: str | None = None,
        base_version: int | None = None,
    ) -> SyncOperationDTO:
        from app import db

        key = (idempotency_key or '').strip()
        if not key:
            raise ValueError('idempotency_key vacío')
        op = (operation_type or '').strip()
        if not op:
            raise ValueError('operation_type vacío')
        cid = (client_id or 'default').strip() or 'default'

        existing = PlatformSyncOperation.query.filter_by(
            organization_id=int(organization_id),
            client_id=cid,
            idempotency_key=key,
        ).first()
        if existing is not None:
            return _to_dto(existing)

        row = PlatformSyncOperation(
            organization_id=int(organization_id),
            client_id=cid,
            idempotency_key=key,
            operation_type=op,
            entity_type=(entity_type or None),
            entity_ref=(entity_ref or None),
            payload=dict(payload or {}),
            base_version=int(base_version) if base_version is not None else None,
            status=SYNC_OP_STATUS_PENDING,
        )
        db.session.add(row)
        db.session.commit()
        return _to_dto(row)

    @staticmethod
    def get(organization_id: int, operation_id: int) -> SyncOperationDTO | None:
        row = PlatformSyncOperation.query.filter_by(
            organization_id=int(organization_id),
            id=int(operation_id),
        ).first()
        return _to_dto(row) if row is not None else None

    @staticmethod
    def process_pending(
        *,
        limit: int = 50,
        organization_id: int | None = None,
        handler: Callable[[SyncOperationDTO], None] | None = None,
    ) -> int:
        """
        Procesa operaciones pendientes listas para reintento.
        ``handler(op_dto)`` debe aplicar la operación o lanzar excepción.
        Sin handler: no-op (solo reservado para worker Etapa 14).
        """
        from datetime import datetime

        from app import db

        q = PlatformSyncOperation.query.filter_by(status=SYNC_OP_STATUS_PENDING).order_by(
            PlatformSyncOperation.id.asc()
        )
        if organization_id is not None:
            q = q.filter_by(organization_id=int(organization_id))
        rows = q.limit(max(1, int(limit))).all()
        processed = 0
        for row in rows:
            if not is_ready_for_retry(row.next_retry_at):
                continue
            dto = _to_dto(row)
            conflict = detect_version_conflict(
                base_version=dto.base_version,
                server_version=(dto.payload or {}).get('_server_version'),
            )
            if conflict:
                row.status = SYNC_OP_STATUS_CONFLICT
                row.conflict_reason = conflict
                db.session.commit()
                continue
            if handler is None:
                continue
            try:
                handler(dto)
                row.status = SYNC_OP_STATUS_APPLIED
                row.applied_at = datetime.utcnow()
                row.error_message = None
                db.session.commit()
                processed += 1
            except Exception as exc:
                row.retry_count = int(row.retry_count or 0) + 1
                if row.retry_count >= max_sync_operation_retries():
                    row.status = SYNC_OP_STATUS_FAILED
                else:
                    row.status = SYNC_OP_STATUS_PENDING
                    row.next_retry_at = compute_next_retry_at(row.retry_count)
                row.error_message = str(exc)[:2000]
                db.session.commit()
        return processed
