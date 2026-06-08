"""Regla de negocio: un usuario + un evento = una sola inscripción pagada activa."""

from __future__ import annotations

REJECTED_DUPLICATE_STATUS = 'rejected_duplicate'
REJECTED_DUPLICATE_REASON = (
    'Duplicado: el usuario ya está inscrito y pagado en este evento.'
)


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
    """Eventos en el carrito (solo para saber a qué evento aplica el pago)."""
    from nodeone.services.payment_event_fulfillment import cart_event_ids

    return cart_event_ids(cart)


def blocked_by_existing_registration(
    payment,
    cart,
    *,
    payer_email: str | None = None,
) -> tuple[bool, int | None, str]:
    """
    ¿Aprobar este pago crearía una inscripción duplicada?
    Devuelve (bloqueado, event_id, mensaje).
    """
    from app import EventRegistration, User

    uid = int(getattr(payment, 'user_id', 0) or 0)
    email = (payer_email or '').strip().lower() or None
    if not email and uid:
        u = User.query.get(uid)
        email = (getattr(u, 'email', None) or '').strip().lower() or None

    for eid in event_ids_in_cart(cart):
        if is_user_already_registered(int(eid), uid, email):
            return True, int(eid), REJECTED_DUPLICATE_REASON

    if not event_ids_in_cart(cart) and uid:
        for reg in EventRegistration.query.filter_by(
            user_id=uid,
            registration_status='confirmed',
            payment_status='paid',
        ).all():
            eid = int(reg.event_id)
            if is_user_already_registered(eid, uid, email):
                return True, eid, REJECTED_DUPLICATE_REASON

    return False, None, ''


def mark_payment_rejected_duplicate(payment, *, reason: str | None = None) -> None:
    from datetime import datetime

    payment.status = REJECTED_DUPLICATE_STATUS
    payment.rejection_reason = reason or REJECTED_DUPLICATE_REASON
    payment.validation_observations = payment.rejection_reason
    payment.validated_at = datetime.utcnow()
