"""Catálogo de eventos, reglas, preferencias por usuario y log del motor unificado de comunicaciones."""

from datetime import datetime

from nodeone.core.db import db


class CommunicationEvent(db.Model):
    """Catálogo estable de eventos (códigos que disparan reglas)."""

    __tablename__ = 'communication_event'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=True)  # transactional, marketing, system
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    rules = db.relationship('CommunicationRule', backref='event', lazy='dynamic')


class CommunicationRule(db.Model):
    """
    Regla por evento, canal y ámbito (organización).
    organization_id NULL = aplica a todos los tenants (plantilla global).
    """

    __tablename__ = 'communication_rule'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(
        db.Integer,
        db.ForeignKey('communication_event.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=True,
        index=True,
    )
    channel = db.Column(db.String(20), nullable=False)  # email, in_app, sms
    marketing_template_id = db.Column(
        db.Integer,
        db.ForeignKey('marketing_email_templates.id', ondelete='SET NULL'),
        nullable=True,
    )
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    delay_minutes = db.Column(db.Integer, nullable=False, default=0)
    is_marketing = db.Column(db.Boolean, nullable=False, default=False)
    respect_user_prefs = db.Column(db.Boolean, nullable=False, default=True)
    priority = db.Column(db.Integer, nullable=False, default=10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    marketing_template = db.relationship('MarketingTemplate', foreign_keys=[marketing_template_id])


class UserCommunicationPreference(db.Model):
    """Preferencia explícita del usuario por evento y canal (ausencia = permitir por defecto)."""

    __tablename__ = 'user_communication_preference'

    __table_args__ = (
        db.UniqueConstraint('user_id', 'event_id', 'channel', name='uq_user_comm_pref_event_channel'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    event_id = db.Column(
        db.Integer,
        db.ForeignKey('communication_event.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    channel = db.Column(db.String(20), nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('communication_preferences', lazy='dynamic'))


class CommunicationLog(db.Model):
    """Auditoría de evaluaciones y envíos del motor."""

    __tablename__ = 'communication_log'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    event_id = db.Column(
        db.Integer,
        db.ForeignKey('communication_event.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    rule_id = db.Column(
        db.Integer,
        db.ForeignKey('communication_rule.id', ondelete='SET NULL'),
        nullable=True,
    )
    channel = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(32), nullable=False)  # skipped_*, pending, executed, failed
    message = db.Column(db.Text, nullable=True)
    context_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    sent_at = db.Column(db.DateTime, nullable=True)
