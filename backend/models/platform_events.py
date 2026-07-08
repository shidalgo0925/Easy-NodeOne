"""Outbox de eventos de dominio entre apps (Etapa 8 — Plataforma)."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db

EVENT_STATUS_PENDING = 'pending'
EVENT_STATUS_DISPATCHED = 'dispatched'
EVENT_STATUS_FAILED = 'failed'

EVENT_STATUS_VALUES = frozenset(
    {EVENT_STATUS_PENDING, EVENT_STATUS_DISPATCHED, EVENT_STATUS_FAILED}
)


class PlatformDomainEvent(db.Model):
    """Evento de dominio publicado por una app; consumido vía bus (sin sync de tablas)."""

    __tablename__ = 'platform_domain_event'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False
    )
    event_type = db.Column(db.String(128), nullable=False)
    source_app_id = db.Column(db.String(64), nullable=False, default='core')
    payload = db.Column(db.JSON, nullable=False, default=dict)
    status = db.Column(db.String(32), nullable=False, default=EVENT_STATUS_PENDING)
    error_message = db.Column(db.Text, nullable=True)
    retry_count = db.Column(db.Integer, nullable=False, default=0)
    next_retry_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    dispatched_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.Index('ix_platform_domain_event_org_status', 'organization_id', 'status'),
        db.Index('ix_platform_domain_event_type', 'event_type'),
    )
