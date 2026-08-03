"""Resolución de organización para certificados de evento."""

from __future__ import annotations


def resolve_event_org_id(event) -> int:
    """Org del creador del evento (multi-tenant)."""
    from nodeone.modules.events.services.certificates import organization_id_for_event

    return int(organization_id_for_event(event) or 1)
