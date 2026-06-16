"""Listado y cancelación de citas ECalendar V1 (Google Calendar)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, NamedTuple
from zoneinfo import ZoneInfo

from nodeone.modules.ecalendar.services.config import ECalendarConfig, load_ecalendar_config
from nodeone.modules.ecalendar.services.event_display import parse_ecalendar_event
from nodeone.modules.ecalendar.services.google_calendar import (
    GoogleCalendarError,
    delete_event,
    list_upcoming_events,
    oauth_valid,
)

DEV_APPOINTMENTS_ORG_NAME = 'Easy NodeOne - Dev'

ERROR_MESSAGES: dict[str, str] = {
    'ecalendar_disabled': 'ECalendar no está activado.',
    'google_not_configured': 'Faltan credenciales Google.',
    'oauth_invalid': 'OAuth no válido. Revisá /admin/ecalendar.',
    'google_api_error': 'Error al consultar Google Calendar.',
    'event_not_found': 'La cita ya no existe en Google Calendar.',
    'missing_event_id': 'ID de evento inválido.',
}


class AppointmentsView(NamedTuple):
    cfg: ECalendarConfig
    org_id: int
    org_name: str
    all_items: list[dict[str, Any]]
    visible_items: list[dict[str, Any]]
    error: str | None
    bookings_only: bool

    @property
    def total_events(self) -> int:
        return len(self.all_items)

    @property
    def bookings_count(self) -> int:
        return sum(1 for item in self.all_items if item.get('is_ecalendar_booking'))

    @property
    def error_message(self) -> str | None:
        if not self.error:
            return None
        return error_message(self.error)


def error_message(code: str | None) -> str | None:
    if not code:
        return None
    return ERROR_MESSAGES.get(code, code)


def error_http_status(code: str) -> int:
    if code == 'event_not_found':
        return 404
    if code in ('ecalendar_disabled', 'google_not_configured', 'oauth_invalid'):
        return 503
    return 502


WEEKDAYS_ES = ('lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom')
MONTHS_ES = ('ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic')


def format_appointment_datetime(start_iso: str, tz_name: str) -> tuple[str, str]:
    if not start_iso:
        return '—', '—'
    try:
        tz = ZoneInfo(tz_name)
        dt = datetime.fromisoformat(start_iso.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        else:
            dt = dt.astimezone(tz)
        date_s = f'{WEEKDAYS_ES[dt.weekday()]}, {dt.day:02d} {MONTHS_ES[dt.month - 1]} {dt.year}'
        return date_s, dt.strftime('%H:%M')
    except (TypeError, ValueError):
        return start_iso, ''


def enrich_appointments_display(
    items: list[dict[str, Any]],
    *,
    tz_name: str,
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for item in items:
        row = dict(item)
        row['display_date'], row['display_time'] = format_appointment_datetime(
            row.get('start') or '',
            tz_name,
        )
        enriched.append(row)
    return enriched


def appointments_to_calendar_events(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Eventos en formato FullCalendar."""
    events: list[dict[str, Any]] = []
    for item in items:
        start = (item.get('start') or '').strip()
        if not start:
            continue
        end = (item.get('end') or '').strip() or start
        is_booking = bool(item.get('is_ecalendar_booking'))
        events.append({
            'id': item.get('event_id'),
            'title': item.get('title') or 'Cita',
            'start': start,
            'end': end,
            'backgroundColor': '#2563eb' if is_booking else '#64748b',
            'borderColor': '#1d4ed8' if is_booking else '#475569',
            'extendedProps': {
                'product': item.get('product') or '',
                'client_name': item.get('client_name') or '',
                'email': item.get('email') or '',
                'phone': item.get('phone') or '',
                'company': item.get('company') or '',
                'google_event_link': item.get('google_event_link') or '',
                'is_ecalendar_booking': is_booking,
            },
        })
    return events


def parse_bookings_only_param(raw: str | None, *, default: bool = True) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() not in ('0', 'false', 'no')


def filter_appointments(items: list[dict[str, Any]], *, bookings_only: bool) -> list[dict[str, Any]]:
    if not bookings_only:
        return items
    return [item for item in items if item.get('is_ecalendar_booking')]


def resolve_dev_appointments_org() -> tuple[int, str]:
    """Citas del landing: tenant Easy NodeOne - Dev (org operativa en appdev)."""
    from models.saas import SaasOrganization

    row = SaasOrganization.query.filter_by(name=DEV_APPOINTMENTS_ORG_NAME).first()
    if row is not None:
        return int(row.id), str(row.name)
    return 1, DEV_APPOINTMENTS_ORG_NAME


def load_dev_appointments_config() -> tuple[ECalendarConfig, int, str]:
    org_id, org_name = resolve_dev_appointments_org()
    return load_ecalendar_config(organization_id=org_id), org_id, org_name


def _cfg_error(cfg: ECalendarConfig) -> str | None:
    if not cfg.enabled:
        return 'ecalendar_disabled'
    if not cfg.google_configured:
        return 'google_not_configured'
    if not oauth_valid(cfg):
        return 'oauth_invalid'
    return None


def query_dev_appointments_for_dashboard() -> list[dict[str, Any]]:
    """Eventos Google Calendar del tenant ECalendar (30 días) para el dashboard admin."""
    view = query_dev_appointments(bookings_only=False)
    if view.error:
        return []
    events = appointments_to_calendar_events(view.visible_items)
    for ev in events:
        props = dict(ev.get('extendedProps') or {})
        props['type'] = 'ecalendar'
        ev['extendedProps'] = props
    return events


def query_dev_appointments(*, bookings_only: bool) -> AppointmentsView:
    cfg, org_id, org_name = load_dev_appointments_config()
    items, err = list_admin_appointments(cfg)
    all_items = enrich_appointments_display(items or [], tz_name=cfg.timezone)
    visible_items = filter_appointments(all_items, bookings_only=bookings_only)
    return AppointmentsView(
        cfg=cfg,
        org_id=org_id,
        org_name=org_name,
        all_items=all_items,
        visible_items=visible_items,
        error=err,
        bookings_only=bookings_only,
    )


def list_admin_appointments(cfg: ECalendarConfig) -> tuple[list[dict[str, Any]] | None, str | None]:
    err = _cfg_error(cfg)
    if err:
        return None, err

    tz = ZoneInfo(cfg.timezone)
    now = datetime.now(tz)
    time_max = now + timedelta(days=cfg.horizon_days)

    try:
        raw_events = list_upcoming_events(cfg, time_min=now, time_max=time_max)
    except GoogleCalendarError:
        return None, 'google_api_error'

    items: list[dict[str, Any]] = []
    for ev in raw_events:
        if ev.get('status') == 'cancelled':
            continue
        start = ev.get('start') or {}
        if not start.get('dateTime'):
            continue
        items.append(parse_ecalendar_event(ev))

    items.sort(key=lambda x: x.get('start') or '')
    return items, None


def cancel_admin_appointment(cfg: ECalendarConfig, event_id: str) -> str | None:
    err = _cfg_error(cfg)
    if err:
        return err
    try:
        delete_event(cfg, event_id)
    except GoogleCalendarError as ex:
        if ex.status_code == 404:
            return 'event_not_found'
        return 'google_api_error'
    return None
