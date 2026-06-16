"""Generación de slots libres ECalendar."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from nodeone.modules.ecalendar.services.config import ECalendarConfig


def _parse_hhmm(value: str) -> time:
    parts = (value or '09:00').split(':')
    h = int(parts[0]) if len(parts) > 0 else 9
    m = int(parts[1]) if len(parts) > 1 else 0
    return time(hour=h, minute=m)


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


def generate_day_slots(cfg: ECalendarConfig, day: date, now: datetime | None = None) -> list[tuple[datetime, datetime]]:
    """Slots teóricos Lun–Vie dentro del horario laboral (sin consultar Google)."""
    tz = ZoneInfo(cfg.timezone)
    if now is None:
        now = datetime.now(tz)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    else:
        now = now.astimezone(tz)

    if day.weekday() >= 5:
        return []

    earliest_day = now.date()
    latest_day = earliest_day + timedelta(days=cfg.horizon_days)
    if day < earliest_day or day > latest_day:
        return []

    start_t = _parse_hhmm(cfg.business_start)
    end_t = _parse_hhmm(cfg.business_end)
    slot_delta = timedelta(minutes=cfg.slot_minutes)
    lead = timedelta(hours=cfg.lead_hours)

    slots: list[tuple[datetime, datetime]] = []
    cursor = datetime.combine(day, start_t, tzinfo=tz)
    day_end = datetime.combine(day, end_t, tzinfo=tz)
    while cursor + slot_delta <= day_end:
        slot_end = cursor + slot_delta
        if slot_end > now + lead:
            slots.append((cursor, slot_end))
        cursor += slot_delta
    return slots


def filter_available_slots(
    cfg: ECalendarConfig,
    day: date,
    busy: list[tuple[datetime, datetime]],
    now: datetime | None = None,
) -> list[dict[str, str]]:
    tz = ZoneInfo(cfg.timezone)
    out = []
    for start, end in generate_day_slots(cfg, day, now=now):
        if any(_overlaps(start, end, b0, b1) for b0, b1 in busy):
            continue
        out.append({'start': start.isoformat(), 'end': end.isoformat()})
    return out
