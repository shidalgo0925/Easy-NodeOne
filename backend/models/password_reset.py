"""Tokens de recuperación de contraseña (hash en BD; un solo uso)."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_token'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True
    )
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ip = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)

    user = db.relationship('User', backref=db.backref('password_reset_tokens', lazy='dynamic'))
