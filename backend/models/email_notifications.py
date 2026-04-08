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

class EmailTemplate(db.Model):
    """Templates de correo editables desde el panel de administración"""
    __tablename__ = 'email_template'
    __table_args__ = (
        db.UniqueConstraint('organization_id', 'template_key', name='uq_email_template_org_key'),
    )
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        default=1,
    )
    template_key = db.Column(db.String(100), nullable=True)  # welcome, membership_payment, etc.
    name = db.Column(db.String(200), nullable=False)  # Nombre descriptivo
    subject = db.Column(db.String(500), nullable=False)  # Asunto del correo
    html_content = db.Column(db.Text, nullable=False)  # Contenido HTML
    text_content = db.Column(db.Text)  # Contenido de texto plano (opcional)
    category = db.Column(db.String(50))  # membership, event, appointment, system, crm
    is_custom = db.Column(db.Boolean, default=False)  # Si es personalizado o usa el template por defecto
    variables = db.Column(db.Text)  # JSON con variables disponibles para este template
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convertir a diccionario para JSON"""
        return {
            'id': self.id,
            'organization_id': getattr(self, 'organization_id', None),
            'template_key': self.template_key,
            'name': self.name,
            'subject': self.subject,
            'html_content': self.html_content,
            'text_content': self.text_content,
            'category': self.category,
            'is_custom': self.is_custom,
            'variables': self.variables,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def get_template(template_key):
        """Obtener template personalizado o None si usa el por defecto"""
        template = EmailTemplate.query.filter_by(template_key=template_key, is_custom=True).first()
        return template


class NotificationSettings(db.Model):
    """Configuración de notificaciones del sistema - permite activar/desactivar cada tipo"""
    id = db.Column(db.Integer, primary_key=True)
    notification_type = db.Column(db.String(50), unique=True, nullable=False)  # welcome, membership_payment, etc.
    name = db.Column(db.String(200), nullable=False)  # Nombre descriptivo
    description = db.Column(db.Text)  # Descripción de qué hace esta notificación
    enabled = db.Column(db.Boolean, default=True)  # Si está habilitada o no
    category = db.Column(db.String(50))  # membership, event, appointment, system
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convertir a diccionario para JSON"""
        return {
            'id': self.id,
            'notification_type': self.notification_type,
            'name': self.name,
            'description': self.description,
            'enabled': self.enabled,
            'category': self.category,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def is_enabled(notification_type):
        """Verificar si un tipo de notificación está habilitado"""
        setting = NotificationSettings.query.filter_by(notification_type=notification_type).first()
        # Si no existe la configuración, por defecto está habilitada (comportamiento actual)
        return setting.enabled if setting else True
    
    @staticmethod
    def get_all_settings():
        """Obtener todas las configuraciones agrupadas por categoría"""
        settings = NotificationSettings.query.order_by(NotificationSettings.category, NotificationSettings.name).all()
        result = {}
        for setting in settings:
            if setting.category not in result:
                result[setting.category] = []
            result[setting.category].append(setting.to_dict())
        return result


class Office365Request(db.Model):
    """Solicitudes de acceso a Office 365 (estado: pending, approved, rejected)."""
    __tablename__ = 'office365_request'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    purpose = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    admin_notes = db.Column(db.Text, nullable=True)
    discount_code_id = db.Column(db.Integer, db.ForeignKey('discount_code.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('office365_requests', lazy=True))
    discount_code = db.relationship('DiscountCode', foreign_keys=[discount_code_id], backref='office365_requests')

    __table_args__ = (
        db.Index('idx_office365_status', 'status'),
        db.Index('idx_office365_created', 'created_at'),
        db.Index('idx_office365_user', 'user_id'),
    )

