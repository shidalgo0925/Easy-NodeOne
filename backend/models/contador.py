"""Módulo Contador: inventario físico por plantilla/variante (sin ventas ni stock formal)."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class ContadorProductTemplate(db.Model):
    __tablename__ = 'contador_product_template'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    name = db.Column(db.String(300), nullable=False)
    name_normalized = db.Column(db.String(320), nullable=False, index=True)
    category = db.Column(db.String(120), nullable=False, default='')
    subcategory = db.Column(db.String(120), nullable=False, default='')
    product_class = db.Column(db.String(80), nullable=False, default='')
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    variants = db.relationship(
        'ContadorProductVariant', backref='template', lazy='dynamic', cascade='all, delete-orphan'
    )

    __table_args__ = (
        db.UniqueConstraint(
            'organization_id',
            'category',
            'subcategory',
            'product_class',
            'name_normalized',
            name='uq_contador_template_org_dims',
        ),
    )


class ContadorProductVariant(db.Model):
    __tablename__ = 'contador_product_variant'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    template_id = db.Column(
        db.Integer, db.ForeignKey('contador_product_template.id', ondelete='CASCADE'), nullable=False, index=True
    )
    attribute_name = db.Column(db.String(80), nullable=False, default='PRESENTACIÓN')
    attribute_value = db.Column(db.String(200), nullable=False)
    attribute_value_normalized = db.Column(db.String(220), nullable=False, index=True)
    display_name = db.Column(db.String(400), nullable=False)
    code = db.Column(db.String(40), nullable=False, index=True)
    barcode = db.Column(db.String(80), nullable=True, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            'template_id',
            'attribute_value_normalized',
            name='uq_contador_variant_tpl_attr',
        ),
        db.UniqueConstraint(
            'organization_id',
            'code',
            name='uq_contador_variant_org_code',
        ),
    )


class ContadorSession(db.Model):
    __tablename__ = 'contador_session'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='draft', index=True)
    source_filename = db.Column(db.String(255), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    opened_at = db.Column(db.DateTime, nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)

    lines = db.relationship(
        'ContadorCountLine', backref='session', lazy='dynamic', cascade='all, delete-orphan'
    )


class ContadorCountLine(db.Model):
    __tablename__ = 'contador_count_line'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    session_id = db.Column(
        db.Integer, db.ForeignKey('contador_session.id', ondelete='CASCADE'), nullable=False, index=True
    )
    variant_id = db.Column(
        db.Integer, db.ForeignKey('contador_product_variant.id', ondelete='CASCADE'), nullable=False, index=True
    )
    counted_qty = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)
    counted_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    counted_at = db.Column(db.DateTime, nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    variant = db.relationship('ContadorProductVariant', lazy='joined')

    __table_args__ = (
        db.UniqueConstraint('session_id', 'variant_id', name='uq_contador_line_sess_var'),
    )


class ContadorCaptureLog(db.Model):
    __tablename__ = 'contador_capture_log'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    session_id = db.Column(
        db.Integer, db.ForeignKey('contador_session.id', ondelete='CASCADE'), nullable=False, index=True
    )
    line_id = db.Column(
        db.Integer, db.ForeignKey('contador_count_line.id', ondelete='CASCADE'), nullable=False, index=True
    )
    variant_id = db.Column(
        db.Integer, db.ForeignKey('contador_product_variant.id', ondelete='CASCADE'), nullable=False, index=True
    )
    old_qty = db.Column(db.Float, nullable=True)
    new_qty = db.Column(db.Float, nullable=True)
    action = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class ContadorExportLog(db.Model):
    __tablename__ = 'contador_export_log'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    session_id = db.Column(
        db.Integer, db.ForeignKey('contador_session.id', ondelete='CASCADE'), nullable=False, index=True
    )
    export_type = db.Column(db.String(20), nullable=False)
    filename = db.Column(db.String(255), nullable=True)
    target_name = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='ok')
    message = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
