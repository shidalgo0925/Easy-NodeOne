"""
Consultas de eventos para el portal (listado público, carril en /services, banner en home).

Misma lógica que ``nodeone.modules.events.routes`` (organización, publicado, vigencia, visibilidad).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import or_


def portal_events_scoped_query(*, organization_id: int):
    """
    ``Event`` de la org del tenant, unidos al ``User`` creador (``user_in_org_clause``).
    """
    from app import Event, User, default_organization_id
    from nodeone.services.user_organization import user_in_org_clause

    oid = int(organization_id or default_organization_id())
    return Event.query.join(User, Event.created_by == User.id).filter(user_in_org_clause(User, oid))


def apply_portal_list_filters(q, *, user: Any | None):
    """
    Filtros del listado principal: publicado, aún no terminado, visibilidad según sesión.
    """
    from app import Event

    q = q.filter(Event.publish_status == 'published', Event.end_date >= datetime.utcnow())
    _authed = user is not None and getattr(user, 'is_authenticated', False)
    if not _authed:
        return q.filter(Event.visibility == 'public')
    return q.filter(
        or_(
            Event.visibility == 'public',
            Event.visibility == 'members',
            Event.visibility == None,  # noqa: E711
        )
    )


def get_portal_featured_events(*, organization_id: int, user: Any | None, limit: int = 5):
    """
    Próximos eventos publicados visibles, orden: destacados primero, luego por fecha.
    Carril «Próximos eventos» en /services (3–5 ítems).
    """
    from app import Event
    from sqlalchemy.orm import joinedload

    q = portal_events_scoped_query(organization_id=organization_id)
    q = apply_portal_list_filters(q, user=user)
    return (
        q.options(joinedload(Event.images))
        .order_by(Event.featured.desc().nulls_last(), Event.start_date.asc())
        .limit(int(limit))
        .all()
    )


def get_next_featured_portal_event(*, organization_id: int, user: Any | None):
    """
    Un solo evento: publicado, ``featured=True``, vigente, visibilidad según usuario.
    Para bloque destacado en dashboard (flyer + CTA).
    """
    from app import Event
    from sqlalchemy.orm import joinedload

    q = portal_events_scoped_query(organization_id=organization_id)
    q = apply_portal_list_filters(q, user=user)
    q = q.filter(Event.featured == True)  # noqa: E712
    return q.options(joinedload(Event.images)).order_by(Event.start_date.asc()).first()


def count_portal_visible_events(*, organization_id: int, user: Any | None) -> int:
    """Conteo para badge en menú (mismo criterio que /events)."""
    q = portal_events_scoped_query(organization_id=organization_id)
    q = apply_portal_list_filters(q, user=user)
    return int(q.count() or 0)
