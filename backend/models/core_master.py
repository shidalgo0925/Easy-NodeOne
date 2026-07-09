"""Modelos maestro Core — Etapa 10b."""

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
