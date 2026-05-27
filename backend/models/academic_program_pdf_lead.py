"""Leads capturados desde landing (WordPress/Elementor) para descargar PDF de diplomados.

Flujo: formulario → correo de confirmación → lead confirmado → acceso al PDF.
"""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class AcademicProgramPdfLead(db.Model):
    __tablename__ = 'academic_program_pdf_lead'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )

    program_id = db.Column(
        db.Integer,
        db.ForeignKey('academic_program.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    program_slug = db.Column(db.String(200), nullable=True, index=True)
    crm_lead_id = db.Column(db.Integer, nullable=True, index=True)

    name = db.Column(db.String(255), nullable=False, index=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    phone = db.Column(db.String(80), nullable=False)

    country = db.Column(db.String(120), nullable=True)
    company = db.Column(db.String(255), nullable=True)
    message = db.Column(db.Text, nullable=True)

    source = db.Column(db.String(120), nullable=True, index=True)  # wp_landing_pdf, etc.
    utm_source = db.Column(db.String(120), nullable=True)
    utm_medium = db.Column(db.String(120), nullable=True)
    utm_campaign = db.Column(db.String(120), nullable=True)

    ip_address = db.Column(db.String(64), nullable=True, index=True)
    user_agent = db.Column(db.String(500), nullable=True)

    # pending → confirmed (legacy: new tratado como pending en confirmación)
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)

    confirmation_token = db.Column(db.String(120), nullable=True, index=True)
    confirmation_token_expires = db.Column(db.DateTime, nullable=True)
    confirmation_sent_at = db.Column(db.DateTime, nullable=True)
    email_confirmed_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
