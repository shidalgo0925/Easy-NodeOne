"""Agenda post-pago V1: coaching con Google Calendar (ECalendar)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from nodeone.modules.ecalendar.services.bookings import create_booking
from nodeone.modules.ecalendar.services.config import load_ecalendar_config

AGENDA_STATUS_NOT_REQUIRED = 'not_required'
AGENDA_STATUS_PENDING = 'pending'
AGENDA_STATUS_SCHEDULED = 'scheduled'

SLUG_ECALENDAR_PRODUCT: dict[str, str] = {
    'coaching-individual': 'coaching_personal',
    'coaching-ejecutivo': 'coaching_ejecutivo',
}


def ecalendar_product_id_for_program(program) -> str | None:
    pid = (getattr(program, 'ecalendar_product_id', None) or '').strip()
    if pid:
        return pid
    slug = (getattr(program, 'slug', None) or '').strip().lower()
    return SLUG_ECALENDAR_PRODUCT.get(slug)


def program_requires_agenda(program) -> bool:
    return bool(getattr(program, 'requires_agenda', False))


def enrollment_needs_agenda(enrollment) -> bool:
    if not enrollment or not enrollment.program:
        return False
    if not program_requires_agenda(enrollment.program):
        return False
    status = (getattr(enrollment, 'agenda_status', None) or '').strip().lower()
    return status == AGENDA_STATUS_PENDING


def enrollment_agenda_display(enrollment) -> dict[str, Any] | None:
    """Datos para dashboard alumno."""
    if not enrollment or not enrollment.program:
        return None
    if not program_requires_agenda(enrollment.program):
        return None
    status = (getattr(enrollment, 'agenda_status', None) or AGENDA_STATUS_NOT_REQUIRED).strip().lower()
    out: dict[str, Any] = {
        'enrollment_id': int(enrollment.id),
        'program_name': enrollment.program.name or '',
        'program_slug': enrollment.program.slug or '',
        'agenda_status': status,
        'scheduled_at': getattr(enrollment, 'scheduled_at', None),
        'schedule_url': None,
    }
    if status == AGENDA_STATUS_PENDING:
        out['schedule_url'] = f'/inscripcion/agendar/{int(enrollment.id)}'
    return out


def find_pending_agenda_enrollment(*, user_id: int, payment_id: int | None = None):
    from models.academic_program import AcademicProgramEnrollment

    q = AcademicProgramEnrollment.query.filter_by(
        user_id=int(user_id),
        agenda_status=AGENDA_STATUS_PENDING,
    )
    if payment_id is not None:
        q = q.filter_by(payment_id=int(payment_id))
    return q.order_by(AcademicProgramEnrollment.id.desc()).first()


def list_user_coaching_agenda_items(user_id: int) -> list[dict[str, Any]]:
    from models.academic_program import AcademicProgram, AcademicProgramEnrollment

    rows = (
        AcademicProgramEnrollment.query.filter_by(user_id=int(user_id))
        .join(AcademicProgram, AcademicProgramEnrollment.program_id == AcademicProgram.id)
        .filter(AcademicProgram.requires_agenda.is_(True))
        .filter(
            AcademicProgramEnrollment.agenda_status.in_(
                (AGENDA_STATUS_PENDING, AGENDA_STATUS_SCHEDULED)
            )
        )
        .order_by(AcademicProgramEnrollment.id.desc())
        .limit(10)
        .all()
    )
    items = []
    for en in rows:
        item = enrollment_agenda_display(en)
        if item:
            items.append(item)
    return items


def init_agenda_status_on_payment(enrollment, program) -> None:
    if program_requires_agenda(program):
        enrollment.agenda_status = AGENDA_STATUS_PENDING
    else:
        enrollment.agenda_status = AGENDA_STATUS_NOT_REQUIRED


def book_enrollment_agenda(enrollment, slot_start_raw: str) -> tuple[dict[str, Any] | None, int, str | None]:
    """Reserva cita tras pago (reutiliza create_booking de ECalendar)."""
    from nodeone.core.db import db

    if not enrollment or not enrollment.program:
        return None, 400, 'invalid_enrollment'
    if not enrollment_needs_agenda(enrollment):
        return None, 400, 'agenda_not_pending'

    program = enrollment.program
    product_id = ecalendar_product_id_for_program(program)
    if not product_id:
        return None, 400, 'invalid_product'

    user = enrollment.user
    if not user:
        return None, 400, 'invalid_user'

    name = ' '.join(
        x for x in ((getattr(user, 'first_name', None) or ''), (getattr(user, 'last_name', None) or '')) if x
    ).strip() or (getattr(user, 'email', None) or 'Alumno')
    email = (getattr(user, 'email', None) or '').strip().lower()
    if not email:
        return None, 400, 'invalid_email'

    cfg = load_ecalendar_config(organization_id=int(enrollment.organization_id))
    payload = {
        'product_id': product_id,
        'name': name,
        'email': email,
        'slot_start': slot_start_raw,
        'notes': f'Matrícula EN1 #{enrollment.id} — {program.name or program.slug}',
    }
    result, status, err = create_booking(cfg, payload)
    if err:
        return None, status, err

    assert result is not None
    try:
        slot_start = datetime.fromisoformat((result.get('slot_start') or slot_start_raw).replace('Z', '+00:00'))
        if slot_start.tzinfo:
            slot_start = slot_start.replace(tzinfo=None)
    except ValueError:
        slot_start = datetime.utcnow()

    enrollment.agenda_status = AGENDA_STATUS_SCHEDULED
    enrollment.scheduled_at = slot_start
    enrollment.google_event_id = (result.get('booking_id') or '').strip() or None
    db.session.add(enrollment)
    db.session.commit()

    return {
        'ok': True,
        'enrollment_id': int(enrollment.id),
        'booking_id': enrollment.google_event_id,
        'slot_start': result.get('slot_start'),
        'slot_end': result.get('slot_end'),
        'title': result.get('title'),
    }, 201, None
