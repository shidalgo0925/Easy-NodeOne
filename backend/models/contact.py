"""Maestro de contactos / terceros (tipo res.partner Odoo)."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class Contact(db.Model):
    """
    Sujeto comercial y fiscal por organización.
    No confundir con User (acceso al sistema).
    """

    __tablename__ = 'en1_contact'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )

    contact_type = db.Column(db.String(30), nullable=False, default='person')  # person|company|consumer_final
    display_name = db.Column(db.String(300), nullable=False, index=True)
    first_name = db.Column(db.String(120), nullable=True)
    last_name = db.Column(db.String(120), nullable=True)
    company_name = db.Column(db.String(300), nullable=True)
    commercial_name = db.Column(db.String(300), nullable=True)

    email = db.Column(db.String(255), nullable=True, index=True)
    phone = db.Column(db.String(50), nullable=True)
    mobile = db.Column(db.String(50), nullable=True)

    country = db.Column(db.String(8), nullable=False, default='PA')
    province = db.Column(db.String(120), nullable=True)
    district = db.Column(db.String(120), nullable=True)
    township = db.Column(db.String(120), nullable=True)
    fiscal_address = db.Column(db.Text, nullable=True)

    identification_type = db.Column(db.String(30), nullable=False, default='consumer_final')
    tax_id = db.Column(db.String(80), nullable=True, index=True)
    dv = db.Column(db.String(10), nullable=True)

    is_customer = db.Column(db.Boolean, nullable=False, default=False)
    is_supplier = db.Column(db.Boolean, nullable=False, default=False)
    is_member = db.Column(db.Boolean, nullable=False, default=False)
    is_student = db.Column(db.Boolean, nullable=False, default=False)
    is_participant = db.Column(db.Boolean, nullable=False, default=False)
    is_instructor = db.Column(db.Boolean, nullable=False, default=False)
    is_donor = db.Column(db.Boolean, nullable=False, default=False)
    is_employee = db.Column(db.Boolean, nullable=False, default=False)
    is_tax_exempt = db.Column(db.Boolean, nullable=False, default=False)

    image_url = db.Column(db.String(500), nullable=True)

    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = db.relationship('SaasOrganization', backref=db.backref('contacts', lazy='dynamic'))

    __table_args__ = (
        db.Index('ix_en1_contact_org_display', 'organization_id', 'display_name'),
    )

    def role_labels(self) -> list[str]:
        roles = []
        if self.is_customer:
            roles.append('Cliente')
        if self.is_supplier:
            roles.append('Proveedor')
        if self.is_member:
            roles.append('Miembro')
        if self.is_student:
            roles.append('Estudiante')
        if self.is_participant:
            roles.append('Participante')
        if self.is_instructor:
            roles.append('Instructor')
        if self.is_donor:
            roles.append('Donante')
        if self.is_employee:
            roles.append('Empleado')
        return roles
