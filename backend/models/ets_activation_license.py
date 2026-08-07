"""Licencia de activación ETS (ADR-035) — orden de activación, no el token."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class EtsActivationLicense(db.Model):
    __tablename__ = 'ets_activation_license'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    contract_id = db.Column(db.Integer, nullable=True, index=True)
    subscription_id = db.Column(db.Integer, nullable=True, index=True)
    product_code = db.Column(db.String(64), nullable=False, default='eposone', index=True)
    # standalone | connected
    modality = db.Column(db.String(32), nullable=False)
    # self_serve | assisted
    implementation_strategy = db.Column(db.String(32), nullable=False)
    # issued | active | suspended | revoked | expired | renewed
    status = db.Column(db.String(32), nullable=False, default='issued', index=True)
    starts_at = db.Column(db.DateTime, nullable=True)
    ends_at = db.Column(db.DateTime, nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)
    created_by_user_id = db.Column(db.Integer, nullable=True)
    revoked_at = db.Column(db.DateTime, nullable=True)
    revoke_reason = db.Column(db.String(200), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
