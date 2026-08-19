"""Sesión de toma física de inventario (EP1 Connected). Stock sigue en core_stock_*."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


COUNT_STATUS_DRAFT = 'DRAFT'
COUNT_STATUS_COUNTING = 'COUNTING'
COUNT_STATUS_COMPLETED = 'COMPLETED'
COUNT_STATUS_APPROVED = 'APPROVED'
COUNT_STATUS_CANCELLED = 'CANCELLED'
COUNT_STATUSES = frozenset(
    {
        COUNT_STATUS_DRAFT,
        COUNT_STATUS_COUNTING,
        COUNT_STATUS_COMPLETED,
        COUNT_STATUS_APPROVED,
        COUNT_STATUS_CANCELLED,
    }
)

COUNT_MODE_BLIND = 'BLIND'
COUNT_MODES = frozenset({COUNT_MODE_BLIND, 'GUIDED'})


class PhysicalInventoryCount(db.Model):
    __tablename__ = 'physical_inventory_count'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    warehouse_org_unit_id = db.Column(
        db.Integer,
        db.ForeignKey('core_org_unit.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    status = db.Column(db.String(24), nullable=False, default=COUNT_STATUS_COUNTING, index=True)
    count_mode = db.Column(db.String(16), nullable=False, default=COUNT_MODE_BLIND)
    client_count_id = db.Column(db.String(80), nullable=True, index=True)
    created_by_user_id = db.Column(db.Integer, nullable=True)
    approved_by_user_id = db.Column(db.Integer, nullable=True)
    source_device_id = db.Column(db.Integer, nullable=True)
    source_system = db.Column(db.String(32), nullable=False, default='EP1')
    notes = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    lines = db.relationship(
        'PhysicalInventoryCountLine',
        backref='count',
        lazy='select',
        cascade='all, delete-orphan',
        order_by='PhysicalInventoryCountLine.id',
    )

    __table_args__ = (
        db.UniqueConstraint(
            'organization_id',
            'client_count_id',
            name='uq_physical_inventory_count_org_client',
        ),
    )


class PhysicalInventoryCountLine(db.Model):
    __tablename__ = 'physical_inventory_count_line'

    id = db.Column(db.Integer, primary_key=True)
    count_id = db.Column(
        db.Integer,
        db.ForeignKey('physical_inventory_count.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    product_id = db.Column(db.Integer, nullable=True)
    product_ref = db.Column(db.String(64), nullable=False, index=True)
    uom = db.Column(db.String(16), nullable=True)
    client_line_id = db.Column(db.String(80), nullable=True)
    snapshot_qty = db.Column(db.Float, nullable=False, default=0.0)
    physical_qty = db.Column(db.Float, nullable=True)
    expected_qty = db.Column(db.Float, nullable=True)
    difference_qty = db.Column(db.Float, nullable=True)
    notes = db.Column(db.String(500), nullable=True)
    counted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('count_id', 'product_ref', name='uq_physical_count_line_product'),
        db.UniqueConstraint('count_id', 'client_line_id', name='uq_physical_count_line_client'),
    )
