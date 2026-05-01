"""Historial de QR estáticos generados por organización."""
from datetime import datetime

from nodeone.core.db import db


class QrCodeRecord(db.Model):
    __tablename__ = 'qr_codes'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    content = db.Column(db.Text, nullable=False)
    format = db.Column(db.String(8), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    error_level = db.Column(db.String(1), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
