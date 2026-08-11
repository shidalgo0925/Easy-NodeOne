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
    # Licenciamiento comercial V1 (por Caja; configurable por admin)
    trial_days_default = db.Column(db.Integer, nullable=False, default=15)
    # on_create | on_activate | on_first_provision
    trial_start_policy = db.Column(db.String(40), nullable=False, default='on_first_provision')
    provisioning_code_ttl_minutes = db.Column(db.Integer, nullable=False, default=30)
    offline_grace_days = db.Column(db.Integer, nullable=False, default=7)
    # ADR-036 — SIMPLE | CHAIN_OF_CUSTODY (default SIMPLE)
    cash_operation_mode = db.Column(db.String(32), nullable=False, default='SIMPLE')
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
