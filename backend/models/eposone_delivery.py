"""Modelos Delivery — Etapa 16 (EPosOne)."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db

DELIVERY_STATUS_PENDING = 'pending'
DELIVERY_STATUS_ASSIGNED = 'assigned'
DELIVERY_STATUS_IN_TRANSIT = 'in_transit'
DELIVERY_STATUS_DELIVERED = 'delivered'
DELIVERY_STATUS_CANCELLED = 'cancelled'

DELIVERY_TRANSITIONS: dict[str, frozenset[str]] = {
    DELIVERY_STATUS_PENDING: frozenset({DELIVERY_STATUS_ASSIGNED, DELIVERY_STATUS_CANCELLED}),
    DELIVERY_STATUS_ASSIGNED: frozenset({DELIVERY_STATUS_IN_TRANSIT, DELIVERY_STATUS_CANCELLED}),
    DELIVERY_STATUS_IN_TRANSIT: frozenset({DELIVERY_STATUS_DELIVERED, DELIVERY_STATUS_CANCELLED}),
    DELIVERY_STATUS_DELIVERED: frozenset(),
    DELIVERY_STATUS_CANCELLED: frozenset(),
}


class EposoneDelivery(db.Model):
    __tablename__ = 'eposone_delivery'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    order_id = db.Column(
        db.Integer, db.ForeignKey('core_commercial_order.id', ondelete='CASCADE'), nullable=False, index=True
    )
    order_ref = db.Column(db.String(50), nullable=False, index=True)
    status = db.Column(db.String(32), nullable=False, default=DELIVERY_STATUS_PENDING)
    driver_name = db.Column(db.String(200), nullable=True)
    driver_contact_id = db.Column(db.Integer, db.ForeignKey('en1_contact.id', ondelete='SET NULL'), nullable=True)
    destination_address = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    total_qty = db.Column(db.Float, nullable=False, default=0.0)
    delivered_qty = db.Column(db.Float, nullable=False, default=0.0)
    assigned_at = db.Column(db.DateTime, nullable=True)
    delivered_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'order_id', name='uq_eposone_delivery_order'),
    )
