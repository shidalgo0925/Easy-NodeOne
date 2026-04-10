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

class Notification(db.Model):
    """Sistema de notificaciones para eventos y movimientos del sistema"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=True)  # NULL si no es relacionado a evento
    notification_type = db.Column(db.String(50), nullable=False)  # event_registration, event_cancellation, event_confirmation, event_update, etc.
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    email_sent = db.Column(db.Boolean, default=False)
    email_sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    user = db.relationship('User', backref='notifications')
    event = db.relationship('Event', backref='notifications')
    
    def mark_as_read(self):
        """Marcar notificación como leída"""
        self.is_read = True
        # Commit removido - se hace en el endpoint


class EmailLog(db.Model):
    """Registro completo de todos los emails enviados por el sistema"""
    id = db.Column(db.Integer, primary_key=True)
    from_email = db.Column(db.String(200))  # Email del remitente
    to_email = db.Column(db.String(120), nullable=False)  # Email del destinatario (campo legacy, sinónimo de recipient_email)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # NULL si es email externo
    recipient_email = db.Column(db.String(120), nullable=False)  # Email del destinatario
    recipient_name = db.Column(db.String(200))  # Nombre del destinatario
    subject = db.Column(db.String(500), nullable=False)
    html_content = db.Column(db.Text)  # Contenido HTML del email
    text_content = db.Column(db.Text)  # Contenido de texto plano
    email_type = db.Column(db.String(50), nullable=False)  # membership_payment, event_registration, appointment_confirmation, etc.
    related_entity_type = db.Column(db.String(50))  # membership, event, appointment, payment, etc.
    related_entity_id = db.Column(db.Integer)  # ID de la entidad relacionada
    status = db.Column(db.String(20), default='sent')  # sent, failed, pending
    error_message = db.Column(db.Text)  # Mensaje de error si falló
    retry_count = db.Column(db.Integer, default=0)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    recipient = db.relationship('User', backref='email_logs', foreign_keys=[recipient_id])
    
    def to_dict(self):
        """Convertir a diccionario para JSON"""
        return {
            'id': self.id,
            'recipient_email': self.recipient_email,
            'recipient_name': self.recipient_name,
            'subject': self.subject,
            'email_type': self.email_type,
            'related_entity_type': self.related_entity_type,
            'related_entity_id': self.related_entity_id,
            'status': self.status,
            'retry_count': self.retry_count,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class EmailConfig(db.Model):
    """Configuración del servidor de correo SMTP"""
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    mail_server = db.Column(db.String(200), nullable=False, default='smtp.gmail.com')
    mail_port = db.Column(db.Integer, nullable=False, default=587)
    mail_use_tls = db.Column(db.Boolean, default=True)
    mail_use_ssl = db.Column(db.Boolean, default=False)
    mail_username = db.Column(db.String(200))  # Se puede dejar vacío si se usa variable de entorno
    mail_password = db.Column(db.String(500))  # Encriptado o en variable de entorno
    mail_default_sender = db.Column(db.String(200), nullable=False, default='noreply@example.com')
    use_environment_variables = db.Column(db.Boolean, default=True)  # Si usa vars de entorno o BD
    is_active = db.Column(db.Boolean, default=True)
    use_for_marketing = db.Column(db.Boolean, default=False)  # Usar esta config para envíos masivos (campañas)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def get_active_config(organization_id=None, allow_fallback_to_default_org=True):
        """
        Configuración SMTP activa.
        - Sin organization_id: primera fila activa (arranque / legado).
        - Con organization_id y allow_fallback_to_default_org=False: solo ese tenant.
        """
        q_active = EmailConfig.query.filter_by(is_active=True)
        if organization_id is None:
            return q_active.order_by(EmailConfig.id.asc()).first()
        oid = int(organization_id)
        row = q_active.filter_by(organization_id=oid).order_by(EmailConfig.id.asc()).first()
        if row is not None:
            return row
        if not allow_fallback_to_default_org:
            return None
        try:
            from utils.organization import default_organization_id

            def_oid = int(default_organization_id())
        except Exception:
            def_oid = None
        if def_oid is not None:
            row = q_active.filter_by(organization_id=def_oid).order_by(EmailConfig.id.asc()).first()
            if row is not None:
                return row
        return (
            q_active.filter(EmailConfig.organization_id.is_(None)).order_by(EmailConfig.id.asc()).first()
        )

    @staticmethod
    def get_marketing_config(organization_id=None, allow_fallback_to_default_org=True):
        """
        SMTP para campañas: fila use_for_marketing del tenant; si no hay, misma lógica que get_active_config.
        organization_id=None conserva el comportamiento global (legado).
        """
        if organization_id is None:
            cfg = (
                EmailConfig.query.filter_by(use_for_marketing=True, is_active=True)
                .order_by(EmailConfig.id.asc())
                .first()
            )
            return cfg or EmailConfig.get_active_config()
        oid = int(organization_id)
        cfg = (
            EmailConfig.query.filter_by(
                use_for_marketing=True, is_active=True, organization_id=oid
            )
            .order_by(EmailConfig.id.asc())
            .first()
        )
        if cfg:
            return cfg
        return EmailConfig.get_active_config(
            organization_id=oid, allow_fallback_to_default_org=allow_fallback_to_default_org
        )

    def to_dict(self):
        """Convertir a diccionario para JSON (sin password)"""
        return {
            'id': self.id,
            'organization_id': getattr(self, 'organization_id', None),
            'mail_server': self.mail_server,
            'mail_port': self.mail_port,
            'mail_use_tls': self.mail_use_tls,
            'mail_use_ssl': self.mail_use_ssl,
            'mail_username': self.mail_username if not self.use_environment_variables else '[Desde variables de entorno]',
            'mail_default_sender': self.mail_default_sender,
            'use_environment_variables': self.use_environment_variables,
            'is_active': self.is_active,
            'use_for_marketing': getattr(self, 'use_for_marketing', False),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def apply_to_app(self, app_instance):
        """Aplicar esta configuración a la instancia de Flask"""
        if self.use_environment_variables:
            # Usar variables de entorno si está configurado así
            app_instance.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', self.mail_server)
            app_instance.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', self.mail_port))
            app_instance.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
            app_instance.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
            app_instance.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', self.mail_username or '')
            app_instance.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', self.mail_password or '')
            app_instance.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', self.mail_default_sender)
        else:
            # Usar valores de la base de datos
            app_instance.config['MAIL_SERVER'] = self.mail_server
            app_instance.config['MAIL_PORT'] = self.mail_port
            app_instance.config['MAIL_USE_TLS'] = self.mail_use_tls
            app_instance.config['MAIL_USE_SSL'] = self.mail_use_ssl
            app_instance.config['MAIL_USERNAME'] = self.mail_username
            app_instance.config['MAIL_PASSWORD'] = self.mail_password
            app_instance.config['MAIL_DEFAULT_SENDER'] = self.mail_default_sender
        # Evitar [SSL: WRONG_VERSION_NUMBER]: 587 = STARTTLS (no SSL directo), 465 = SSL directo
        port = int(app_instance.config.get('MAIL_PORT', 587))
        if port == 587:
            app_instance.config['MAIL_USE_SSL'] = False
            app_instance.config['MAIL_USE_TLS'] = True
        elif port == 465:
            app_instance.config['MAIL_USE_SSL'] = True
            app_instance.config['MAIL_USE_TLS'] = False
        # Timeout para no colgar (Flask-Mail usa MAIL_TIMEOUT si existe)
        app_instance.config['MAIL_TIMEOUT'] = 25


# --- Marketing (Email Marketing) ---
class MarketingSegment(db.Model):
    __tablename__ = 'marketing_segment'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    query_rules = db.Column(db.Text)  # JSON: {"logic":"and"|"or","conditions":[{"field","op","value"}]}
    exclusion_user_ids = db.Column(db.Text)  # JSON: [1,2,3] opcional; fase 2
    is_dynamic = db.Column(db.Boolean, default=True)  # true = recalcular miembros al enviar
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MarketingTemplate(db.Model):
    __tablename__ = 'marketing_email_templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    html = db.Column(db.Text, nullable=False)
    variables = db.Column(db.Text)  # JSON array: ["nombre","empresa"]
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MarketingCampaign(db.Model):
    __tablename__ = 'marketing_campaigns'
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        default=1,
        index=True,
    )
    name = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(500), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('marketing_email_templates.id'), nullable=False)
    segment_id = db.Column(db.Integer, db.ForeignKey('marketing_segment.id'), nullable=False)
    status = db.Column(db.String(20), default='draft')  # draft, scheduled, sending, sent
    scheduled_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    body_html = db.Column(db.Text, nullable=True)  # override: si está definido se usa en lugar de template.html
    exclusion_emails = db.Column(db.Text, nullable=True)  # JSON array de emails a excluir
    from_name = db.Column(db.String(200), nullable=True)   # ej. "Easy NodeOne" o "Nombre <email@x.com>"
    reply_to = db.Column(db.String(200), nullable=True)   # email de respuesta
    subject_b = db.Column(db.String(500), nullable=True)  # variante B para prueba A/B de asunto
    meeting_url = db.Column(db.String(500), nullable=True)  # URL reunión / Meet; en plantilla {{ reunion_url }}
    template = db.relationship('MarketingTemplate', backref='campaigns')
    segment = db.relationship('MarketingSegment', backref='campaigns')


class CampaignRecipient(db.Model):
    __tablename__ = 'campaign_recipients'
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('marketing_campaigns.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tracking_id = db.Column(db.String(64), unique=True, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, sent, opened, clicked, bounced
    sent_at = db.Column(db.DateTime)
    opened_at = db.Column(db.DateTime)
    clicked_at = db.Column(db.DateTime)
    variant = db.Column(db.String(1), nullable=True)  # 'A' o 'B' para prueba A/B
    campaign = db.relationship('MarketingCampaign', backref='recipients')
    user = db.relationship('User', backref='campaign_recipients')


class AutomationFlow(db.Model):
    __tablename__ = 'automation_flows'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    trigger_event = db.Column(db.String(50), nullable=False)  # member_created, membership_renewed, event_registered
    template_id = db.Column(db.Integer, db.ForeignKey('marketing_email_templates.id'), nullable=False)
    delay_hours = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    template = db.relationship('MarketingTemplate', backref='automation_flows')


class EmailQueueItem(db.Model):
    __tablename__ = 'email_queue'
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    recipient_id = db.Column(db.Integer, db.ForeignKey('campaign_recipients.id'), nullable=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('marketing_campaigns.id'), nullable=True)
    payload = db.Column(db.Text)  # JSON: subject, html, to_email, tracking_id, etc.
    status = db.Column(db.String(20), default='pending')  # pending, processing, sent, failed
    send_after = db.Column(db.DateTime, nullable=True)  # enviar a partir de; NULL = ya
    attempts = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

