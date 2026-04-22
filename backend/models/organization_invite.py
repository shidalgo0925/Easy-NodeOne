"""Invitaciones a una organización (enlace con token)."""
from datetime import datetime

from nodeone.core.db import db


class OrganizationInvite(db.Model):
    __tablename__ = 'organization_invite'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False)
    email = db.Column(db.String(120), nullable=False, index=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    role = db.Column(db.String(50), nullable=False, default='user')
    status = db.Column(db.String(20), nullable=False, default='pending')
    invited_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    accepted_at = db.Column(db.DateTime, nullable=True)
    accepted_user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
