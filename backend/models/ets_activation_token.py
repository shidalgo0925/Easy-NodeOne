"""Token de activación ETS (ADR-035) — credencial canjeable por EP1."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class EtsActivationToken(db.Model):
    __tablename__ = 'ets_activation_token'

    id = db.Column(db.Integer, primary_key=True)
    license_id = db.Column(
        db.Integer,
        db.ForeignKey('ets_activation_license.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    token = db.Column(db.String(64), nullable=False, unique=True, index=True)
    # active | consumed | revoked | expired
    status = db.Column(db.String(32), nullable=False, default='active', index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    max_uses = db.Column(db.Integer, nullable=False, default=1)
    uses_count = db.Column(db.Integer, nullable=False, default=0)
    register_ref = db.Column(db.String(64), nullable=True)
    jti = db.Column(db.String(64), nullable=False, unique=True)
    consumed_at = db.Column(db.DateTime, nullable=True)
    consumed_device_uuid = db.Column(db.String(128), nullable=True)
    revoked_at = db.Column(db.DateTime, nullable=True)
    revoke_reason = db.Column(db.String(200), nullable=True)
    created_by_user_id = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
