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


def _event_uploads_public_url(stored: str | None) -> str | None:
    """
    Normaliza rutas de portada/galería: si en BD quedó solo el nombre de archivo
    (sin ``/`` inicial), el navegador resuelve la URL respecto a la ruta actual
    (p. ej. ``/admin/events/12`` → pide ``/admin/events/cover_....png``) y responde 404.
    """
    p = (stored or '').strip()
    if not p or p.lower() in ('none', 'null', 'undefined'):
        return None
    if p.startswith('http://') or p.startswith('https://') or p.startswith('//'):
        return p
    if p.startswith('/static/'):
        return p
    if p.startswith('static/'):
        return '/' + p
    if p.startswith('uploads/'):
        return '/static/' + p
    if p.startswith('/'):
        return p
    if '/' not in p:
        return f'/static/uploads/events/{p}'
    return f'/static/uploads/events/{p.split("/")[-1]}'


def _event_stored_path_exists_on_disk(stored: str) -> bool:
    """True si la ruta (o URL absoluta externa) debería servirse; evita portada rota en BD sin fichero."""
    try:
        from flask import current_app

        u = _event_uploads_public_url(stored)
        if not u:
            return False
        if u.startswith('http://') or u.startswith('https://') or u.startswith('//'):
            return True
        rel = u.lstrip('/')
        fs = os.path.normpath(os.path.join(current_app.root_path, '..', rel))
        return os.path.isfile(fs)
    except Exception:
        return True


