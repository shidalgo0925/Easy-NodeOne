"""Regla de negocio: un usuario + un evento = una sola inscripción pagada activa."""

from __future__ import annotations

REJECTED_DUPLICATE_STATUS = 'rejected_duplicate'
REJECTED_DUPLICATE_REASON = (
    'Ya existe una inscripción pagada para este usuario en este evento'
)

PENDING_ADMIN_STATUSES = (
    'pending_receipt',
    'pending_payment',
    'pending_admin_review',
    'pending_validation',
    'manual_review',
    'partially_paid',
)

DEFAULT_RELATIC_EVENT_ID = 2


def is_user_already_registered(
    event_id: int,
    user_id: int | None,
    email: str | None = None,
) -> bool:
    """
    True si existe event_registration confirmed + payment_status=paid
    para el mismo evento y usuario (por user_id o email normalizado).
    """
    from app import EventRegistration, User
    from sqlalchemy import func

    eid = int(event_id)
    q = EventRegistration.query.filter_by(
        event_id=eid,
        registration_status='confirmed',
        payment_status='paid',
    )
    if user_id:
        if q.filter_by(user_id=int(user_id)).first():
            return True
    em = (email or '').strip().lower()
    if em:
        row = (
            q.join(User, EventRegistration.user_id == User.id)
            .filter(func.lower(func.trim(User.email)) == em)
            .first()
        )
        if row:
            return True
    return False


def event_ids_in_cart(cart) -> list[int]:
    from nodeone.services.payment_event_fulfillment import cart_event_ids

    return cart_event_ids(cart)


def should_reject_duplicate_payment(
    payment,
    cart,
    *,
    payer_email: str | None = None,
    event_id: int = DEFAULT_RELATIC_EVENT_ID,
) -> tuple[bool, int | None, str]:
    """¿Este pago pendiente es duplicado porque el usuario ya está inscrito?"""
    from app import User

    uid = int(getattr(payment, 'user_id', 0) or 0)
    email = (payer_email or '').strip().lower() or None
    if not email and uid:
        u = User.query.get(uid)
        email = (getattr(u, 'email', None) or '').strip().lower() or None

    for eid in event_ids_in_cart(cart):
        if is_user_already_registered(int(eid), uid, email):
            return True, int(eid), REJECTED_DUPLICATE_REASON

    if not event_ids_in_cart(cart) and is_user_already_registered(int(event_id), uid, email):
        return True, int(event_id), REJECTED_DUPLICATE_REASON

    return False, None, ''


def mark_payment_rejected_duplicate(payment, *, reason: str | None = None) -> None:
    from datetime import datetime

    payment.status = REJECTED_DUPLICATE_STATUS
    payment.rejection_reason = reason or REJECTED_DUPLICATE_REASON
    payment.validation_observations = payment.rejection_reason
    payment.validated_at = datetime.utcnow()


def purge_duplicate_pending_registrations(
    event_id: int = DEFAULT_RELATIC_EVENT_ID,
) -> dict[str, int]:
    """
    Sacar de Pendientes los pagos cuyo usuario ya tiene inscripción pagada activa.
    Fuente de verdad: event_registration (no payment).
    """
    from app import Payment, User, db

    stats = {'reviewed': 0, 'rejected': 0, 'skipped': 0}
    pending = (
        Payment.query.filter(Payment.status.in_(PENDING_ADMIN_STATUSES))
        .order_by(Payment.id.asc())
        .all()
    )
    for payment in pending:
        stats['reviewed'] += 1
        if (payment.status or '').strip() == REJECTED_DUPLICATE_STATUS:
            stats['skipped'] += 1
            continue
        user = User.query.get(int(payment.user_id))
        email = (getattr(user, 'email', None) or '').strip().lower() or None
        if not is_user_already_registered(int(event_id), int(payment.user_id), email):
            stats['skipped'] += 1
            continue
        mark_payment_rejected_duplicate(payment)
        stats['rejected'] += 1

    if stats['rejected']:
        db.session.commit()
    return stats
