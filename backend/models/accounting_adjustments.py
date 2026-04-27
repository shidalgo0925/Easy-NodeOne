"""Modelos para ajustes contables (tipo Odoo) sobre accounting_core."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class AccountingAdjustment(db.Model):
    __tablename__ = 'accounting_adjustment'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    name = db.Column(db.String(160), nullable=False)
    adjustment_type = db.Column(db.String(32), nullable=False)  # depreciation, provision, reclass, fx, inventory, closing
    adjustment_date = db.Column(db.Date, nullable=False, index=True)
    journal_id = db.Column(db.Integer, db.ForeignKey('journal.id', ondelete='RESTRICT'), nullable=False, index=True)
    debit_account_id = db.Column(db.Integer, db.ForeignKey('account.id', ondelete='RESTRICT'), nullable=False, index=True)
    credit_account_id = db.Column(
        db.Integer, db.ForeignKey('account.id', ondelete='RESTRICT'), nullable=False, index=True
    )
    amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    description = db.Column(db.String(255), nullable=True)
    state = db.Column(db.String(16), nullable=False, default='draft', index=True)  # draft, applied, cancelled
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    applied_entry_id = db.Column(
        db.Integer, db.ForeignKey('journal_entry.id', ondelete='SET NULL'), nullable=True, index=True
    )
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    applied_at = db.Column(db.DateTime, nullable=True)

    journal = db.relationship('Journal', foreign_keys=[journal_id], lazy='joined')
    debit_account = db.relationship('Account', foreign_keys=[debit_account_id], lazy='joined')
    credit_account = db.relationship('Account', foreign_keys=[credit_account_id], lazy='joined')
    applied_entry = db.relationship('JournalEntry', foreign_keys=[applied_entry_id], lazy='joined')

    __table_args__ = (
        db.CheckConstraint('amount > 0', name='ck_accounting_adjustment_amount_positive'),
        db.CheckConstraint("state in ('draft','applied','cancelled')", name='ck_accounting_adjustment_state'),
    )
