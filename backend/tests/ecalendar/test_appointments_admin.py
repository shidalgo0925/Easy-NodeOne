"""Tests utilidades citas admin ECalendar."""

from nodeone.modules.ecalendar.services.appointments_admin import (
    filter_appointments,
    parse_bookings_only_param,
)


def test_parse_bookings_only_param_defaults_true():
    assert parse_bookings_only_param(None) is True
    assert parse_bookings_only_param('1') is True
    assert parse_bookings_only_param('0') is False
    assert parse_bookings_only_param('false') is False


def test_appointments_to_calendar_events():
    items = [{
        'event_id': 'abc',
        'title': '[Easy Odoo] Demo con Juan',
        'start': '2026-06-18T15:00:00-05:00',
        'end': '2026-06-18T15:30:00-05:00',
        'is_ecalendar_booking': True,
        'product': 'Easy Odoo',
    }]
    from nodeone.modules.ecalendar.services.appointments_admin import appointments_to_calendar_events
    ev = appointments_to_calendar_events(items)
    assert len(ev) == 1
    assert ev[0]['id'] == 'abc'
    assert ev[0]['start'].startswith('2026-06-18')

    items = [
        {'title': 'Demo', 'is_ecalendar_booking': True},
        {'title': 'Comida', 'is_ecalendar_booking': False},
    ]
    assert len(filter_appointments(items, bookings_only=True)) == 1
    assert len(filter_appointments(items, bookings_only=False)) == 2
