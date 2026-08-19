"""Preferencias regionales y de presentación por organización (no fiscal)."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class OrganizationRegionalSettings(db.Model):
    __tablename__ = 'organization_regional_settings'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        index=True,
    )
    country_code = db.Column(db.String(8), nullable=True)
    timezone = db.Column(db.String(64), nullable=False, default='America/Panama')
    date_format = db.Column(db.String(16), nullable=False, default='DD/MM/YYYY')
    time_format = db.Column(db.String(8), nullable=False, default='24h')
    week_start = db.Column(db.String(8), nullable=False, default='monday')
    number_format = db.Column(db.String(16), nullable=False, default='1,234.56')
    money_decimals = db.Column(db.Integer, nullable=False, default=2)
    qty_decimals = db.Column(db.Integer, nullable=False, default=2)
    currency_code = db.Column(db.String(8), nullable=False, default='USD')
    currency_symbol = db.Column(db.String(16), nullable=False, default='$')
    symbol_position = db.Column(db.String(8), nullable=False, default='before')
    locale = db.Column(db.String(16), nullable=False, default='es')
    paper_size = db.Column(db.String(16), nullable=False, default='a4')
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
