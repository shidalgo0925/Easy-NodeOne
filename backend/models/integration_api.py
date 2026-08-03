"""API Center — keys y log de consumo (integraciones B2B)."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class IntegrationApiKey(db.Model):
    __tablename__ = 'integration_api_key'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    key_prefix = db.Column(db.String(16), nullable=False)
    key_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    status = db.Column(db.String(20), nullable=False, default='active')  # active | revoked | disabled
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)
    revoked_at = db.Column(db.DateTime, nullable=True)


class IntegrationApiAccessLog(db.Model):
    __tablename__ = 'integration_api_access_log'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, nullable=False, index=True)
    api_key_id = db.Column(
        db.Integer, db.ForeignKey('integration_api_key.id', ondelete='SET NULL'), nullable=True, index=True
    )
    endpoint = db.Column(db.String(200), nullable=False)
    http_status = db.Column(db.Integer, nullable=False)
    result = db.Column(db.String(64), nullable=True)  # found_active | found_inactive | not_found | error | ...
    duration_ms = db.Column(db.Integer, nullable=True)
    client_ip = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
