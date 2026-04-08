"""Generación automática de slots desde disponibilidad de asesores."""
from datetime import datetime, timedelta

from app import (
    Advisor,
    AdvisorAvailability,
    AdvisorServiceAvailability,
    AppointmentAdvisor,
    AppointmentSlot,
    AppointmentType,
    db,
)


def generate_slots_from_availability(advisor_id, appointment_type_id, days_ahead=30, slot_interval_minutes=None):
    """
    Genera slots automáticamente desde AdvisorAvailability / AdvisorServiceAvailability.
    """
    advisor = Advisor.query.get(advisor_id)
    appointment_type = AppointmentType.query.get(appointment_type_id)

    if not advisor or not appointment_type:
        return []

    assignment = AppointmentAdvisor.query.filter_by(
        appointment_type_id=appointment_type_id,
        advisor_id=advisor_id,
        is_active=True,
    ).first()

    if not assignment:
        return []

    availabilities = AdvisorServiceAvailability.query.filter_by(
        advisor_id=advisor_id,
        appointment_type_id=appointment_type_id,
        is_active=True,
    ).all()

    if not availabilities:
        availabilities_general = AdvisorAvailability.query.filter_by(
            advisor_id=advisor_id,
            is_active=True,
        ).all()

        if not availabilities_general:
            return []

        class AvailabilityWrapper:
            def __init__(self, av):
                self.day_of_week = av.day_of_week
                self.start_time = av.start_time
                self.end_time = av.end_time
                self.timezone = av.timezone

        availabilities = [AvailabilityWrapper(av) for av in availabilities_general]

    slot_duration = appointment_type.duration()
    slot_interval = timedelta(minutes=slot_interval_minutes) if slot_interval_minutes else slot_duration

    start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=days_ahead)

    slots_created = []
    current_date = start_date

    while current_date < end_date:
        day_of_week = current_date.weekday()

        day_availabilities = [av for av in availabilities if av.day_of_week == day_of_week]

        for availability in day_availabilities:
            slot_start = datetime.combine(current_date.date(), availability.start_time)
            slot_end_time = availability.end_time

            current_slot_start = slot_start

            while current_slot_start.time() < slot_end_time:
                current_slot_end = current_slot_start + slot_duration

                if current_slot_end.time() > slot_end_time:
                    break

                if current_slot_start < datetime.utcnow():
                    current_slot_start += slot_interval
                    continue

                existing_slot = AppointmentSlot.query.filter(
                    AppointmentSlot.advisor_id == advisor_id,
                    AppointmentSlot.appointment_type_id == appointment_type_id,
                    AppointmentSlot.start_datetime == current_slot_start,
                    AppointmentSlot.is_available == True,
                ).first()

                if not existing_slot:
                    conflicting = AppointmentSlot.query.filter(
                        AppointmentSlot.advisor_id == advisor_id,
                        AppointmentSlot.start_datetime < current_slot_end,
                        AppointmentSlot.end_datetime > current_slot_start,
                        AppointmentSlot.is_available == True,
                    ).first()

                    if not conflicting:
                        new_slot = AppointmentSlot(
                            appointment_type_id=appointment_type_id,
                            advisor_id=advisor_id,
                            start_datetime=current_slot_start,
                            end_datetime=current_slot_end,
                            capacity=1,
                            is_available=True,
                            is_auto_generated=True,
                        )
                        db.session.add(new_slot)
                        slots_created.append(new_slot)

                current_slot_start += slot_interval

        current_date += timedelta(days=1)

    if slots_created:
        db.session.commit()

    return slots_created
