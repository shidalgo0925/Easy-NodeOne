"""Modelos del dominio comercial Core — Etapa 14 (EPosOne MVP)."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class CoreCommercialOrder(db.Model):
    __tablename__ = 'core_commercial_order'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    order_ref = db.Column(db.String(50), nullable=False, index=True)
    operational_status = db.Column(db.String(32), nullable=False, default='draft')
    payment_status = db.Column(db.String(32), nullable=False, default='unpaid')
    fiscal_status = db.Column(db.String(32), nullable=False, default='not_required')
    contact_id = db.Column(db.Integer, db.ForeignKey('en1_contact.id', ondelete='SET NULL'), nullable=True)
    currency = db.Column(db.String(8), nullable=False, default='USD')
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    tax_total = db.Column(db.Float, nullable=False, default=0.0)
    grand_total = db.Column(db.Float, nullable=False, default=0.0)
    amount_paid = db.Column(db.Float, nullable=False, default=0.0)
    source_app_id = db.Column(db.String(64), nullable=False, default='eposone')
    notes = db.Column(db.Text, nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    lines = db.relationship(
        'CoreCommercialOrderLine',
        backref='order',
        lazy='joined',
        cascade='all, delete-orphan',
        order_by='CoreCommercialOrderLine.id',
    )

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'order_ref', name='uq_core_commercial_order_ref'),
    )

    @property
    def status(self) -> str:
        """Alias legacy — usar operational_status."""
        return str(self.operational_status or 'draft')

    @status.setter
    def status(self, value: str) -> None:
        self.operational_status = (value or 'draft').strip().lower()

    def sync_payment_status(self) -> str:
        from nodeone.core.commerce.constants import compute_order_payment_status

        ps = compute_order_payment_status(float(self.amount_paid or 0), float(self.grand_total or 0))
        self.payment_status = ps
        return ps

    def maybe_mark_fiscal_pending(self, *, skip_fiscal: bool = False) -> str | None:
        """Dominio 6.8 — default on_paid: fiscal_status pending al cobrar completo."""
        from nodeone.core.commerce.constants import (
            ORDER_FISCAL_STATUS_NOT_REQUIRED,
            ORDER_FISCAL_STATUS_PENDING,
            ORDER_PAYMENT_STATUS_PAID,
        )

        if skip_fiscal:
            return None
        if str(self.payment_status or '') != ORDER_PAYMENT_STATUS_PAID:
            return None
        if str(self.fiscal_status or '') != ORDER_FISCAL_STATUS_NOT_REQUIRED:
            return None
        prev = str(self.fiscal_status)
        self.fiscal_status = ORDER_FISCAL_STATUS_PENDING
        return prev


class CoreCommercialOrderLine(db.Model):
    __tablename__ = 'core_commercial_order_line'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey('core_commercial_order.id', ondelete='CASCADE'), nullable=False, index=True
    )
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=1.0)
    unit_price = db.Column(db.Float, nullable=False, default=0.0)
    line_total = db.Column(db.Float, nullable=False, default=0.0)
    product_ref = db.Column(db.String(128), nullable=True)
    line_status = db.Column(db.String(32), nullable=False, default='pending')


class CoreCommercialPayment(db.Model):
    __tablename__ = 'core_commercial_payment'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    order_id = db.Column(
        db.Integer, db.ForeignKey('core_commercial_order.id', ondelete='CASCADE'), nullable=False, index=True
    )
    payment_ref = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(32), nullable=False, default='captured')
    payment_type = db.Column(db.String(32), nullable=False, default='cash')
    amount = db.Column(db.Float, nullable=False, default=0.0)
    currency = db.Column(db.String(8), nullable=False, default='USD')
    captured_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    cash_shift_id = db.Column(
        db.Integer, db.ForeignKey('core_cash_shift.id', ondelete='SET NULL'), nullable=True, index=True
    )
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    order = db.relationship('CoreCommercialOrder', backref=db.backref('payments', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'payment_ref', name='uq_core_commercial_payment_ref'),
    )


class CoreCashShift(db.Model):
    __tablename__ = 'core_cash_shift'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    register_ref = db.Column(db.String(64), nullable=False, index=True)
    status = db.Column(db.String(32), nullable=False, default='open')
    opening_balance = db.Column(db.Float, nullable=False, default=0.0)
    closing_balance = db.Column(db.Float, nullable=True)
    counted_amount = db.Column(db.Float, nullable=True)
    expected_balance = db.Column(db.Float, nullable=True)
    opened_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)

    movements = db.relationship(
        'CoreCashMovement',
        backref='shift',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )


class CoreCashMovement(db.Model):
    __tablename__ = 'core_cash_movement'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    shift_id = db.Column(
        db.Integer, db.ForeignKey('core_cash_shift.id', ondelete='CASCADE'), nullable=False, index=True
    )
    movement_type = db.Column(db.String(32), nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    payment_id = db.Column(
        db.Integer, db.ForeignKey('core_commercial_payment.id', ondelete='SET NULL'), nullable=True
    )
    notes = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class CorePosTerminal(db.Model):
    __tablename__ = 'core_pos_terminal'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    terminal_ref = db.Column(db.String(64), nullable=False)
    register_ref = db.Column(db.String(64), nullable=True)
    status = db.Column(db.String(32), nullable=False, default='active')
    device_label = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'terminal_ref', name='uq_core_pos_terminal_ref'),
    )
