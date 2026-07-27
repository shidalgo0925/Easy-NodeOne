"""Entitlement ETS (ADR-016): capacidad operativa efectiva del tenant sobre un producto.

Producto ≠ Suscripción ≠ Entitlement ≠ Recurso.
Los recursos consumen cupo; nunca poseen derechos.
"""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class EtsProductEntitlement(db.Model):
    """Una fila por suscripción (organization_id + product_code denormalizados)."""

    __tablename__ = 'ets_product_entitlement'

    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(
        db.Integer,
        db.ForeignKey('ets_product_subscription.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        index=True,
    )
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    product_code = db.Column(db.String(64), nullable=False, index=True)
    plan_code = db.Column(db.String(64), nullable=False, default='starter')

    # JSON: cupos por tipo de recurso / features / overrides comerciales
    resource_limits_json = db.Column(db.Text, nullable=True)
    features_json = db.Column(db.Text, nullable=True)
    overrides_json = db.Column(db.Text, nullable=True)

    # trial | active | past_due | grace | suspended | cancelled | expired
    effective_state = db.Column(db.String(32), nullable=False, default='trial', index=True)

    starts_at = db.Column(db.DateTime, nullable=True)
    ends_at = db.Column(db.DateTime, nullable=True)

    updated_by_user_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            'organization_id',
            'product_code',
            name='uq_ets_product_entitlement_org_product',
        ),
        db.Index('ix_ets_ent_org_state', 'organization_id', 'effective_state'),
    )
