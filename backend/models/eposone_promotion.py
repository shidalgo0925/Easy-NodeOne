"""Modelos promociones POS — EPosOne."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db

PROMO_TYPE_PERCENT = 'percent'
PROMO_TYPE_FIXED = 'fixed'

PROMO_TYPES: frozenset[str] = frozenset({PROMO_TYPE_PERCENT, PROMO_TYPE_FIXED})


class EposonePromotion(db.Model):
    __tablename__ = 'eposone_promotion'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    promo_ref = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    promo_type = db.Column(db.String(32), nullable=False, default=PROMO_TYPE_PERCENT)
    value = db.Column(db.Float, nullable=False, default=0.0)
    code = db.Column(db.String(64), nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'promo_ref', name='uq_eposone_promotion_ref'),
        db.UniqueConstraint('organization_id', 'code', name='uq_eposone_promotion_code'),
    )
