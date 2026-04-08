"""
Modelos ORM de citas: fuente única en app.py (misma instancia Flask-SQLAlchemy / metadata).

El paquete histórico duplicaba clases sobre nodeone.core.db, rompiendo relaciones
string ('User') y provocando KeyError al usar AppointmentType.query desde las rutas.
"""


def load_appointment_context():
    """Carga db + modelos tras inicializar app (import diferido, sin ciclos)."""
    from app import (
        ActivityLog,
        Advisor,
        Appointment,
        AppointmentAdvisor,
        AppointmentEmailTemplate,
        AppointmentParticipant,
        AppointmentPricing,
        AppointmentSlot,
        AppointmentType,
        AdvisorAvailability,
        AdvisorServiceAvailability,
        DailyServiceAvailability,
        Notification,
        Proposal,
        Service,
        User,
        db,
    )

    return {
        'db': db,
        'User': User,
        'Advisor': Advisor,
        'AppointmentType': AppointmentType,
        'AppointmentAdvisor': AppointmentAdvisor,
        'AppointmentSlot': AppointmentSlot,
        'Appointment': Appointment,
        'AppointmentParticipant': AppointmentParticipant,
        'AppointmentPricing': AppointmentPricing,
        'AdvisorAvailability': AdvisorAvailability,
        'AdvisorServiceAvailability': AdvisorServiceAvailability,
        'DailyServiceAvailability': DailyServiceAvailability,
        'ActivityLog': ActivityLog,
        'Service': Service,
        'Notification': Notification,
        'Proposal': Proposal,
        'AppointmentEmailTemplate': AppointmentEmailTemplate,
    }
