"""Tablas auxiliares del bridge comercial ESB ↔ EN1."""

from datetime import datetime

from nodeone.core.db import db


class CommercialBridgeIdempotency(db.Model):
    """Idempotency-Key para operaciones de escritura del bridge comercial.

    Persistencia: fila en BD hasta ``expires_at`` (TTL 7 días).
    Tras expirar se puede reutilizar la misma key (se elimina al leer).
    """

    __tablename__ = 'commercial_bridge_idempotency'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, nullable=False, index=True)
    operation = db.Column(db.String(32), nullable=False)  # bootstrap | checkout
    idempotency_key = db.Column(db.String(128), nullable=False)
    request_hash = db.Column(db.String(64), nullable=False)
    response_status = db.Column(db.Integer, nullable=False)
    response_body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    __table_args__ = (
        db.UniqueConstraint(
            'organization_id',
            'operation',
            'idempotency_key',
            name='uq_commercial_bridge_idem_org_op_key',
        ),
    )
