"""Cola offline y cursores de sincronización — Etapa 13."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db

SYNC_OP_STATUS_PENDING = 'pending'
SYNC_OP_STATUS_APPLIED = 'applied'
SYNC_OP_STATUS_CONFLICT = 'conflict'
SYNC_OP_STATUS_FAILED = 'failed'

SYNC_OP_STATUS_VALUES = frozenset(
    {
        SYNC_OP_STATUS_PENDING,
        SYNC_OP_STATUS_APPLIED,
        SYNC_OP_STATUS_CONFLICT,
        SYNC_OP_STATUS_FAILED,
    }
)


class PlatformSyncOperation(db.Model):
    """Operación de escritura encolada desde cliente offline (idempotente)."""

    __tablename__ = 'platform_sync_operation'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False
    )
    client_id = db.Column(db.String(128), nullable=False, default='default')
    idempotency_key = db.Column(db.String(128), nullable=False)
    operation_type = db.Column(db.String(64), nullable=False)
    entity_type = db.Column(db.String(64), nullable=True)
    entity_ref = db.Column(db.String(128), nullable=True)
    payload = db.Column(db.JSON, nullable=False, default=dict)
    base_version = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(32), nullable=False, default=SYNC_OP_STATUS_PENDING)
    conflict_reason = db.Column(db.Text, nullable=True)
    retry_count = db.Column(db.Integer, nullable=False, default=0)
    next_retry_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    applied_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.UniqueConstraint(
            'organization_id',
            'client_id',
            'idempotency_key',
            name='uq_platform_sync_op_idempotency',
        ),
        db.Index('ix_platform_sync_op_org_status', 'organization_id', 'status'),
    )


class PlatformSyncCursor(db.Model):
    """Cursor incremental por org, cliente y dominio (eventos, catálogo, etc.)."""

    __tablename__ = 'platform_sync_cursor'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False
    )
    client_id = db.Column(db.String(128), nullable=False, default='default')
    domain = db.Column(db.String(64), nullable=False)
    cursor_value = db.Column(db.String(128), nullable=False, default='0')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            'organization_id',
            'client_id',
            'domain',
            name='uq_platform_sync_cursor_domain',
        ),
    )
