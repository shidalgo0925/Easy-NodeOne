"""Convocatorias (cohortes) de programas tipo curso/diplomado vendidos como servicio COURSE."""

from datetime import date, datetime

from nodeone.core.db import db


class CourseCohort(db.Model):
    """
    Una edición concreta de un programa (fecha inicio, cupos, modalidad).
    El producto de catálogo es ``Service`` (service_type=COURSE); el precio base sale de ahí
    salvo ``price_override_cents``.
    """

    __tablename__ = 'course_cohort'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    service_id = db.Column(db.Integer, db.ForeignKey('service.id', ondelete='CASCADE'), nullable=False, index=True)
    service = db.relationship('Service', backref=db.backref('course_cohorts', lazy='dynamic'))

    slug = db.Column(db.String(80), nullable=True)  # opcional p. ej. 2026-05-virtual
    label = db.Column(db.String(200), nullable=True)  # título corto en UI
    start_date = db.Column(db.Date, nullable=True, index=True)
    end_date = db.Column(db.Date, nullable=True)
    weeks_duration = db.Column(db.Integer, nullable=True)
    modality = db.Column(db.String(40), nullable=False, default='virtual')  # virtual | hybrid | presential

    capacity_total = db.Column(db.Integer, nullable=False, default=0)  # 0 = sin límite explícito
    capacity_reserved = db.Column(db.Integer, nullable=False, default=0)

    price_override_cents = db.Column(db.Integer, nullable=True)  # si None → precio del Service

    is_active = db.Column(db.Boolean, nullable=False, default=True)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def spots_available(self):
        """None = ilimitado; int = plazas libres."""
        cap = int(self.capacity_total or 0)
        if cap <= 0:
            return None
        left = cap - int(self.capacity_reserved or 0)
        return max(0, left)

    def is_past_start(self) -> bool:
        if not self.start_date:
            return False
        return self.start_date < date.today()
