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
    contact_id = db.Column(
        db.Integer,
        db.ForeignKey('en1_contact.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    customer_contact_id = db.Column(
        db.Integer,
        db.ForeignKey('tenant_crm_contact.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    salesperson_contact_id = db.Column(
        db.Integer,
        db.ForeignKey('tenant_crm_contact.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    salesperson_user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
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
    # Origen: manual | xls (la FE no depende de esto; sigue el pipeline de cotización).
    source = db.Column(db.String(20), nullable=False, default='manual')
    import_profile = db.Column(db.String(64), nullable=True)
    import_profile_version = db.Column(db.Integer, nullable=True)
    import_filename = db.Column(db.String(255), nullable=True)
    import_file_hash = db.Column(db.String(64), nullable=True, index=True)
    import_external_ref = db.Column(db.String(80), nullable=True)

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


class SalesXlsImport(db.Model):
    """Auditoría de importación XLS → cotización. No emite FE."""

    __tablename__ = 'sales_xls_import'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_path = db.Column(db.String(500), nullable=True)
    file_hash = db.Column(db.String(64), nullable=False, index=True)
    import_profile = db.Column(db.String(64), nullable=False)
    import_profile_version = db.Column(db.Integer, nullable=False, default=1)
    external_reference = db.Column(db.String(80), nullable=True, index=True)
    status = db.Column(db.String(20), nullable=False, default='analyzed', index=True)
    warnings_json = db.Column(db.Text, nullable=True)
    errors_json = db.Column(db.Text, nullable=True)
    parser_payload_json = db.Column(db.Text, nullable=True)
    totals_json = db.Column(db.Text, nullable=True)
    quotation_id = db.Column(
        db.Integer,
        db.ForeignKey('quotations.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    committed_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'file_hash', name='uq_sales_xls_import_org_hash'),
    )