# Modelos de Eventos
class Event(db.Model):
    """Modelo para eventos según el diagrama de flujo - 5 pasos: Evento, Descripción, Publicidad, Certificado, Kahoot"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    summary = db.Column(db.Text)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), default='general')
    format = db.Column(db.String(50), default='virtual')  # virtual, presencial, híbrido
    tags = db.Column(db.String(500))
    base_price = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='USD')
    registration_url = db.Column(db.String(500))
    contact_email = db.Column(db.String(120))
    contact_phone = db.Column(db.String(20))
    location = db.Column(db.String(200))
    country = db.Column(db.String(100))
    # Campos adicionales según diagrama
    venue = db.Column(db.String(200))  # Sede o Universidad
    university = db.Column(db.String(200))  # Universidad organizadora
    is_virtual = db.Column(db.Boolean, default=False)
    has_certificate = db.Column(db.Boolean, default=False)
    certificate_instructions = db.Column(db.Text)
    certificate_template = db.Column(db.String(500))  # Template del certificado
    # Integración Kahoot
    kahoot_enabled = db.Column(db.Boolean, default=False)
    kahoot_link = db.Column(db.String(500))
    kahoot_required = db.Column(db.Boolean, default=False)  # Si es obligatorio participar
    # Flujo de 5 pasos
    step_1_event_completed = db.Column(db.Boolean, default=False)  # 1. Evento
    step_2_description_completed = db.Column(db.Boolean, default=False)  # 2. Descripción
    step_3_publicity_completed = db.Column(db.Boolean, default=False)  # 3. Publicidad
    step_4_certificate_completed = db.Column(db.Boolean, default=False)  # 4. Certificado
    step_5_kahoot_completed = db.Column(db.Boolean, default=False)  # 5. Kahoot
    # Salidas del evento (Carteles, Revistas, Libros)
    generates_poster = db.Column(db.Boolean, default=False)
    generates_magazine = db.Column(db.Boolean, default=False)
    generates_book = db.Column(db.Boolean, default=False)
    # Capacidad y registro
    capacity = db.Column(db.Integer, default=0)
    registered_count = db.Column(db.Integer, default=0)
    visibility = db.Column(db.String(20), default='members')  # members, public
    publish_status = db.Column(db.String(20), default='draft')  # draft, published, archived
    featured = db.Column(db.Boolean, default=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    registration_deadline = db.Column(db.DateTime)
    cover_image = db.Column(db.String(500))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    # Roles del evento: Moderador, Administrador, Expositor
    moderator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Moderador del evento
    administrator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Administrador del evento
    speaker_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Expositor/Conferencista principal
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    images = db.relationship('EventImage', backref='event', lazy=True, cascade='all, delete-orphan')
    discounts = db.relationship('EventDiscount', backref='event', lazy=True, cascade='all, delete-orphan')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_events')
    moderator = db.relationship('User', foreign_keys=[moderator_id], backref='moderated_events')
    administrator = db.relationship('User', foreign_keys=[administrator_id], backref='administered_events')
    speaker = db.relationship('User', foreign_keys=[speaker_id], backref='speaker_events')
    
    def get_notification_recipients(self):
        """Obtiene todos los usuarios que deben recibir notificaciones del evento"""
        recipients = []
        
        # Creador del evento
        if self.created_by:
            creator = User.query.get(self.created_by)
            if creator:
                recipients.append(creator)
        
        # Moderador
        if self.moderator_id:
            moderator = User.query.get(self.moderator_id)
            if moderator and moderator not in recipients:
                recipients.append(moderator)
        
        # Administrador del evento
        if self.administrator_id:
            administrator = User.query.get(self.administrator_id)
            if administrator and administrator not in recipients:
                recipients.append(administrator)
        
        # Expositor
        if self.speaker_id:
            speaker = User.query.get(self.speaker_id)
            if speaker and speaker not in recipients:
                recipients.append(speaker)
        
        # Si no hay roles asignados, notificar a todos los administradores del sistema
        if not recipients:
            admins = User.query.filter_by(is_admin=True).all()
            recipients.extend(admins)
        
        return recipients
    
    def cover_url(self):
        """URL de portada o primera imagen de galería que exista en disco; si no hay ficheros, None (icono)."""
        try:
            imgs = list(getattr(self, 'images', None) or [])

            def _sort_key(im):
                return (
                    0 if getattr(im, 'is_primary', False) else 1,
                    getattr(im, 'sort_order', 0) or 0,
                    getattr(im, 'id', 0) or 0,
                )

            gallery_paths = []
            for im in sorted(imgs, key=_sort_key):
                fp = (getattr(im, 'file_path', None) or '').strip()
                if fp:
                    gallery_paths.append(fp)
        except Exception:
            gallery_paths = []

        paths = []
        ci = (self.cover_image or '').strip()
        if ci:
            paths.append(ci)
        for fp in gallery_paths:
            if fp not in paths:
                paths.append(fp)

        for raw in paths:
            if _event_stored_path_exists_on_disk(raw):
                out = _event_uploads_public_url(raw)
                if out:
                    return out
        return None
    
    def pricing_for_membership(self, membership_type=None):
        """Calcula el precio final según el tipo de membresía"""
        base_price = self.base_price or 0.0
        discount = None
        final_price = base_price
        
        if membership_type:
            # Buscar descuento aplicable para este tipo de membresía
            event_discount = EventDiscount.query.join(Discount).filter(
                EventDiscount.event_id == self.id,
                Discount.membership_tier == membership_type,
                Discount.is_active == True
            ).order_by(EventDiscount.priority.asc()).first()
            
            if event_discount:
                discount = event_discount.discount
                if discount.discount_type == 'percentage':
                    final_price = base_price * (1 - discount.value / 100)
                elif discount.discount_type == 'fixed':
                    final_price = max(0, base_price - discount.value)
        
        return {
            'base_price': base_price,
            'final_price': final_price,
            'discount': discount
        }

class EventImage(db.Model):
    """Imágenes de galería para eventos"""
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    is_primary = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def public_file_url(self):
        """Misma normalización que portada; usar en plantillas en lugar de ``file_path`` crudo."""
        u = _event_uploads_public_url(self.file_path)
        return u if u else (self.file_path or '')

class Discount(db.Model):
    """Descuentos reutilizables - Sistema de descuentos por categorías según diagrama:
    Básico (Ba), Pro 10%, R 20%, DX 30%"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True)
    description = db.Column(db.Text)
    discount_type = db.Column(db.String(20), default='percentage')  # percentage, fixed
    value = db.Column(db.Float, nullable=False)
    membership_tier = db.Column(db.String(50))  # basic, pro, premium, deluxe, r, dx
    category = db.Column(db.String(50), default='event')  # event, appointment, service
    applies_automatically = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    is_master = db.Column(db.Boolean, default=False)  # Descuento maestro global
    max_uses = db.Column(db.Integer)
    uses = db.Column(db.Integer, default=0)  # Alias para compatibilidad con esquema antiguo
    current_uses = db.Column(db.Integer, default=0)  # Contador de usos
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación con eventos y citas
    events = db.relationship('EventDiscount', backref='discount', lazy=True)
    
    def can_use(self):
        """Verifica si el descuento puede ser usado"""
        if not self.is_active:
            return False
        # Usar current_uses como fuente de verdad, con fallback a uses
        uses_count = self.current_uses if hasattr(self, 'current_uses') and self.current_uses is not None else (self.uses if hasattr(self, 'uses') and self.uses is not None else 0)
        if self.max_uses and uses_count >= self.max_uses:
            return False
        now = datetime.utcnow()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True

