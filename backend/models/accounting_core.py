"""Núcleo contable ERP (Fase 1): plan de cuentas, diarios y asientos."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class Account(db.Model):
    __tablename__ = 'account'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    code = db.Column(db.String(32), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(16), nullable=False)  # asset, liability, equity, income, expense
    allow_reconcile = db.Column(db.Boolean, nullable=False, default=False)
    currency_code = db.Column(db.String(16), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'code', name='uq_account_org_code'),
        db.CheckConstraint(
            "type in ('asset','liability','equity','income','expense')",
            name='ck_account_type',
        ),
    )


class Journal(db.Model):
    __tablename__ = 'journal'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(24), nullable=False)
    type = db.Column(db.String(16), nullable=False)  # sale, purchase, bank, cash, general
    default_account_id = db.Column(db.Integer, db.ForeignKey('account.id', ondelete='SET NULL'), nullable=True, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    default_account = db.relationship('Account', foreign_keys=[default_account_id], lazy='joined')

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'code', name='uq_journal_org_code'),
        db.CheckConstraint("type in ('sale','purchase','bank','cash','general')", name='ck_journal_type'),
    )


class JournalEntry(db.Model):
    __tablename__ = 'journal_entry'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    journal_id = db.Column(db.Integer, db.ForeignKey('journal.id', ondelete='RESTRICT'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    reference = db.Column(db.String(120), nullable=True)
    source_model = db.Column(db.String(80), nullable=True)
    source_id = db.Column(db.Integer, nullable=True)
    state = db.Column(db.String(16), nullable=False, default='draft', index=True)  # draft, posted, reversed
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    posted_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    posted_at = db.Column(db.DateTime, nullable=True)
    reversed_by_entry_id = db.Column(
        db.Integer, db.ForeignKey('journal_entry.id', ondelete='SET NULL'), nullable=True, index=True
    )
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    journal = db.relationship('Journal', foreign_keys=[journal_id], lazy='joined')
    items = db.relationship(
        'JournalItem',
        back_populates='entry',
        cascade='all, delete-orphan',
        lazy='dynamic',
    )
    reversed_by_entry = db.relationship('JournalEntry', remote_side=[id], uselist=False)

    __table_args__ = (
        db.CheckConstraint("state in ('draft','posted','reversed')", name='ck_journal_entry_state'),
        db.Index('ix_journal_entry_org_date', 'organization_id', 'date'),
        db.Index('ix_journal_entry_org_state', 'organization_id', 'state'),
        db.Index('ix_journal_entry_org_source', 'organization_id', 'source_model', 'source_id'),
    )


class JournalItem(db.Model):
    __tablename__ = 'journal_item'

    id = db.Column(db.Integer, primary_key=True)
    entry_id = db.Column(db.Integer, db.ForeignKey('journal_entry.id', ondelete='CASCADE'), nullable=False, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id', ondelete='RESTRICT'), nullable=False, index=True)
    partner_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    debit = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    credit = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    description = db.Column(db.String(255), nullable=True)

    entry = db.relationship('JournalEntry', back_populates='items')
    account = db.relationship('Account', lazy='joined')

    __table_args__ = (
        db.CheckConstraint('debit >= 0', name='ck_journal_item_debit_non_negative'),
        db.CheckConstraint('credit >= 0', name='ck_journal_item_credit_non_negative'),
        db.CheckConstraint('NOT (debit > 0 AND credit > 0)', name='ck_journal_item_not_both_sides'),
        db.CheckConstraint('NOT (debit = 0 AND credit = 0)', name='ck_journal_item_not_both_zero'),
    )
