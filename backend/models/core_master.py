"""Modelos maestro Core — Etapa 10b/10d/10c."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class CoreOrgUnit(db.Model):
    __tablename__ = 'core_org_unit'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    parent_id = db.Column(db.Integer, db.ForeignKey('core_org_unit.id', ondelete='SET NULL'), nullable=True)
    unit_ref = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    unit_type = db.Column(db.String(32), nullable=False, default='branch')
    status = db.Column(db.String(32), nullable=False, default='active')
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'unit_ref', name='uq_core_org_unit_ref'),
    )


class CoreAddress(db.Model):
    __tablename__ = 'core_address'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    owner_type = db.Column(db.String(32), nullable=False)
    owner_id = db.Column(db.Integer, nullable=False)
    kind = db.Column(db.String(32), nullable=False, default='fiscal')
    line1 = db.Column(db.String(300), nullable=True)
    line2 = db.Column(db.String(300), nullable=True)
    city = db.Column(db.String(120), nullable=True)
    state = db.Column(db.String(120), nullable=True)
    postal_code = db.Column(db.String(32), nullable=True)
    country = db.Column(db.String(8), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class CoreAttachment(db.Model):
    __tablename__ = 'core_attachment'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    mime_type = db.Column(db.String(128), nullable=True)
    storage_path = db.Column(db.String(500), nullable=False)
    checksum = db.Column(db.String(128), nullable=True)
    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class CoreProduct(db.Model):
    __tablename__ = 'core_product'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    product_ref = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=True)
    product_type = db.Column(db.String(32), nullable=False, default='good')
    tracks_inventory = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(32), nullable=False, default='active')
    unit_price = db.Column(db.Float, nullable=False, default=0.0)
    currency = db.Column(db.String(8), nullable=False, default='USD')
    source_app_id = db.Column(db.String(64), nullable=True)
    barcode = db.Column(db.String(64), nullable=True)
    cost_price = db.Column(db.Float, nullable=True)
    min_stock = db.Column(db.Float, nullable=True)
    max_stock = db.Column(db.Float, nullable=True)
    category = db.Column(db.String(120), nullable=True)
    # Categoría fiscal ITBMS: ITBMS_7 | ITBMS_10 | ITBMS_15 | EXENTO
    fiscal_category = db.Column(db.String(32), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    # Inventario: UOM venta; compra + factor (ej. caja → und × pack_factor)
    uom = db.Column(db.String(16), nullable=True, default='und')
    purchase_uom = db.Column(db.String(16), nullable=True)
    pack_factor = db.Column(db.Float, nullable=True, default=1.0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'product_ref', name='uq_core_product_ref'),
    )


class CoreContactLegacyLink(db.Model):
    """Puente lectura dual tenant_crm_contact ↔ en1_contact (Etapa 10c)."""

    __tablename__ = 'core_contact_legacy_link'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    contact_id = db.Column(db.Integer, db.ForeignKey('en1_contact.id', ondelete='CASCADE'), nullable=False)
    legacy_contact_id = db.Column(db.Integer, nullable=False)
    link_source = db.Column(db.String(32), nullable=False, default='manual')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'contact_id', name='uq_core_contact_legacy_canonical'),
        db.UniqueConstraint('organization_id', 'legacy_contact_id', name='uq_core_contact_legacy_legacy'),
    )
