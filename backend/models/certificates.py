"""Modelos ORM (NodeOne)."""
from datetime import datetime, timedelta
import json
import os
import re
import secrets
from flask import has_request_context, url_for
from flask_login import UserMixin, current_user
from sqlalchemy import text as sql_text
from werkzeug.security import generate_password_hash, check_password_hash

from nodeone.core.db import db

# ---------------------------------------------------------------------------
# Módulo Certificados (certificate_events + certificates)
# ---------------------------------------------------------------------------
class CertificateEvent(db.Model):
    """Evento que genera certificados (código de evento)."""
    __tablename__ = 'certificate_events'
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, default=1
    )
    name = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    duration_hours = db.Column(db.Float, nullable=True)
    institution = db.Column(db.String(200))
    convenio = db.Column(db.String(200))
    rector_name = db.Column(db.String(200))
    academic_director_name = db.Column(db.String(200))
    partner_organization = db.Column(db.String(200))  # Ej. Relatic Panamá (pie derecho)
    logo_left_url = db.Column(db.String(500))
    logo_right_url = db.Column(db.String(500))
    seal_url = db.Column(db.String(500))
    background_url = db.Column(db.String(500))  # Fondo del certificado
    membership_required_id = db.Column(db.Integer, db.ForeignKey('membership_plan.id', ondelete='SET NULL'), nullable=True)
    event_required_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='SET NULL'), nullable=True)
    template_html = db.Column(db.Text)
    template_id = db.Column(db.Integer, db.ForeignKey('certificate_templates.id', ondelete='SET NULL'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    verification_enabled = db.Column(db.Boolean, default=True)
    code_prefix = db.Column(db.String(20), default='REL')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    membership_plan = db.relationship('MembershipPlan', backref='certificate_events')
    event_required = db.relationship('Event', foreign_keys=[event_required_id])
    certificate_template = db.relationship('CertificateTemplate', backref='certificate_events', foreign_keys=[template_id])
    certificates = db.relationship('Certificate', backref='certificate_event', lazy=True)


class Certificate(db.Model):
    """Certificado generado para un usuario y un certificate_event."""
    __tablename__ = 'certificates'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    certificate_event_id = db.Column(db.Integer, db.ForeignKey('certificate_events.id', ondelete='CASCADE'), nullable=False)
    certificate_code = db.Column(db.String(80), unique=True, nullable=False)
    verification_hash = db.Column(db.String(64), nullable=True)
    pdf_path = db.Column(db.String(500), nullable=True)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='generated')

    user = db.relationship('User', backref='certificates')
    __table_args__ = (db.UniqueConstraint('user_id', 'certificate_event_id', name='uq_certificate_user_event'),)


class CertificateTemplate(db.Model):
    """Plantilla visual tipo Canva: layout JSON (Fabric.js) para generar certificados PDF."""
    __tablename__ = 'certificate_templates'
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, default=1
    )
    name = db.Column(db.String(200), nullable=False)
    width = db.Column(db.Integer, default=1200)
    height = db.Column(db.Integer, default=900)
    background_image = db.Column(db.String(500), nullable=True)
    json_layout = db.Column(db.Text, nullable=True)  # JSON: canvas + elements (text, image, variable, qr)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

