"""Creación de reservas ECalendar."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from nodeone.modules.ecalendar.products import product_by_id
from nodeone.modules.ecalendar.services.availability import filter_available_slots, generate_day_slots
from nodeone.modules.ecalendar.services.config import ECalendarConfig
from nodeone.modules.ecalendar.services.google_calendar import (
    GoogleCalendarError,
    create_event,
    list_busy_intervals,
)

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def _parse_slot_start(raw: str, cfg: ECalendarConfig) -> datetime:
    tz = ZoneInfo(cfg.timezone)
    dt = datetime.fromisoformat((raw or '').replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def build_event_title(cfg: ECalendarConfig, product_name: str, guest_name: str) -> str:
    title = f'[{product_name}] Demo con {guest_name}'
    if cfg.title_prefix:
        title = f'{cfg.title_prefix} {title}'
    return title[:200]


def validate_booking_payload(
    data: dict[str, Any],
    *,
    products_json: str | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    product_id = (data.get('product_id') or '').strip()
    product = product_by_id(product_id, products_json)
    if not product:
        return None, 'invalid_product'
    name = (data.get('name') or '').strip()
    if len(name) < 2:
        return None, 'invalid_name'
    email = (data.get('email') or '').strip().lower()
    if not _EMAIL_RE.match(email):
        return None, 'invalid_email'
    slot_start_raw = (data.get('slot_start') or '').strip()
    if not slot_start_raw:
        return None, 'invalid_slot_start'
    whatsapp = (data.get('whatsapp') or data.get('phone') or '').strip()
    return {
        'product': product,
        'name': name,
        'email': email,
        'whatsapp': whatsapp,
        'company': (data.get('company') or '').strip(),
        'notes': (data.get('notes') or data.get('comments') or '').strip(),
        'slot_start_raw': slot_start_raw,
    }, None


def slot_is_available(cfg: ECalendarConfig, slot_start: datetime, slot_end: datetime) -> bool:
    tz = ZoneInfo(cfg.timezone)
    day = slot_start.astimezone(tz).date()
    theoretical = generate_day_slots(cfg, day, now=datetime.now(tz))
    if not any(s == slot_start and e == slot_end for s, e in theoretical):
        return False
    day_start = datetime.combine(day, datetime.min.time(), tzinfo=tz)
    day_end = day_start + timedelta(days=1)
    busy = list_busy_intervals(cfg, time_min=day_start, time_max=day_end)
    available = filter_available_slots(cfg, day, busy, now=datetime.now(tz))
    key = slot_start.isoformat()
    return any(item['start'] == key for item in available)


def create_booking(cfg: ECalendarConfig, data: dict[str, Any]) -> tuple[dict[str, Any] | None, int, str | None]:
    parsed, err = validate_booking_payload(data, products_json=cfg.products_json)
    if err:
        return None, 400, err
    assert parsed is not None
    try:
        slot_start = _parse_slot_start(parsed['slot_start_raw'], cfg)
    except ValueError:
        return None, 400, 'invalid_slot_start'
    slot_end = slot_start + timedelta(minutes=cfg.slot_minutes)

    if not cfg.enabled:
        return None, 503, 'ecalendar_disabled'
    if not cfg.google_configured:
        return None, 503, 'google_not_configured'

    if not slot_is_available(cfg, slot_start, slot_end):
        return None, 409, 'slot_unavailable'

    title = build_event_title(cfg, parsed['product']['name'], parsed['name'])
    description = '\n'.join([
        f"Nombre: {parsed['name']}",
        f"Empresa: {parsed['company'] or '—'}",
        f"Correo: {parsed['email']}",
        f"WhatsApp: {parsed['whatsapp'] or '—'}",
        f"Producto: {parsed['product']['name']}",
        f"Comentarios: {parsed['notes'] or '—'}",
    ])

    try:
        event = create_event(
            cfg,
            title=title,
            start=slot_start,
            end=slot_end,
            attendee_email=parsed['email'],
            description=description,
        )
    except GoogleCalendarError as ex:
        if ex.status_code == 409:
            return None, 409, 'slot_unavailable'
        return None, 502, 'google_api_error'

    return {
        'ok': True,
        'booking_id': event.get('id'),
        'title': title,
        'slot_start': slot_start.isoformat(),
        'slot_end': slot_end.isoformat(),
    }, 201, None
