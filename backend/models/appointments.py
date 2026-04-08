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
# Modelos de Citas / Appointments
# ---------------------------------------------------------------------------
class Advisor(db.Model):
    """Perfil de asesores internos que atienden citas."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    headline = db.Column(db.String(120))
    bio = db.Column(db.Text)
    specializations = db.Column(db.Text)
    meeting_url = db.Column(db.String(255))
    photo_url = db.Column(db.String(255))
    average_response_time = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('advisor_profile', uselist=False))
    advisor_assignments = db.relationship('AppointmentAdvisor', backref='advisor', lazy=True, cascade='all, delete-orphan')
    availability = db.relationship('AdvisorAvailability', backref='advisor', lazy=True, cascade='all, delete-orphan')
    slots = db.relationship('AppointmentSlot', backref='advisor', lazy=True, cascade='all, delete-orphan')
    appointments = db.relationship('Appointment', backref='advisor_profile', lazy=True)


class AppointmentType(db.Model):
    """Servicios configurables que pueden reservar los miembros."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    display_name = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text)
    service_category = db.Column(db.String(100))
    duration_minutes = db.Column(db.Integer, default=60)
    is_group_allowed = db.Column(db.Boolean, default=False)
    max_participants = db.Column(db.Integer, default=1)
    base_price = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='USD')
    is_virtual = db.Column(db.Boolean, default=True)
    requires_confirmation = db.Column(db.Boolean, default=True)
    color_tag = db.Column(db.String(20), default='#0d6efd')
    icon = db.Column(db.String(50), default='fa-calendar-check')
    display_order = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, default=1
    )

    advisor_assignments = db.relationship('AppointmentAdvisor', backref='appointment_type', lazy=True, cascade='all, delete-orphan')
    pricing_rules = db.relationship('AppointmentPricing', backref='appointment_type', lazy=True, cascade='all, delete-orphan')
    slots = db.relationship('AppointmentSlot', backref='appointment_type', lazy=True, cascade='all, delete-orphan')
    appointments = db.relationship('Appointment', backref='appointment_type', lazy=True)

    def duration(self):
        return timedelta(minutes=self.duration_minutes or 60)

    def public_service_label(self):
        """Etiqueta corta para UI/correos: display_name o name."""
        dn = (self.display_name or '').strip()
        if dn:
            return dn
        return (self.name or '').strip() or 'Servicio'

    def pricing_for_membership(self, membership_type=None):
        """Calcula el precio final considerando reglas por membresía."""
        base_price = self.base_price or 0.0
        final_price = base_price
        discount_percentage = 0.0
        is_included = False
        rule = None

        if membership_type:
            rule = AppointmentPricing.query.filter_by(
                appointment_type_id=self.id,
                membership_type=membership_type,
                is_active=True
            ).first()

        if rule:
            if rule.is_included:
                final_price = 0.0
                is_included = True
            elif rule.price is not None:
                final_price = rule.price
            elif rule.discount_percentage:
                discount_percentage = rule.discount_percentage
                final_price = max(0.0, base_price * (1 - discount_percentage / 100))

        return {
            'base_price': base_price,
            'final_price': final_price,
            'discount_percentage': discount_percentage,
            'is_included': is_included,
            'rule': rule
        }


class AppointmentAdvisor(db.Model):
    """Asignación de asesores a tipos de cita."""
    id = db.Column(db.Integer, primary_key=True)
    appointment_type_id = db.Column(db.Integer, db.ForeignKey('appointment_type.id'), nullable=False)
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisor.id'), nullable=False)
    priority = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('appointment_type_id', 'advisor_id', name='uq_type_advisor'),
    )


class AdvisorAvailability(db.Model):
    """Bloques semanales de disponibilidad declarados por cada asesor."""
    id = db.Column(db.Integer, primary_key=True)
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisor.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0 = lunes ... 6 = domingo
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    timezone = db.Column(db.String(50), default='America/Panama')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.CheckConstraint('end_time > start_time', name='ck_availability_time_window'),
    )


