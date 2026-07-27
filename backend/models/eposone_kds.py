"""Modelos KDS — Etapa 15 (EPosOne)."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db

KDS_STATION_KITCHEN = 'kitchen'
KDS_STATION_BAR = 'bar'
KDS_STATION_RUNNER = 'runner'

KDS_TICKET_PENDING = 'pending'
KDS_TICKET_PREPARING = 'preparing'
KDS_TICKET_READY = 'ready'
KDS_TICKET_SERVED = 'served'
KDS_TICKET_CANCELLED = 'cancelled'


class EposoneKdsStation(db.Model):
    __tablename__ = 'eposone_kds_station'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    station_ref = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    station_type = db.Column(db.String(32), nullable=False, default=KDS_STATION_KITCHEN)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'station_ref', name='uq_eposone_kds_station_ref'),
    )


class EposoneKdsTicket(db.Model):
    __tablename__ = 'eposone_kds_ticket'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    order_id = db.Column(
        db.Integer, db.ForeignKey('core_commercial_order.id', ondelete='CASCADE'), nullable=False, index=True
    )
    order_ref = db.Column(db.String(50), nullable=False, index=True)
    station_id = db.Column(
        db.Integer, db.ForeignKey('eposone_kds_station.id', ondelete='SET NULL'), nullable=True, index=True
    )
    station_type = db.Column(db.String(32), nullable=False, default=KDS_STATION_KITCHEN)
    status = db.Column(db.String(32), nullable=False, default=KDS_TICKET_PENDING)
    priority = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ready_at = db.Column(db.DateTime, nullable=True)
    served_at = db.Column(db.DateTime, nullable=True)

    station = db.relationship('EposoneKdsStation', backref=db.backref('tickets', lazy='dynamic'))
    lines = db.relationship(
        'EposoneKdsTicketLine',
        backref='ticket',
        lazy='joined',
        cascade='all, delete-orphan',
        order_by='EposoneKdsTicketLine.id',
    )


class EposoneKdsTicketLine(db.Model):
    __tablename__ = 'eposone_kds_ticket_line'

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(
        db.Integer, db.ForeignKey('eposone_kds_ticket.id', ondelete='CASCADE'), nullable=False, index=True
    )
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=1.0)
    status = db.Column(db.String(32), nullable=False, default=KDS_TICKET_PENDING)
