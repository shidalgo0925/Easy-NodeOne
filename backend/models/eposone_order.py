"""Pedido EPosOne — Hito 3 Order Domain (Spec v1.0 CONGELADA)."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class EposoneOrder(db.Model):
    __tablename__ = 'eposone_order'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, nullable=False, index=True)
    local_number = db.Column(db.String(64), nullable=True)
    en1_number = db.Column(db.String(64), nullable=False, index=True)
    branch_ref = db.Column(db.String(64), nullable=True)
    pos_ref = db.Column(db.String(64), nullable=True)
    register_ref = db.Column(db.String(64), nullable=True)
    owner_device_uuid = db.Column(db.String(64), nullable=False, index=True)
    owner_pos_ref = db.Column(db.String(64), nullable=True)
    user_ref = db.Column(db.String(64), nullable=True)
    customer_ref = db.Column(db.String(64), nullable=True)
    table_ref = db.Column(db.String(64), nullable=True, index=True)
    status = db.Column(db.String(32), nullable=False, default='open')
    payment_status = db.Column(db.String(32), nullable=False, default='unpaid')
    financially_closed = db.Column(db.Boolean, nullable=False, default=False)
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    tax = db.Column(db.Float, nullable=False, default=0.0)
    discount = db.Column(db.Float, nullable=False, default=0.0)
    tip = db.Column(db.Float, nullable=False, default=0.0)
    total = db.Column(db.Float, nullable=False, default=0.0)
    amount_paid = db.Column(db.Float, nullable=False, default=0.0)
    notes = db.Column(db.Text, nullable=True)
    parent_order_id = db.Column(db.Integer, db.ForeignKey('eposone_order.id', ondelete='SET NULL'), nullable=True)
    opened_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship(
        'EposoneOrderItem',
        backref='order',
        lazy='joined',
        cascade='all, delete-orphan',
        order_by='EposoneOrderItem.id',
    )
    payments = db.relationship(
        'EposoneOrderPayment',
        backref='order',
        lazy='select',
        cascade='all, delete-orphan',
        order_by='EposoneOrderPayment.id',
    )
    events = db.relationship(
        'EposoneOrderEvent',
        backref='order',
        lazy='select',
        cascade='all, delete-orphan',
        order_by='EposoneOrderEvent.sequence',
    )

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'en1_number', name='uq_eposone_order_en1_number'),
    )


class EposoneOrderItem(db.Model):
    __tablename__ = 'eposone_order_item'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey('eposone_order.id', ondelete='CASCADE'), nullable=False, index=True
    )
    line_ref = db.Column(db.String(64), nullable=False)
    product_ref = db.Column(db.String(128), nullable=False)
    qty = db.Column(db.Float, nullable=False, default=1.0)
    unit_price = db.Column(db.Float, nullable=False, default=0.0)
    tax = db.Column(db.Float, nullable=False, default=0.0)
    discount = db.Column(db.Float, nullable=False, default=0.0)
    notes = db.Column(db.Text, nullable=True)
    line_status = db.Column(db.String(32), nullable=False, default='pending')


class EposoneOrderPayment(db.Model):
    __tablename__ = 'eposone_order_payment'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey('eposone_order.id', ondelete='CASCADE'), nullable=False, index=True
    )
    payment_ref = db.Column(db.String(64), nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    method = db.Column(db.String(32), nullable=False, default='cash')
    kind = db.Column(db.String(32), nullable=False, default='payment')  # payment|deposit|partial
    currency = db.Column(db.String(8), nullable=False, default='USD')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    payment_method_id = db.Column(
        db.Integer, db.ForeignKey('eposone_payment_method.id', ondelete='SET NULL'), nullable=True, index=True
    )
    reference = db.Column(db.String(128), nullable=True)
    authorization_code = db.Column(db.String(64), nullable=True)
    received_by = db.Column(db.String(64), nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(32), nullable=False, default='captured')
    exchange_rate = db.Column(db.Float, nullable=True)


class EposonePaymentMethod(db.Model):
    """Métodos de pago POS configurables por organización (Order Domain)."""

    __tablename__ = 'eposone_payment_method'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, nullable=False, index=True)
    method_key = db.Column(db.String(40), nullable=False)
    label = db.Column(db.String(120), nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    display_order = db.Column(db.Integer, nullable=False, default=100)
    requires_reference = db.Column(db.Boolean, nullable=False, default=False)
    requires_authorization = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'method_key', name='uq_eposone_payment_method_org_key'),
    )


class EposoneOrderEvent(db.Model):
    __tablename__ = 'eposone_order_event'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey('eposone_order.id', ondelete='CASCADE'), nullable=False, index=True
    )
    organization_id = db.Column(db.Integer, nullable=False, index=True)
    event_id = db.Column(db.String(64), nullable=False)
    type = db.Column(db.String(64), nullable=False)
    sequence = db.Column(db.Integer, nullable=False, default=1)
    occurred_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    actor_user_ref = db.Column(db.String(64), nullable=True)
    actor_device_uuid = db.Column(db.String(64), nullable=True)
    payload_json = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'event_id', name='uq_eposone_order_event_id'),
    )


class EposoneOrderCancellation(db.Model):
    __tablename__ = 'eposone_order_cancellation'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey('eposone_order.id', ondelete='CASCADE'), nullable=False, index=True
    )
    reason = db.Column(db.Text, nullable=False)
    user_ref = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class EposoneOrderReturn(db.Model):
    __tablename__ = 'eposone_order_return'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey('eposone_order.id', ondelete='CASCADE'), nullable=False, index=True
    )
    reason = db.Column(db.Text, nullable=False)
    user_ref = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
