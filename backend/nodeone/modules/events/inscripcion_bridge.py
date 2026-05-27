"""Puente /inscripcion/evento-* ↔ Event (mismo patrón URL que programas académicos)."""
from __future__ import annotations

EVENT_INSCRIPCION_PREFIXES: tuple[str, ...] = (
    'evento-profesional-',
    'evento-personal-',
)


def is_event_inscripcion_slug(slug: str | None) -> bool:
    s = (slug or '').strip().lower()
    return any(s.startswith(p) for p in EVENT_INSCRIPCION_PREFIXES)


def find_event_for_inscripcion(slug: str, *, allow_draft_preview: bool = True):
    """
    Resuelve Event por slug evento-*.
    Publicados: visibles a todos. Borradores: solo staff (admin del catálogo).
    """
    from app import Event

    s = (slug or '').strip().lower()
    if not is_event_inscripcion_slug(s):
        return None
    event = Event.query.filter_by(slug=s).first()
    if event is None:
        return None
    if (event.publish_status or 'draft').lower() == 'published':
        return event
    if not allow_draft_preview:
        return None
    try:
        from nodeone.modules.academic_enrollment.catalog_public import catalog_can_manage_programs

        if catalog_can_manage_programs():
            return event
    except Exception:
        pass
    return None


def event_detail_context(event):
    """Contexto compartido para ficha de evento ( /events/ y /inscripcion/evento-* )."""
    from flask_login import current_user

    from nodeone.modules.events.routes import EventRegistration, ensure_models

    ensure_models()
    membership = current_user.get_active_membership() if current_user.is_authenticated else None
    membership_type = membership.membership_type if membership else 'basic'
    pricing = event.pricing_for_membership(membership_type)

    registration = None
    if current_user.is_authenticated and EventRegistration:
        registration = EventRegistration.query.filter_by(
            event_id=event.id,
            user_id=current_user.id,
        ).first()

    is_full = False
    available_spots = None
    if event.capacity and event.capacity > 0 and EventRegistration:
        registered_count = EventRegistration.query.filter_by(
            event_id=event.id,
            registration_status='confirmed',
        ).count()
        available_spots = event.capacity - registered_count
        is_full = available_spots <= 0

    return {
        'event': event,
        'membership': membership,
        'pricing': pricing,
        'registration': registration,
        'is_full': is_full,
        'available_spots': available_spots,
        'inscripcion_landing': True,
    }


def render_event_inscripcion_landing(event):
    from flask import render_template

    return render_template('events/detail.html', **event_detail_context(event))
