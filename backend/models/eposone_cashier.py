"""Credencial operativa de cajero EPosOne (la persona vive en en1_contact)."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class EposoneCashierCredential(db.Model):
    __tablename__ = 'eposone_cashier_credential'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    cashier_contact_id = db.Column(
        db.Integer,
        db.ForeignKey('en1_contact.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        index=True,
    )
    pin_verifier = db.Column(db.String(512), nullable=False)
    pin_version = db.Column(db.Integer, nullable=False, default=1)
    pin_updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        db.UniqueConstraint(
            'organization_id',
            'cashier_contact_id',
            name='uq_eposone_cashier_credential_org_contact',
        ),
    )
