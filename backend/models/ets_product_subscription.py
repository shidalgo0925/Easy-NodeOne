"""Suscripción ETS: relación comercial organization (tenant) ↔ product_code.

No confundir con Product Registry (catálogo) ni License Engine (operación por caja/dispositivo).
"""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class EtsProductSubscription(db.Model):
    """Una fila vigente por (organization_id, product_code). Historial = cambios de status en la misma fila."""

    __tablename__ = 'ets_product_subscription'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    # Código del Product Registry (eposone, epayroll, …). No copiar metadatos del producto.
    product_code = db.Column(db.String(64), nullable=False, index=True)

    # pending | trial | active | past_due | suspended | cancelled | expired
    status = db.Column(db.String(32), nullable=False, default='pending', index=True)

    starts_at = db.Column(db.DateTime, nullable=True)
    ends_at = db.Column(db.DateTime, nullable=True)
    trial_ends_at = db.Column(db.DateTime, nullable=True)

    reason = db.Column(db.String(200), nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)
    created_by_user_id = db.Column(db.Integer, nullable=True)
    updated_by_user_id = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'product_code', name='uq_ets_product_subscription_org_product'),
        db.Index('ix_ets_sub_org_status', 'organization_id', 'status'),
    )