class AdvisorServiceAvailability(db.Model):
    """
    Horarios de disponibilidad de asesores por servicio/tipo de cita.
    Permite configurar horarios específicos para cada combinación asesor-servicio.
    Similar al Schedule Tab de Odoo.
    """
    id = db.Column(db.Integer, primary_key=True)
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisor.id'), nullable=False)
    appointment_type_id = db.Column(db.Integer, db.ForeignKey('appointment_type.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0 = lunes ... 6 = domingo
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    timezone = db.Column(db.String(50), default='America/Panama')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    advisor = db.relationship('Advisor', backref='service_availabilities')
    appointment_type = db.relationship('AppointmentType', backref='advisor_availabilities')
    created_by_user = db.relationship('User', backref='service_availabilities_created', foreign_keys=[created_by])

    __table_args__ = (
        db.CheckConstraint('end_time > start_time', name='ck_service_availability_time_window'),
        db.Index('idx_advisor_service_day', 'advisor_id', 'appointment_type_id', 'day_of_week'),
    )


class DailyServiceAvailability(db.Model):
    """
    Disponibilidad específica por día, servicio y asesor.
    Permite configurar horarios para días específicos en lugar de horarios semanales recurrentes.
    """
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)  # Día específico (ej: 2026-01-15)
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisor.id'), nullable=False)
    appointment_type_id = db.Column(db.Integer, db.ForeignKey('appointment_type.id'), nullable=False)
    start_time = db.Column(db.Time, nullable=False)  # Hora inicio del bloque (ej: 09:00)
    end_time = db.Column(db.Time, nullable=False)    # Hora fin del bloque (ej: 12:00)
    timezone = db.Column(db.String(50), default='America/Panama')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    advisor = db.relationship('Advisor', backref='daily_availabilities')
    appointment_type = db.relationship('AppointmentType', backref='daily_availabilities')
    created_by_user = db.relationship('User', backref='daily_availabilities_created', foreign_keys=[created_by])
    
    __table_args__ = (
        db.CheckConstraint('end_time > start_time', name='ck_daily_availability_time_window'),
        db.Index('idx_daily_availability', 'date', 'advisor_id', 'appointment_type_id'),
        db.Index('idx_daily_availability_date', 'date'),
    )


class AppointmentPricing(db.Model):
    """Reglas de precio/descuento por tipo de membresía."""
    id = db.Column(db.Integer, primary_key=True)
    appointment_type_id = db.Column(db.Integer, db.ForeignKey('appointment_type.id'), nullable=False)
    membership_type = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float)
    discount_percentage = db.Column(db.Float, default=0.0)
    is_included = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('appointment_type_id', 'membership_type', name='uq_pricing_membership'),
    )


class AppointmentSlot(db.Model):
    """Slots concretos de tiempo que pueden reservar los miembros."""
    id = db.Column(db.Integer, primary_key=True)
    appointment_type_id = db.Column(db.Integer, db.ForeignKey('appointment_type.id'), nullable=False)
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisor.id'), nullable=False)
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=False)
    capacity = db.Column(db.Integer, default=1)
    reserved_seats = db.Column(db.Integer, default=0)
    is_available = db.Column(db.Boolean, default=True)
    is_auto_generated = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by_user = db.relationship('User', backref='appointment_slots_created', foreign_keys=[created_by])
    appointment = db.relationship('Appointment', backref='slot', uselist=False)

    __table_args__ = (
        db.CheckConstraint('capacity >= 1', name='ck_slot_capacity_positive'),
        db.CheckConstraint('end_datetime > start_datetime', name='ck_slot_time_window'),
    )

    def remaining_seats(self):
        return max(0, (self.capacity or 1) - (self.reserved_seats or 0))


