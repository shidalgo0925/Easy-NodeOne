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

class Policy(db.Model):
    """Políticas institucionales (correo, términos, privacidad, etc.)."""
    __tablename__ = 'policy'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=True)  # HTML
    version = db.Column(db.String(20), default='1.0')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    acceptances = db.relationship('PolicyAcceptance', backref='policy', lazy=True)

    def to_dict(self):
        return {
            'id': self.id, 'title': self.title, 'slug': self.slug, 'content': self.content,
            'version': self.version, 'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class PolicyAcceptance(db.Model):
    """Registro de aceptación de políticas por usuario (respaldo legal)."""
    __tablename__ = 'policy_acceptance'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    policy_id = db.Column(db.Integer, db.ForeignKey('policy.id', ondelete='CASCADE'), nullable=False)
    accepted_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)
    version = db.Column(db.String(20), nullable=True)  # versión aceptada

    user = db.relationship('User', backref=db.backref('policy_acceptances', lazy=True))

    __table_args__ = (db.Index('idx_policy_acceptance_user_policy', 'user_id', 'policy_id'),)

