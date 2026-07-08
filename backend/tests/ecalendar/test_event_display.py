"""Tests parseo eventos ECalendar V1."""

from nodeone.modules.ecalendar.services.event_display import parse_ecalendar_event


def test_parse_v1_event_title_and_description():
    event = {
        'id': 'abc123',
        'summary': '[Easy Odoo] Demo con Juan Pérez',
        'description': 'Nombre: Juan Pérez\nEmpresa: ACME\nCorreo: juan@test.com\nWhatsApp: +50760000000\nProducto: Easy Odoo\nComentarios: Hola',
        'start': {'dateTime': '2026-06-18T15:00:00-05:00'},
        'end': {'dateTime': '2026-06-18T15:30:00-05:00'},
        'htmlLink': 'https://calendar.google.com/event?eid=abc',
    }
    out = parse_ecalendar_event(event)
    assert out['event_id'] == 'abc123'
    assert out['product'] == 'Easy Odoo'
    assert out['client_name'] == 'Juan Pérez'
    assert out['email'] == 'juan@test.com'
    assert out['phone'] == '+50760000000'
    assert out['is_ecalendar_booking'] is True