class EventDiscount(db.Model):
    """Relación muchos a muchos entre eventos y descuentos"""
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    discount_id = db.Column(db.Integer, db.ForeignKey('discount.id'), nullable=False)
    priority = db.Column(db.Integer, default=1)  # Orden de aplicación si hay múltiples
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class DiscountCode(db.Model):
    """Códigos promocionales que los usuarios introducen manualmente"""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Tipo y valor del descuento
    discount_type = db.Column(db.String(20), default='percentage')  # percentage, fixed
    value = db.Column(db.Float, nullable=False)
    
    # Alcance del descuento
    applies_to = db.Column(db.String(50), default='all')  # all, events, memberships, appointments
    event_ids = db.Column(db.Text)  # JSON array de event IDs (opcional)
    
    # Válido para solicitud de correo Office 365 (sin hardcodear nombre)
    valid_for_office365 = db.Column(db.Boolean, default=False)
    
    # Vigencia
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    
    # Límites de uso
    max_uses_total = db.Column(db.Integer)  # Límite total de usos
    max_uses_per_user = db.Column(db.Integer, default=1)  # Límite por usuario
    current_uses = db.Column(db.Integer, default=0)
    
    # Estado
    is_active = db.Column(db.Boolean, default=True)
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_discount_codes')
    applications = db.relationship('DiscountApplication', backref='discount_code', lazy=True, cascade='all, delete-orphan')
    
    def can_use(self, user_id=None):
        """Verifica si el código puede ser usado por un usuario"""
        if not self.is_active:
            return False, "Este código de descuento no está activo"
        
        # Verificar vigencia
        now = datetime.utcnow()
        if self.start_date and now < self.start_date:
            return False, f"Este código será válido a partir del {self.start_date.strftime('%d/%m/%Y')}"
        if self.end_date and now > self.end_date:
            return False, "Este código de descuento ha expirado"
        
        # Verificar límite total
        if self.max_uses_total and self.current_uses >= self.max_uses_total:
            return False, "Este código ha alcanzado su límite de usos"
        
        # Verificar límite por usuario
        if user_id and self.max_uses_per_user:
            user_uses = DiscountApplication.query.filter_by(
                discount_code_id=self.id,
                user_id=user_id
            ).count()
            if user_uses >= self.max_uses_per_user:
                return False, f"Ya has usado este código el máximo de veces permitidas ({self.max_uses_per_user})"
        
        return True, "Código válido"
    
    def apply_discount(self, amount):
        """Aplica el descuento a un monto"""
        if self.discount_type == 'percentage':
            return amount * (self.value / 100)
        elif self.discount_type == 'fixed':
            return min(self.value, amount)  # No puede ser mayor que el monto
        return 0


class DiscountApplication(db.Model):
    """Historial de aplicación de códigos de descuento"""
    id = db.Column(db.Integer, primary_key=True)
    discount_code_id = db.Column(db.Integer, db.ForeignKey('discount_code.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'), nullable=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=True)
    
    # Montos
    original_amount = db.Column(db.Float, nullable=False)  # Monto original
    discount_amount = db.Column(db.Float, nullable=False)  # Monto descontado
    final_amount = db.Column(db.Float, nullable=False)  # Monto final
    
    # Metadata
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    user = db.relationship('User', backref='discount_applications')
    payment = db.relationship('Payment', backref='discount_applications')
    cart = db.relationship('Cart', backref='discount_applications')


# ---------------------------------------------------------------------------
# Modelos adicionales para eventos según el diagrama de flujo
# ---------------------------------------------------------------------------
class EventParticipant(db.Model):
    """Participantes de eventos con categorías (participantes, asistentes, ponentes)"""
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    participation_category = db.Column(db.String(50), nullable=False)  # participant, attendee, speaker
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    check_in_time = db.Column(db.DateTime)  # Hora de llegada/check-in
    check_out_time = db.Column(db.DateTime)  # Hora de salida/check-out
    attendance_confirmed = db.Column(db.Boolean, default=False)
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid, refunded
    payment_amount = db.Column(db.Float, default=0.0)
    discount_applied = db.Column(db.Float, default=0.0)
    membership_type_at_registration = db.Column(db.String(50))  # Para aplicar descuentos históricos
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    event = db.relationship('Event', backref='participants')
    user = db.relationship('User', backref='event_participations')
    
    __table_args__ = (
        db.UniqueConstraint('event_id', 'user_id', name='uq_event_user'),
    )


