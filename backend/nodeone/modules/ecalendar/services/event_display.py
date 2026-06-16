"""Parseo de eventos Google Calendar creados por ECalendar V1."""

from __future__ import annotations

import re
from typing import Any

_TITLE_RE = re.compile(
    r'^(?:\[[^\]]+\]\s*)?\[([^\]]+)\]\s*Demo con\s+(.+)$',
    re.IGNORECASE,
)
_FIELD_RE = re.compile(r'^([^:]+):\s*(.*)$')


def _parse_description_fields(description: str | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in (description or '').splitlines():
        line = line.strip()
        if not line:
            continue
        m = _FIELD_RE.match(line)
        if not m:
            continue
        key = m.group(1).strip().lower()
        val = m.group(2).strip()
        if val and val != '—':
            out[key] = val
    return out


def parse_ecalendar_event(event: dict[str, Any]) -> dict[str, Any]:
    """Normaliza un evento GCal API para el dashboard admin."""
    summary = (event.get('summary') or '').strip()
    description = event.get('description') or ''
    fields = _parse_description_fields(description)

    product = fields.get('producto', '')
    client_name = fields.get('nombre', '')
    m = _TITLE_RE.match(summary)
    if m:
        if not product:
            product = m.group(1).strip()
        if not client_name:
            client_name = m.group(2).strip()

    start = event.get('start') or {}
    end = event.get('end') or {}
    start_iso = start.get('dateTime') or start.get('date') or ''
    end_iso = end.get('dateTime') or end.get('date') or ''

    html_link = (event.get('htmlLink') or '').strip()
    event_id = (event.get('id') or '').strip()

    return {
        'event_id': event_id,
        'title': summary,
        'product': product,
        'client_name': client_name,
        'email': fields.get('correo', ''),
        'phone': fields.get('whatsapp', '') or fields.get('teléfono', '') or fields.get('telefono', ''),
        'company': fields.get('empresa', ''),
        'notes': fields.get('comentarios', ''),
        'start': start_iso,
        'end': end_iso,
        'google_event_link': html_link,
        'is_ecalendar_booking': bool(m or fields.get('correo')),
    }
