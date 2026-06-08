"""Crea EventParticipant a partir de EventRegistration confirmados."""

from __future__ import annotations


def _payment_status_from_registration(reg) -> str:
    ps = (getattr(reg, 'payment_status', None) or '').strip().lower()
    if ps in ('paid', 'pending', 'complimentary', 'waived', 'not_required'):
        return ps
    return 'paid' if ps else 'pending'


def _participant_exists(event_id: int, user_id: int | None, email: str | None) -> bool:
    from app import EventParticipant
    from sqlalchemy import func

    if user_id:
        if EventParticipant.query.filter_by(event_id=event_id, user_id=user_id).first():
            return True
    em = (email or '').strip().lower()
    if em:
        row = (
            EventParticipant.query.filter_by(event_id=event_id)
            .filter(func.lower(func.trim(EventParticipant.email)) == em)
            .first()
        )
        if row:
            return True
    return False


def import_participants_from_registrations(
    event_id: int,
    *,
    only_confirmed: bool = True,
    dry_run: bool = False,
) -> dict[str, int]:
    """
    Por cada inscripción del evento crea un participante si no existe (user_id o email).
  Devuelve contadores created / skipped / cancelled_skipped.
    """
    from app import EventParticipant, EventRegistration, User, db

    q = EventRegistration.query.filter_by(event_id=event_id)
    if only_confirmed:
        q = q.filter(EventRegistration.registration_status == 'confirmed')
    regs = q.order_by(EventRegistration.id.asc()).all()

    created = skipped = cancelled_skipped = 0
    for reg in regs:
        if only_confirmed and (reg.registration_status or '').strip().lower() == 'cancelled':
            cancelled_skipped += 1
            continue
        user = User.query.get(reg.user_id) if reg.user_id else None
        if not user:
            skipped += 1
            continue
        email = (user.email or '').strip().lower() or None
        if _participant_exists(event_id, int(user.id), email):
            skipped += 1
            continue
        if dry_run:
            created += 1
            continue
        fn = (user.first_name or '').strip() or None
        ln = (user.last_name or '').strip() or None
        p = EventParticipant(
            event_id=event_id,
            user_id=int(user.id),
            first_name=fn,
            last_name=ln,
            full_name=' '.join(x for x in (fn, ln) if x).strip() or None,
            document_id=(getattr(user, 'cedula_or_passport', None) or '').strip() or None,
            email=email,
            phone=(getattr(user, 'phone', None) or '').strip() or None,
            participant_type='member',
            registration_source='inscripcion_confirmada',
            participation_category='member',
            payment_status=_payment_status_from_registration(reg),
            attendance_status='pending',
            certificate_status='pending',
            attendance_confirmed=False,
            notes=f'Importado desde registro #{reg.id}',
        )
        db.session.add(p)
        created += 1
    if not dry_run and created:
        db.session.commit()
    return {
        'created': created,
        'skipped': skipped,
        'cancelled_skipped': cancelled_skipped,
    }


def count_importable_registrations(event_id: int, *, only_confirmed: bool = True) -> int:
    from app import EventParticipant, EventRegistration, User
    from sqlalchemy import func

    q = EventRegistration.query.filter_by(event_id=event_id)
    if only_confirmed:
        q = q.filter(EventRegistration.registration_status == 'confirmed')
    importable = 0
    for reg in q.all():
        user = User.query.get(reg.user_id) if reg.user_id else None
        if not user:
            continue
        em = (user.email or '').strip().lower()
        if EventParticipant.query.filter_by(event_id=event_id, user_id=user.id).first():
            continue
        if em and (
            EventParticipant.query.filter_by(event_id=event_id)
            .filter(func.lower(func.trim(EventParticipant.email)) == em)
            .first()
        ):
            continue
        importable += 1
    return importable
