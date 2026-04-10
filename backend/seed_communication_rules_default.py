#!/usr/bin/env python3
"""
Semilla idempotente: communication_event + communication_rule (canal in_app, ámbito global).

Así `communication_rules_exist()` devuelve True y `run_communication_engine_if_configured`
dispara el motor. Las notificaciones in-app usan título/mensaje del `context` que envía
cada flujo (email sigue dependiendo de plantilla marketing si añadís reglas `email`).

Uso (desde backend/):
  ../venv/bin/python3 seed_communication_rules_default.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db  # noqa: E402
from models.communication_rules import (  # noqa: E402
    CommunicationEvent,
    CommunicationLog,
    CommunicationRule,
    UserCommunicationPreference,
)

# Mismo catálogo que migrate_communication_engine.py
COMMUNICATION_EVENTS_SEED = (
    ('member_created', 'Usuario registrado', 'Alta de nuevo miembro / cuenta.', 'transactional'),
    ('membership_renewed', 'Membresía renovada', 'Renovación confirmada.', 'transactional'),
    ('membership_payment', 'Pago de membresía', 'Confirmación u avisos de pago de membresía.', 'transactional'),
    ('membership_expiring', 'Membresía por expirar', 'Avisos antes del vencimiento (scheduler).', 'transactional'),
    ('membership_expired', 'Membresía expirada', 'Aviso al expirar (scheduler).', 'transactional'),
    ('payment_received', 'Pago recibido', 'Pago confirmado (genérico).', 'transactional'),
    ('event_registered', 'Inscripción a evento', 'Usuario inscrito en un evento.', 'transactional'),
    ('event_registration', 'Aviso a responsables de evento', 'Nuevo registro (staff).', 'transactional'),
    ('event_registration_user', 'Confirmación registro evento (usuario)', 'Email al usuario al inscribirse.', 'transactional'),
    ('event_cancellation', 'Cancelación evento (responsables)', 'Aviso a staff por cancelación.', 'transactional'),
    ('event_cancellation_user', 'Cancelación registro (usuario)', 'Email al usuario que cancela.', 'transactional'),
    ('event_confirmation', 'Confirmación registro (responsables)', 'Aviso a staff al confirmar registro.', 'transactional'),
    ('event_update', 'Actualización de evento', 'Aviso a inscritos por cambios.', 'transactional'),
    ('appointment_created', 'Cita creada', 'Solicitud o confirmación de cita.', 'transactional'),
    ('appointment_booked', 'Cita agendada (cliente)', 'Cliente tras pago de slot / cita confirmada.', 'transactional'),
    ('appointment_confirmation', 'Confirmación de cita', 'Cita confirmada.', 'transactional'),
    ('appointment_reminder', 'Recordatorio de cita', 'Recordatorios 24h/1h (scheduler).', 'transactional'),
    ('appointment_cancellation', 'Cancelación de cita', 'Aviso al miembro por cancelación.', 'transactional'),
    ('appointment_new_admin', 'Nueva cita (administradores)', 'Aviso a admins por cita creada tras pago.', 'transactional'),
    ('password_reset', 'Restablecer contraseña', 'Flujo de recuperación de contraseña.', 'system'),
    ('welcome', 'Bienvenida', 'Email de bienvenida.', 'system'),
    ('invoice_generated', 'Factura generada', 'Factura o documento contable.', 'transactional'),
    ('system_alert', 'Alerta del sistema', 'Avisos operativos.', 'system'),
    ('marketing_campaign', 'Campaña de marketing', 'Envíos masivos programados.', 'marketing'),
)


def main() -> None:
    with app.app_context():
        CommunicationEvent.__table__.create(db.engine, checkfirst=True)
        CommunicationRule.__table__.create(db.engine, checkfirst=True)
        UserCommunicationPreference.__table__.create(db.engine, checkfirst=True)
        CommunicationLog.__table__.create(db.engine, checkfirst=True)

        ev_new = 0
        for code, name, description, category in COMMUNICATION_EVENTS_SEED:
            ev = CommunicationEvent.query.filter_by(code=code).first()
            if ev:
                continue
            db.session.add(
                CommunicationEvent(
                    code=code,
                    name=name,
                    description=description,
                    category=category,
                )
            )
            ev_new += 1
        if ev_new:
            db.session.commit()

        rule_new = 0
        for code, _, _, _ in COMMUNICATION_EVENTS_SEED:
            ev = CommunicationEvent.query.filter_by(code=code).first()
            if not ev:
                continue
            dup = (
                CommunicationRule.query.filter_by(
                    event_id=ev.id,
                    channel='in_app',
                    organization_id=None,
                ).first()
            )
            if dup:
                continue
            db.session.add(
                CommunicationRule(
                    event_id=ev.id,
                    organization_id=None,
                    channel='in_app',
                    enabled=True,
                    marketing_template_id=None,
                    delay_minutes=0,
                    is_marketing=False,
                    respect_user_prefs=True,
                    priority=10,
                )
            )
            rule_new += 1
        if rule_new:
            db.session.commit()

        n_ev = CommunicationEvent.query.count()
        n_ru = CommunicationRule.query.count()
        print(f'✅ communication_event: {n_ev} filas (+{ev_new} nuevas en esta pasada)')
        print(f'✅ communication_rule: {n_ru} filas (+{rule_new} reglas in_app globales nuevas)')


if __name__ == '__main__':
    main()
