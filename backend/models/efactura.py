"""Facturación electrónica Panamá (PAC efacturapty y futuros proveedores)."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class ElectronicInvoiceProviderConfig(db.Model):
    __tablename__ = 'electronic_invoice_provider_config'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    provider = db.Column(db.String(40), nullable=False, default='efacturapty')
    environment = db.Column(db.String(20), nullable=False, default='sandbox')
    api_base_url = db.Column(db.String(500), nullable=False, default='https://api.efacturapty.com')
    api_token_encrypted = db.Column(db.Text, nullable=True)
    default_branch = db.Column(db.String(40), nullable=True)
    default_pos = db.Column(db.String(40), nullable=False, default='001')
    default_currency = db.Column(db.String(8), nullable=False, default='USD')
    enabled = db.Column(db.Boolean, nullable=False, default=False)
    emission_mode = db.Column(db.String(20), nullable=False, default='manual')
    emit_on_invoice_confirm = db.Column(db.Boolean, nullable=False, default=False)
    emit_on_payment_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    last_test_status = db.Column(db.String(20), nullable=True)
    last_test_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'provider', name='uq_einv_provider_config_org_provider'),
    )


class ElectronicInvoiceDocument(db.Model):
    __tablename__ = 'electronic_invoice_document'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    invoice_id = db.Column(db.Integer, nullable=True, index=True)
    provider = db.Column(db.String(40), nullable=False, default='efacturapty')
    environment = db.Column(db.String(20), nullable=False, default='sandbox')

    document_type = db.Column(db.String(30), nullable=False, default='invoice')
    internal_reference = db.Column(db.String(120), nullable=True)
    source_model = db.Column(db.String(80), nullable=True, index=True)
    source_id = db.Column(db.Integer, nullable=True, index=True)

    customer_name = db.Column(db.String(300), nullable=True)
    customer_tax_id = db.Column(db.String(80), nullable=True)
    customer_email = db.Column(db.String(255), nullable=True)

    subtotal = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    tax_total = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    discount_total = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    currency = db.Column(db.String(8), nullable=False, default='USD')

    status = db.Column(db.String(30), nullable=False, default='draft', index=True)
    cufe = db.Column(db.String(200), nullable=True, index=True)
    pac_reference = db.Column(db.String(120), nullable=True)
    authorization_message = db.Column(db.Text, nullable=True)

    request_payload = db.Column(db.Text, nullable=True)
    response_payload = db.Column(db.Text, nullable=True)

    pdf_url = db.Column(db.String(500), nullable=True)
    xml_url = db.Column(db.String(500), nullable=True)
    qr_url = db.Column(db.String(500), nullable=True)

    issued_at = db.Column(db.DateTime, nullable=True)
    accepted_at = db.Column(db.DateTime, nullable=True)
    rejected_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)

    error_message = db.Column(db.Text, nullable=True)
    retry_count = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ElectronicInvoiceEventLog(db.Model):
    __tablename__ = 'electronic_invoice_event_log'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    document_id = db.Column(
        db.Integer, db.ForeignKey('electronic_invoice_document.id', ondelete='SET NULL'), nullable=True, index=True
    )
    event_type = db.Column(db.String(40), nullable=False, index=True)
    message = db.Column(db.Text, nullable=True)
    http_status = db.Column(db.Integer, nullable=True)
    request_payload = db.Column(db.Text, nullable=True)
    response_payload = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    document = db.relationship('ElectronicInvoiceDocument', backref=db.backref('event_logs', lazy='dynamic'))
