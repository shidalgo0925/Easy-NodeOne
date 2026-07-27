"""Modelos menú digital — Etapa 17 (EPosOne)."""

from __future__ import annotations

import secrets
from datetime import datetime

from nodeone.core.db import db


def _new_public_token() -> str:
    return secrets.token_urlsafe(18)


class EposoneDigitalMenu(db.Model):
    __tablename__ = 'eposone_digital_menu'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    menu_ref = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    public_token = db.Column(db.String(64), nullable=False, default=_new_public_token, index=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    items = db.relationship(
        'EposoneDigitalMenuItem',
        backref='menu',
        lazy='joined',
        cascade='all, delete-orphan',
        order_by='EposoneDigitalMenuItem.sort_order',
    )

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'menu_ref', name='uq_eposone_digital_menu_ref'),
        db.UniqueConstraint('public_token', name='uq_eposone_digital_menu_token'),
    )


class EposoneDigitalMenuItem(db.Model):
    __tablename__ = 'eposone_digital_menu_item'

    id = db.Column(db.Integer, primary_key=True)
    menu_id = db.Column(
        db.Integer, db.ForeignKey('eposone_digital_menu.id', ondelete='CASCADE'), nullable=False, index=True
    )
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    category = db.Column(db.String(120), nullable=True)
    price = db.Column(db.Float, nullable=False, default=0.0)
    available = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
