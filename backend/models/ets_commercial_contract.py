"""Contrato comercial ETS (ADR-031) — documento comercial principal."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class EtsCommercialContract(db.Model):
    """Contrato entre ETS y el Cliente; la Suscripción cuelga de aquí."""

    __tablename__ = 'ets_commercial_contract'

    id = db.Column(db.Integer, primary_key=True)
    contract_number = db.Column(db.String(64), nullable=False, unique=True, index=True)
    customer_id = db.Column(
        db.Integer,
        db.ForeignKey('ets_commercial_customer.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    product_code = db.Column(db.String(64), nullable=False, index=True)
    plan_code = db.Column(db.String(64), nullable=False)
    # standalone | connected
    modality = db.Column(db.String(32), nullable=False, default='connected')
    # draft | active | suspended | cancelled | expired
    status = db.Column(db.String(32), nullable=False, default='active', index=True)
    starts_at = db.Column(db.DateTime, nullable=True)
    ends_at = db.Column(db.DateTime, nullable=True)
    source = db.Column(db.String(64), nullable=True)

    # Condiciones comerciales acordadas
    agreed_price = db.Column(db.Numeric(12, 2), nullable=True)
    discount_percent = db.Column(db.Numeric(5, 2), nullable=True)
    discount_amount = db.Column(db.Numeric(12, 2), nullable=True)
    currency = db.Column(db.String(8), nullable=True, default='USD')
    # monthly | annual
    billing_period = db.Column(db.String(16), nullable=True)
    # self_serve | assisted
    implementation_mode = db.Column(db.String(32), nullable=True)

    # Evidencia de contrato
    # electronic | paper
    contract_type = db.Column(db.String(16), nullable=True, default='electronic')
    contract_version = db.Column(db.String(32), nullable=True)
    terms_version = db.Column(db.String(32), nullable=True)
    accepted_at = db.Column(db.DateTime, nullable=True)
    accepted_by_user_id = db.Column(db.Integer, nullable=True)
    # CoreAttachment.id (papel) — nullable
    attachment_id = db.Column(db.Integer, nullable=True)

    metadata_json = db.Column(db.Text, nullable=True)
    created_by_user_id = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