class EventSpeaker(db.Model):
    """Ponentes/Exponentes de eventos"""
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Puede ser externo
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120))
    bio = db.Column(db.Text)
    photo_url = db.Column(db.String(500))
    organization = db.Column(db.String(200))  # Sede o Universidad
    country = db.Column(db.String(100))
    title = db.Column(db.String(200))  # Título de la presentación
    topic_description = db.Column(db.Text)  # Información del tema
    presentation_time = db.Column(db.DateTime)  # Hora de la presentación
    duration_minutes = db.Column(db.Integer, default=30)
    sort_order = db.Column(db.Integer, default=0)
    is_confirmed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    event = db.relationship('Event', backref='speakers')
    user = db.relationship('User', backref='speaker_appearances')


class EventCertificate(db.Model):
    """Certificados generados para participantes de eventos"""
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    participant_id = db.Column(db.Integer, db.ForeignKey('event_participant.id'), nullable=False)
    certificate_number = db.Column(db.String(100), unique=True, nullable=False)
    certificate_url = db.Column(db.String(500))  # URL del PDF generado
    preview_url = db.Column(db.String(500))  # URL del preview
    issued_date = db.Column(db.DateTime, default=datetime.utcnow)
    issued_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # Admin que emitió
    email_sent = db.Column(db.Boolean, default=False)
    email_sent_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    event = db.relationship('Event', backref='certificates')
    participant = db.relationship('EventParticipant', backref='certificates')
    issuer = db.relationship('User', backref='certificates_issued')


class EventWorkshop(db.Model):
    """Talleres dentro de eventos"""
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    instructor_name = db.Column(db.String(200))  # Si es externo
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200))  # Sala, link virtual, etc.
    capacity = db.Column(db.Integer, default=0)
    registered_count = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, default=0.0)
    is_included = db.Column(db.Boolean, default=True)  # Si está incluido en el evento
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    event = db.relationship('Event', backref='workshops')
    instructor = db.relationship('User', backref='workshops_taught')


class EventTopic(db.Model):
    """Temas/Presentaciones de eventos"""
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    speaker_id = db.Column(db.Integer, db.ForeignKey('event_speaker.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    topic_type = db.Column(db.String(50))  # presentation, panel, keynote, etc.
    start_time = db.Column(db.DateTime)
    duration_minutes = db.Column(db.Integer, default=30)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    event = db.relationship('Event', backref='topics')
    speaker = db.relationship('EventSpeaker', backref='topics')

class EventRegistration(db.Model):
    """Registro completo de eventos con flujo de email y almacenamiento"""
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    registration_status = db.Column(db.String(20), default='pending')  # pending, confirmed, cancelled, completed
    # Flujo de emails
    confirmation_email_sent = db.Column(db.Boolean, default=False)
    confirmation_email_sent_at = db.Column(db.DateTime)
    reminder_email_sent = db.Column(db.Boolean, default=False)
    reminder_email_sent_at = db.Column(db.DateTime)
    certificate_email_sent = db.Column(db.Boolean, default=False)
    certificate_email_sent_at = db.Column(db.DateTime)
    # Integración Kahoot
    kahoot_link = db.Column(db.String(500))
    kahoot_participated = db.Column(db.Boolean, default=False)
    kahoot_score = db.Column(db.Integer)
    # Descuentos aplicados
    base_price = db.Column(db.Float, default=0.0)
    discount_applied = db.Column(db.Float, default=0.0)
    final_price = db.Column(db.Float, default=0.0)
    membership_type = db.Column(db.String(50))
    discount_code_used = db.Column(db.String(50))
    # Pagos
    payment_status = db.Column(db.String(20), default='pending')
    payment_method = db.Column(db.String(50))
    payment_reference = db.Column(db.String(100))
    payment_date = db.Column(db.DateTime)
    # Datos adicionales
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    event = db.relationship('Event', backref='registrations')
    user = db.relationship('User', backref='event_registrations')
    
    __table_args__ = (
        db.UniqueConstraint('event_id', 'user_id', name='uq_event_registration'),
    )