class Appointment(db.Model):
    """Reservas realizadas por miembros - Modelo inspirado en Odoo."""
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(40), unique=True, default=lambda: secrets.token_hex(4).upper())
    appointment_type_id = db.Column(db.Integer, db.ForeignKey('appointment_type.id'), nullable=False)
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisor.id'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('appointment_slot.id'), nullable=True)  # NULL cuando está en cola
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    membership_type = db.Column(db.String(50))
    is_group = db.Column(db.Boolean, default=False)
    start_datetime = db.Column(db.DateTime, nullable=True)  # NULL cuando está en cola, se asigna cuando el asesor confirma
    end_datetime = db.Column(db.DateTime, nullable=True)  # NULL cuando está en cola, se asigna cuando el asesor confirma
    status = db.Column(db.String(20), default='pending')  # pending, PENDIENTE, confirmed, CONFIRMADA, cancelled, RECHAZADA, completed, no_show
    queue_position = db.Column(db.Integer, nullable=True)  # Posición en la cola (opcional, para ordenar)
    advisor_confirmed = db.Column(db.Boolean, default=False)
    advisor_confirmed_at = db.Column(db.DateTime)
    is_initial_consult = db.Column(db.Boolean, default=True)  # Primera reunión (solicitud → confirmación)
    advisor_response_notes = db.Column(db.Text, nullable=True)  # Comentario al confirmar/rechazar
    confirmed_at = db.Column(db.DateTime, nullable=True)  # Fecha/hora de confirmación por asesor
    cancellation_reason = db.Column(db.Text)
    cancelled_by = db.Column(db.String(20))  # user, advisor, system
    cancelled_at = db.Column(db.DateTime)
    base_price = db.Column(db.Float, default=0.0)
    final_price = db.Column(db.Float, default=0.0)
    discount_applied = db.Column(db.Float, default=0.0)
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid, refunded, partial
    payment_method = db.Column(db.String(50))  # stripe, cash, bank_transfer, free
    payment_reference = db.Column(db.String(100))
    user_notes = db.Column(db.Text)
    advisor_notes = db.Column(db.Text)
    # Campos adicionales inspirados en Odoo
    calendar_sync_url = db.Column(db.String(500))  # URL para sincronizar con Google Calendar, Outlook, etc.
    calendar_event_id = db.Column(db.String(200))  # ID del evento en el calendario externo
    reminder_sent = db.Column(db.Boolean, default=False)  # Si se envió recordatorio
    reminder_sent_at = db.Column(db.DateTime)
    confirmation_sent = db.Column(db.Boolean, default=False)  # Si se envió confirmación
    confirmation_sent_at = db.Column(db.DateTime)
    cancellation_sent = db.Column(db.Boolean, default=False)  # Si se envió notificación de cancelación
    cancellation_sent_at = db.Column(db.DateTime)
    meeting_url = db.Column(db.String(500))  # URL de la reunión (Zoom, Teams, etc.)
    meeting_password = db.Column(db.String(100))  # Contraseña de la reunión si aplica
    check_in_time = db.Column(db.DateTime)  # Hora de llegada/check-in
    check_out_time = db.Column(db.DateTime)  # Hora de salida/check-out
    duration_actual = db.Column(db.Integer)  # Duración real en minutos
    rating = db.Column(db.Integer)  # Calificación del 1 al 5
    rating_comment = db.Column(db.Text)  # Comentario de la calificación
    # Campos para vincular con servicios
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=True)  # Servicio relacionado (para citas de diagnóstico)
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'), nullable=True)  # Pago relacionado
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, default=1
    )
    reminder_24h_sent_at = db.Column(db.DateTime)
    reminder_1h_sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref='appointments')
    participants = db.relationship('AppointmentParticipant', backref='appointment', lazy=True, cascade='all, delete-orphan')
    related_service = db.relationship('Service', foreign_keys=[service_id], backref='diagnostic_appointments')
    payment = db.relationship('Payment', foreign_keys=[payment_id], backref='appointments')

    def can_user_cancel(self):
        """Permite cancelar si faltan al menos 12 horas."""
        return self.start_datetime - datetime.utcnow() > timedelta(hours=12)
    
    def is_past(self):
        """Verifica si la cita ya pasó."""
        return self.end_datetime < datetime.utcnow()
    
    def is_upcoming(self):
        """Verifica si la cita está próxima (dentro de las próximas 24 horas)."""
        now = datetime.utcnow()
        return self.start_datetime > now and (self.start_datetime - now) <= timedelta(hours=24)
    
    def get_duration_minutes(self):
        """Calcula la duración en minutos."""
        if self.end_datetime and self.start_datetime:
            delta = self.end_datetime - self.start_datetime
            return int(delta.total_seconds() / 60)
        return 0

    def should_invoice(self):
        """Fase 5: Primera reunión gratuita — no facturar ni exigir pago."""
        return not getattr(self, 'is_initial_consult', False)


class AppointmentParticipant(db.Model):
    """Participantes adicionales (para citas grupales)."""
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    invited_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id], backref='appointment_participations')
    invited_by = db.relationship('User', foreign_keys=[invited_by_id], backref='appointment_invitations', lazy=True)


class Proposal(db.Model):
    """Fase 6: Propuesta del asesor al cliente tras reunión (solo si cita CONFIRMADA)."""
    __tablename__ = 'proposal'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    description = db.Column(db.Text, nullable=True)
    total_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='ENVIADA')  # ENVIADA, ACEPTADA, RECHAZADA
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    client = db.relationship('User', foreign_keys=[client_id], backref='proposals_received')
    appointment = db.relationship('Appointment', foreign_keys=[appointment_id], backref='proposals')


class AppointmentEmailTemplate(db.Model):
    """Plantillas de correo por tenant y tipo de cita (prioridad sobre email_template global)."""

    __tablename__ = 'appointment_email_template'
    __table_args__ = (
        db.UniqueConstraint(
            'organization_id',
            'appointment_type_id',
            'template_key',
            name='uq_appointment_email_template_org_type_key',
        ),
    )
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False
    )
    appointment_type_id = db.Column(
        db.Integer, db.ForeignKey('appointment_type.id', ondelete='CASCADE'), nullable=False
    )
    template_key = db.Column(db.String(80), nullable=False)
    name = db.Column(db.String(200), nullable=True)
    subject = db.Column(db.String(500), nullable=False)
    html_content = db.Column(db.Text, nullable=False)
    is_custom = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    appointment_type = db.relationship(
        'AppointmentType', backref=db.backref('email_overrides', lazy=True)
    )


class ActivityLog(db.Model):
    """Log de actividades administrativas"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # create_event, update_event, etc.
    entity_type = db.Column(db.String(50), nullable=False)  # event, discount, user, etc.
    entity_id = db.Column(db.Integer)
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='activity_logs')
    
    @classmethod
    def log_activity(cls, user_id, action, entity_type, entity_id, description, request=None):
        """Método helper para registrar actividades"""
        log = cls(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get('User-Agent') if request else None
        )
        db.session.add(log)
        return log


class ExportTemplate(db.Model):
    """Plantilla de exportación guardada (entidad + campos). visibility: own | shared."""
    __tablename__ = 'export_template'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120), nullable=False)
    entity = db.Column(db.String(50), nullable=False, default='members')
    fields = db.Column(db.Text, nullable=False)  # JSON array de field keys
    visibility = db.Column(db.String(20), default='own', nullable=False)  # own | shared
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='export_templates')
