"""Tests unitarios de slots ECalendar."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from nodeone.modules.ecalendar.services.availability import filter_available_slots, generate_day_slots
from nodeone.modules.ecalendar.services.config import ECalendarConfig


def _cfg() -> ECalendarConfig:
    return ECalendarConfig(
        enabled=True,
        timezone='America/Panama',
        slot_minutes=30,
        lead_hours=4,
        horizon_days=30,
        business_start='09:00',
        business_end='17:00',
        title_prefix='',
        allowed_origins=(),
        products_json='',
        google_client_id='',
        google_client_secret='',
        google_refresh_token='',
        google_calendar_id='primary',
    )


def test_weekend_returns_no_slots():
    cfg = _cfg()
    # 2026-06-06 is Saturday
    slots = generate_day_slots(cfg, date(2026, 6, 6))
    assert slots == []


def test_weekday_generates_slots():
    cfg = _cfg()
    tz = ZoneInfo('America/Panama')
    now = datetime(2026, 6, 2, 8, 0, tzinfo=tz)
    slots = generate_day_slots(cfg, date(2026, 6, 3), now=now)
    assert len(slots) == 16
    assert slots[0][0].hour == 9
    assert slots[-1][1].hour == 17


def test_lead_time_excludes_near_slots():
    cfg = _cfg()
    tz = ZoneInfo('America/Panama')
    now = datetime(2026, 6, 3, 10, 15, tzinfo=tz)
    slots = generate_day_slots(cfg, date(2026, 6, 3), now=now)
    assert slots
    assert slots[0][0] >= now + timedelta(hours=4)


def test_filter_busy_removes_overlapping():
    cfg = _cfg()
    tz = ZoneInfo('America/Panama')
    day = date(2026, 6, 3)
    now = datetime(2026, 6, 2, 8, 0, tzinfo=tz)
    busy = [
        (
            datetime(2026, 6, 3, 10, 0, tzinfo=tz),
            datetime(2026, 6, 3, 10, 30, tzinfo=tz),
        ),
    ]
    available = filter_available_slots(cfg, day, busy, now=now)
    starts = [s['start'] for s in available]
    assert '2026-06-03T10:00:00-05:00' not in starts
