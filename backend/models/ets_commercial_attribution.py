"""Atribución comercial ETS (canal / fuente / campaña / UTM / asesor)."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class EtsCommercialAttribution(db.Model):
    """Origen comercial del cliente — una fila por customer (expediente)."""

    __tablename__ = 'ets_commercial_attribution'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    customer_id = db.Column(
        db.Integer,
        db.ForeignKey('ets_commercial_customer.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        index=True,
    )
    contract_id = db.Column(db.Integer, nullable=True, index=True)

    # Canal: web | presencial | whatsapp | llamada | referido | campana | vendedor
    channel = db.Column(db.String(64), nullable=False, default='web', index=True)
    # Fuente detallada: Instagram, Google, referido por X, visita, etc.
    source_detail = db.Column(db.String(200), nullable=True)
    campaign = db.Column(db.String(200), nullable=True)
    referral_code = db.Column(db.String(64), nullable=True, index=True)
    advisor_user_id = db.Column(db.Integer, nullable=True, index=True)

    utm_source = db.Column(db.String(120), nullable=True)
    utm_medium = db.Column(db.String(120), nullable=True)
    utm_campaign = db.Column(db.String(120), nullable=True)
    utm_content = db.Column(db.String(120), nullable=True)
    utm_term = db.Column(db.String(120), nullable=True)
    landing_url = db.Column(db.String(500), nullable=True)
    attributed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
