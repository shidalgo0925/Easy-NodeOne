# Acceso a datos para servicios (usuario): categorías, servicios, slots.
from datetime import datetime, timedelta

from app import (
    db,
    Service,
    ServiceCategory,
    ServicePricingRule,
    AppointmentType,
    AppointmentAdvisor,
    Advisor,
    AdvisorServiceAvailability,
    AdvisorAvailability,
    DailyServiceAvailability,
    AppointmentSlot,
    Appointment,
)


def get_active_categories():
    return ServiceCategory.query.filter_by(is_active=True).order_by(
        ServiceCategory.display_order, ServiceCategory.name
    ).all()


def get_active_services():
    return Service.query.filter_by(is_active=True).order_by(
        Service.display_order, Service.name
    ).all()


def get_service_or_404(service_id):
    return Service.query.get_or_404(service_id)


def get_appointment_type(atype_id):
    return AppointmentType.query.get(atype_id) if atype_id else None


def get_advisor_assignments(appointment_type_id):
    return AppointmentAdvisor.query.filter_by(
        appointment_type_id=appointment_type_id,
        is_active=True
    ).all()


def advisor_has_availability(advisor_id, appointment_type_id, today, future_date):
    """Comprueba si el asesor tiene algún tipo de disponibilidad o slots."""
    has_specific = AdvisorServiceAvailability.query.filter_by(
        advisor_id=advisor_id,
        appointment_type_id=appointment_type_id,
        is_active=True
    ).first() is not None
    has_general = AdvisorAvailability.query.filter_by(
        advisor_id=advisor_id,
        is_active=True
    ).first() is not None
    has_daily = False
    try:
        has_daily = DailyServiceAvailability.query.filter(
            DailyServiceAvailability.advisor_id == advisor_id,
            DailyServiceAvailability.appointment_type_id == appointment_type_id,
            DailyServiceAvailability.date >= today,
            DailyServiceAvailability.date <= future_date,
            DailyServiceAvailability.is_active == True
        ).first() is not None
    except Exception:
        pass
    has_slots = AppointmentSlot.query.filter(
        AppointmentSlot.advisor_id == advisor_id,
        AppointmentSlot.appointment_type_id == appointment_type_id,
        AppointmentSlot.start_datetime >= datetime.utcnow(),
        AppointmentSlot.start_datetime <= datetime.utcnow() + timedelta(days=90),
        AppointmentSlot.is_available == True
    ).first() is not None
    return has_specific or has_general or has_daily or has_slots


def count_slots(advisor_id, appointment_type_id, days=30):
    return AppointmentSlot.query.filter(
        AppointmentSlot.advisor_id == advisor_id,
        AppointmentSlot.appointment_type_id == appointment_type_id,
        AppointmentSlot.start_datetime >= datetime.utcnow(),
        AppointmentSlot.start_datetime <= datetime.utcnow() + timedelta(days=days)
    ).count()


def get_available_slots(appointment_type_id, days_ahead=30, limit=200, advisor_ids=None):
    q = AppointmentSlot.query.filter(
        AppointmentSlot.appointment_type_id == appointment_type_id,
        AppointmentSlot.start_datetime >= datetime.utcnow(),
        AppointmentSlot.start_datetime <= datetime.utcnow() + timedelta(days=days_ahead),
        AppointmentSlot.is_available == True
    )
    if advisor_ids is not None:
        q = q.filter(AppointmentSlot.advisor_id.in_(advisor_ids))
    return q.order_by(AppointmentSlot.start_datetime.asc()).limit(limit).all()


def get_slots_for_calendar(appointment_type_id, advisor_ids, start_dt, end_dt):
    return AppointmentSlot.query.filter(
        AppointmentSlot.appointment_type_id == appointment_type_id,
        AppointmentSlot.advisor_id.in_(advisor_ids),
        AppointmentSlot.start_datetime >= start_dt,
        AppointmentSlot.start_datetime < end_dt,
        AppointmentSlot.is_available == True
    ).order_by(AppointmentSlot.start_datetime.asc()).all()


def get_appointments_in_range(appointment_type_id, advisor_ids, start_dt, end_dt):
    return Appointment.query.filter(
        Appointment.appointment_type_id == appointment_type_id,
        Appointment.advisor_id.in_(advisor_ids),
        Appointment.status.in_(['CONFIRMADA', 'PENDIENTE', 'confirmed', 'pending']),
        Appointment.start_datetime.isnot(None),
        Appointment.start_datetime >= start_dt,
        Appointment.start_datetime < end_dt
    ).all()
