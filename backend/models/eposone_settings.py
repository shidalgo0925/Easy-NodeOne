"""Configuración operativa EPosOne por organización."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class EposoneSettings(db.Model):
    __tablename__ = 'eposone_settings'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, unique=True, index=True
    )
    default_currency = db.Column(db.String(3), nullable=False, default='USD')
    kds_auto_enqueue = db.Column(db.Boolean, nullable=False, default=True)
    delivery_auto_create = db.Column(db.Boolean, nullable=False, default=True)
    fiscal_on_payment = db.Column(db.Boolean, nullable=False, default=False)
    supervisor_approval_required = db.Column(db.Boolean, nullable=False, default=True)
    # Hito EN1-01 — código de emparejamiento tablet ↔ org
    provisioning_code = db.Column(db.String(64), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
