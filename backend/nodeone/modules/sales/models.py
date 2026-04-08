from datetime import datetime

from nodeone.core.db import db


class Quotation(db.Model):
    __tablename__ = 'quotations'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    number = db.Column(db.String(50), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='RESTRICT'), nullable=False, index=True)
    crm_lead_id = db.Column(db.Integer, db.ForeignKey('crm_lead.id', ondelete='SET NULL'), index=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    validity_date = db.Column(db.DateTime)
    payment_terms = db.Column(db.String(200), nullable=True)
    status = db.Column(
        db.String(20),
        nullable=False,
        default='draft',
    )  # draft|sent|confirmed|invoiced|paid|cancelled
    total = db.Column(db.Float, nullable=False, default=0.0)
    tax_total = db.Column(db.Float, nullable=False, default=0.0)
    grand_total = db.Column(db.Float, nullable=False, default=0.0)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'number', name='uq_quotations_org_number'),
    )


class QuotationLine(db.Model):
    __tablename__ = 'quotation_lines'

    id = db.Column(db.Integer, primary_key=True)
    quotation_id = db.Column(
        db.Integer,
        db.ForeignKey('quotations.id', ondelete='CASCADE'),
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

