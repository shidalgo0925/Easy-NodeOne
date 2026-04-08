from datetime import datetime

from nodeone.core.db import db


class Tax(db.Model):
    __tablename__ = 'taxes'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(120), nullable=False)
    percentage = db.Column(db.Float, nullable=False, default=0.0)
    type = db.Column(db.String(20), nullable=False, default='excluded')  # included|excluded (legacy, sincronizado con price_included)
    computation = db.Column(db.String(20), nullable=False, default='percent')  # percent|fixed
    amount_fixed = db.Column(db.Float, nullable=False, default=0.0)
    price_included = db.Column(db.Boolean, nullable=False, default=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'name', name='uq_taxes_org_name'),
    )


class Invoice(db.Model):
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    number = db.Column(db.String(50), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='RESTRICT'), nullable=False, index=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='draft')  # draft|posted|paid|cancelled
    origin_quotation_id = db.Column(db.Integer, db.ForeignKey('quotations.id', ondelete='SET NULL'), index=True)
    total = db.Column(db.Float, nullable=False, default=0.0)
    tax_total = db.Column(db.Float, nullable=False, default=0.0)
    grand_total = db.Column(db.Float, nullable=False, default=0.0)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'number', name='uq_invoices_org_number'),
    )


class InvoiceLine(db.Model):
    __tablename__ = 'invoice_lines'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(
        db.Integer,
        db.ForeignKey('invoices.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    product_id = db.Column(db.Integer, index=True)
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=1.0)
    price_unit = db.Column(db.Float, nullable=False, default=0.0)
    tax_id = db.Column(db.Integer, db.ForeignKey('taxes.id', ondelete='SET NULL'), index=True)
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    total = db.Column(db.Float, nullable=False, default=0.0)

