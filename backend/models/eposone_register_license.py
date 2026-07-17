"""Licencia comercial EPosOne por Caja (unidad de venta).

No confundir con Provisioning (vincula tablet) ni con LicensePolicy (cupos ADR-005).
"""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class EposoneRegisterLicense(db.Model):
    """Estado comercial de una Caja (register_ref) dentro de una organización."""

    __tablename__ = 'eposone_register_license'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    register_ref = db.Column(db.String(64), nullable=False, index=True)

    # trial | subscription | courtesy | promotion | demo | perpetual | suspended
    license_type = db.Column(db.String(32), nullable=False, default='unlicensed')
    # pending | active | expired | suspended | cancelled
    status = db.Column(db.String(32), nullable=False, default='pending')
    plan_code = db.Column(db.String(64), nullable=False, default='eposone')

    starts_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)

    trial_used = db.Column(db.Boolean, nullable=False, default=False)
    trial_started_at = db.Column(db.DateTime, nullable=True)
    trial_expires_at = db.Column(db.DateTime, nullable=True)

    notes = db.Column(db.String(500), nullable=True)
    reason = db.Column(db.String(200), nullable=True)
    activated_by_user_id = db.Column(db.Integer, nullable=True)
    last_validated_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'register_ref', name='uq_eposone_register_license'),
        db.Index('ix_eposone_reg_lic_org_reg', 'organization_id', 'register_ref'),
    )


class EposoneCommercialCode(db.Model):
    """Código de activación/licencia (NO es provisioning)."""

    __tablename__ = 'eposone_commercial_code'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=True, index=True
    )
    code = db.Column(db.String(64), nullable=False, unique=True, index=True)
    # trial | subscription | courtesy | perpetual | extension_days
    benefit_type = db.Column(db.String(32), nullable=False, default='trial')
    duration_days = db.Column(db.Integer, nullable=True)
    max_uses = db.Column(db.Integer, nullable=False, default=1)
    uses_count = db.Column(db.Integer, nullable=False, default=0)
    registers_granted = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(32), nullable=False, default='active')  # active | exhausted | revoked
    expires_at = db.Column(db.DateTime, nullable=True)
    label = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
