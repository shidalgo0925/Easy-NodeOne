"""ADR-EN1-EP1 — handoff de dinero (mesera → Caja Central) + auditoría de cierre TEST."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class EposoneMoneyHandoff(db.Model):
    __tablename__ = 'eposone_money_handoff'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    client_handoff_id = db.Column(db.String(80), nullable=False)
    cashier_contact_id = db.Column(db.Integer, nullable=True, index=True)
    cashier_name = db.Column(db.String(120), nullable=True)
    shift_id = db.Column(db.Integer, nullable=True, index=True)
    register_ref = db.Column(db.String(64), nullable=True)
    expected_amount = db.Column(db.Float, nullable=False, default=0.0)
    received_amount = db.Column(db.Float, nullable=True)
    difference_amount = db.Column(db.Float, nullable=True)
    other_tender_amount = db.Column(db.Float, nullable=False, default=0.0)
    order_refs_json = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(40), nullable=False, default='PENDING_HANDOFF', index=True)
    received_by_user_id = db.Column(db.Integer, nullable=True)
    received_by_label = db.Column(db.String(160), nullable=True)
    received_at = db.Column(db.DateTime, nullable=True)
    reversed_by_user_id = db.Column(db.Integer, nullable=True)
    reversed_by_label = db.Column(db.String(160), nullable=True)
    reversed_at = db.Column(db.DateTime, nullable=True)
    reverse_reason = db.Column(db.String(400), nullable=True)
    is_test = db.Column(db.Boolean, nullable=False, default=False)
    test_session_id = db.Column(db.String(80), nullable=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'client_handoff_id', name='uq_eposone_money_handoff_client'),
    )


class EposoneOpsAuditEvent(db.Model):
    __tablename__ = 'eposone_ops_audit_event'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    event_type = db.Column(db.String(64), nullable=False, index=True)
    authorized_by_user_id = db.Column(db.Integer, nullable=True)
    authorized_by_label = db.Column(db.String(160), nullable=True)
    payload_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
