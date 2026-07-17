"""Códigos de provisioning EPosOne — Hito EN1-02 (código = destino operativo)."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class EposoneProvisioningCode(db.Model):
    """Código único que apunta a Empresa + Sucursal + POS + Caja."""

    __tablename__ = 'eposone_provisioning_code'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    branch_ref = db.Column(db.String(64), nullable=False)
    pos_ref = db.Column(db.String(64), nullable=False)
    register_ref = db.Column(db.String(64), nullable=False)
    code = db.Column(db.String(64), nullable=False, unique=True, index=True)
    status = db.Column(db.String(32), nullable=False, default='active')  # active | used | revoked | expired
    label = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.Index('ix_eposone_prov_org_register', 'organization_id', 'register_ref'),
    )
