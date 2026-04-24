"""Solicitud comercial consultiva: une usuario, servicio, cita y venta (cotización / factura)."""

from datetime import datetime

from nodeone.core.db import db


class ServiceRequest(db.Model):
    __tablename__ = 'service_request'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        default=1,
    )
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id', ondelete='CASCADE'), nullable=False, index=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id', ondelete='SET NULL'), nullable=True, index=True)
    # IDs lógicos (evita orden de creación de tablas respecto a módulo ventas/facturación).
    quotation_id = db.Column(db.Integer, nullable=True, index=True)
    invoice_id = db.Column(db.Integer, nullable=True, index=True)
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisor.id', ondelete='SET NULL'), nullable=True, index=True)
    # Sin FK duro: el módulo CRM puede cargarse después del catálogo en arranques mínimos.
    crm_lead_id = db.Column(db.Integer, nullable=True, index=True)

    status = db.Column(
        db.String(32),
        nullable=False,
        default='requested',
        index=True,
    )
    # requested → appointment_scheduled → in_consultation → quoted → approved → in_progress → completed | cancelled

    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('service_requests', lazy='dynamic'))
    service = db.relationship('Service', foreign_keys=[service_id], backref=db.backref('service_requests', lazy='dynamic'))
    appointment = db.relationship('Appointment', foreign_keys=[appointment_id], backref=db.backref('service_request', uselist=False))
