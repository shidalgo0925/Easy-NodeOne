"""Postulaciones / hojas de vida enviadas desde un servicio de catálogo tipo CV_REGISTRATION."""

from datetime import datetime

from app import db


class CvApplication(db.Model):
    __tablename__ = 'cv_application'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    service_id = db.Column(db.Integer, db.ForeignKey('service.id', ondelete='SET NULL'), nullable=True, index=True)
    service = db.relationship('Service', foreign_keys=[service_id])

    salutation = db.Column(db.String(40), nullable=True)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(200), nullable=False)
    birth_date = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(40), nullable=True)

    phone = db.Column(db.String(80), nullable=True)
    email = db.Column(db.String(255), nullable=False, index=True)

    country_residence = db.Column(db.String(120), nullable=True)
    province = db.Column(db.String(120), nullable=True)
    education_level = db.Column(db.String(200), nullable=True)
    other_languages = db.Column(db.Text, nullable=True)
    preferred_sector = db.Column(db.String(200), nullable=True)
    years_experience_sector = db.Column(db.String(80), nullable=True)
    referral_source = db.Column(db.String(300), nullable=True)
    additional_comments = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(32), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
