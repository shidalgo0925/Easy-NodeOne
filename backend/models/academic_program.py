"""Programas académicos ofertables (inscripción pública) y matrículas del funnel.

Distinto de ``models.academic`` (ERP Moodle: AcademicCourse, Enrollment).
"""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db

_MONTHS_ES: tuple[str, ...] = (
    'enero',
    'febrero',
    'marzo',
    'abril',
    'mayo',
    'junio',
    'julio',
    'agosto',
    'septiembre',
    'octubre',
    'noviembre',
    'diciembre',
)


def format_start_date_es(dt: datetime | None) -> str | None:
    """Ej.: 25 de septiembre de 2026 (mismo criterio que WP / inscripción)."""
    if not dt:
        return None
    return f'{dt.day} de {_MONTHS_ES[dt.month - 1]} de {dt.year}'


class AcademicProgram(db.Model):
    __tablename__ = 'academic_program'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    name = db.Column(db.String(300), nullable=False)
    slug = db.Column(db.String(200), nullable=False)
    program_type = db.Column(
        db.String(32), nullable=False, default='diplomado'
    )  # curso, diplomado, taller, certificacion, servicio, programa
    category = db.Column(db.String(120), nullable=True)
    # Landing ①–⑦ (WP / inscripción); ver glosario en docs PLAN_MODULO_ACADEMIC_ENROLLMENT.
    marketing_tag = db.Column(db.String(120), nullable=True)  # ① área (ej. Neurociencia)
    key_focuses = db.Column(db.Text, nullable=True)  # ⑤a enfoques clave
    ideal_for = db.Column(db.Text, nullable=True)  # ⑤b ideal para
    cta_label = db.Column(db.String(200), nullable=True)  # ⑥ texto botón
    cta_action = db.Column(db.String(32), nullable=False, default='scroll_pricing')  # ⑥ destino
    catalog_sort_order = db.Column(db.Integer, nullable=False, default=0, index=True)  # orden en listados
    short_description = db.Column(db.Text, nullable=True)
    long_description = db.Column(db.Text, nullable=True)  # ④ descripción larga
    modality = db.Column(db.String(120), nullable=True)
    duration_text = db.Column(db.String(200), nullable=True)
    hours = db.Column(db.String(64), nullable=True)
    language = db.Column(db.String(64), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)  # ② catálogo /programas
    flyer_url = db.Column(db.String(500), nullable=True)  # ③ inscripción /inscripcion/
    academic_program_pdf_url = db.Column(db.String(500), nullable=True)  # PDF comercial (landing externo)
    academic_program_pdf_title = db.Column(db.String(200), nullable=True)  # título botón (referencia admin)
    show_academic_program_pdf = db.Column(db.Boolean, default=False, nullable=False)
    academic_program_pdf_filename = db.Column(db.String(255), nullable=True)
    academic_program_pdf_uploaded_at = db.Column(db.DateTime, nullable=True)
    image_wp_landing = db.Column(db.String(500), nullable=True)  # ① WordPress /diplomados/
    media_position = db.Column(db.String(8), nullable=False, default='left')  # left | right (columna imagen 62%)
    price_from = db.Column(db.Float, nullable=True)  # display "desde"
    currency = db.Column(db.String(8), nullable=False, default='USD')
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    seats_limit = db.Column(db.Integer, nullable=True)
    requires_approval = db.Column(db.Boolean, default=False, nullable=False)
    status = db.Column(db.String(32), nullable=False, default='draft', index=True)  # draft, published, archived
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    pricing_plans = db.relationship(
        'AcademicProgramPricingPlan',
        back_populates='program',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )
    enrollments = db.relationship('AcademicProgramEnrollment', back_populates='program', lazy='dynamic')
    resources = db.relationship(
        'AcademicProgramResource',
        back_populates='program',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )

    __table_args__ = (db.UniqueConstraint('organization_id', 'slug', name='uq_academic_program_org_slug'),)

    def display_type_label(self) -> str:
        m = {
            'curso': 'Curso',
            'diplomado': 'Diplomado',
            'taller': 'Taller',
            'certificacion': 'Certificación',
            'servicio': 'Servicio',
            'programa': 'Programa',
        }
        return m.get((self.program_type or '').lower(), (self.program_type or 'Programa').title())

    def start_date_display(self) -> str | None:
        """Texto público: Próximo inicio: 25 de septiembre de 2026."""
        label = format_start_date_es(self.start_date)
        if not label:
            return None
        return f'Próximo inicio: {label}'


class AcademicProgramPricingPlan(db.Model):
    __tablename__ = 'academic_program_pricing_plan'

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey('academic_program.id', ondelete='CASCADE'), nullable=False, index=True)
    program = db.relationship('AcademicProgram', back_populates='pricing_plans')
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(64), nullable=False)  # full, 6, 10
    currency = db.Column(db.String(8), nullable=False, default='USD')
    total_amount_cents = db.Column(db.Integer, nullable=False)  # un cargo = total (como resolve_diplomado_plan)
    installment_count = db.Column(db.Integer, nullable=True)
    installment_amount = db.Column(db.Float, nullable=True)  # informativo
    discount_label = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)

    __table_args__ = (db.UniqueConstraint('program_id', 'code', name='uq_academic_program_plan_code'),)


class AcademicProgramEnrollment(db.Model):
    __tablename__ = 'academic_program_enrollment'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, index=True
    )
    program_id = db.Column(db.Integer, db.ForeignKey('academic_program.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    pricing_plan_id = db.Column(
        db.Integer, db.ForeignKey('academic_program_pricing_plan.id', ondelete='SET NULL'), nullable=True, index=True
    )
    status = db.Column(
        db.String(32), nullable=False, default='pending_payment', index=True
    )  # draft, pending_payment, paid, confirmed, cancelled
    payment_status = db.Column(db.String(32), nullable=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id', ondelete='SET NULL'), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    confirmed_at = db.Column(db.DateTime, nullable=True)

    program = db.relationship('AcademicProgram', back_populates='enrollments', foreign_keys=[program_id])
    user = db.relationship('User', backref=db.backref('academic_program_enrollments', lazy='dynamic'))
    pricing_plan = db.relationship('AcademicProgramPricingPlan', backref=db.backref('enrollments', lazy='dynamic'))


class AcademicProgramResource(db.Model):
    __tablename__ = 'academic_program_resource'

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer, db.ForeignKey('academic_program.id', ondelete='CASCADE'), nullable=False, index=True
    )
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=True)
    resource_type = db.Column(db.String(32), nullable=False, default='other', index=True)
    button_text = db.Column(db.String(200), nullable=True)
    file_url = db.Column(db.String(500), nullable=True)
    external_url = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_public = db.Column(db.Boolean, default=False, nullable=False)
    requires_login = db.Column(db.Boolean, default=False, nullable=False)
    requires_purchase = db.Column(db.Boolean, default=False, nullable=False)
    requires_lead_capture = db.Column(db.Boolean, default=False, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    program = db.relationship('AcademicProgram', back_populates='resources', foreign_keys=[program_id])
