"""Cliente comercial ETS (ADR-031) — identidad comercial, no implementación de producto."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class EtsCommercialCustomer(db.Model):
    """Persona natural o jurídica con relación comercial con ETS.

    organization_id = compañía productora ETS (proveedor), no el negocio operativo del cliente.
    Varios clientes pueden compartir la misma org proveedor.
    """

    __tablename__ = 'ets_commercial_customer'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    display_name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False, index=True)
    phone = db.Column(db.String(64), nullable=True)
    country = db.Column(db.String(120), nullable=True)
    # registered | active | suspended | cancelled
    status = db.Column(db.String(32), nullable=False, default='registered', index=True)
    primary_user_id = db.Column(db.Integer, nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.Index('uq_ets_commercial_customer_provider_email', 'organization_id', 'email', unique=True),
    )
