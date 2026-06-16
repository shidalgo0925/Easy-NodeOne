"""Cliente Google Calendar API (OAuth refresh token)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests

from nodeone.modules.ecalendar.services.config import ECalendarConfig

_TOKEN_URL = 'https://oauth2.googleapis.com/token'
_API_BASE = 'https://www.googleapis.com/calendar/v3'


class GoogleCalendarError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def oauth_valid(cfg: ECalendarConfig) -> bool:
    """True si el refresh token produce access token."""
    if not cfg.google_configured:
        return False
    try:
        _access_token(cfg)
        return True
    except GoogleCalendarError:
        return False


def _access_token(cfg: ECalendarConfig) -> str:
    resp = requests.post(
        _TOKEN_URL,
        data={
            'client_id': cfg.google_client_id,
            'client_secret': cfg.google_client_secret,
            'refresh_token': cfg.google_refresh_token,
            'grant_type': 'refresh_token',
        },
        timeout=30,
    )
    if resp.status_code >= 400:
        raise GoogleCalendarError(f'oauth_refresh_failed: {resp.text[:200]}', resp.status_code)
    data = resp.json()
    token = (data.get('access_token') or '').strip()
    if not token:
        raise GoogleCalendarError('oauth_no_access_token')
    return token


def _headers(cfg: ECalendarConfig) -> dict[str, str]:
    return {
        'Authorization': f'Bearer {_access_token(cfg)}',
        'Content-Type': 'application/json',
    }


def list_busy_intervals(
    cfg: ECalendarConfig,
    *,
    time_min: datetime,
    time_max: datetime,
) -> list[tuple[datetime, datetime]]:
    """Devuelve intervalos ocupados en el calendario configurado."""
    body = {
        'timeMin': time_min.isoformat(),
        'timeMax': time_max.isoformat(),
        'timeZone': cfg.timezone,
        'items': [{'id': cfg.google_calendar_id}],
    }
    resp = requests.post(
        f'{_API_BASE}/freeBusy',
        headers=_headers(cfg),
        json=body,
        timeout=30,
    )
    if resp.status_code >= 400:
        raise GoogleCalendarError(f'freebusy_failed: {resp.text[:200]}', resp.status_code)
    data = resp.json()
    cal = (data.get('calendars') or {}).get(cfg.google_calendar_id) or {}
    busy = []
    tz = ZoneInfo(cfg.timezone)
    for block in cal.get('busy') or []:
        start_s = (block.get('start') or '').strip()
        end_s = (block.get('end') or '').strip()
        if not start_s or not end_s:
            continue
        start = datetime.fromisoformat(start_s.replace('Z', '+00:00')).astimezone(tz)
        end = datetime.fromisoformat(end_s.replace('Z', '+00:00')).astimezone(tz)
        busy.append((start, end))
    return busy


def create_event(
    cfg: ECalendarConfig,
    *,
    title: str,
    start: datetime,
    end: datetime,
    attendee_email: str,
    description: str = '',
) -> dict[str, Any]:
    tz = ZoneInfo(cfg.timezone)
    if start.tzinfo is None:
        start = start.replace(tzinfo=tz)
    if end.tzinfo is None:
        end = end.replace(tzinfo=tz)
    event = {
        'summary': title,
        'description': description,
        'start': {'dateTime': start.isoformat(), 'timeZone': cfg.timezone},
        'end': {'dateTime': end.isoformat(), 'timeZone': cfg.timezone},
        'attendees': [{'email': attendee_email}],
    }
    resp = requests.post(
        f'{_API_BASE}/calendars/{cfg.google_calendar_id}/events',
        headers=_headers(cfg),
        json=event,
        params={'sendUpdates': 'all'},
        timeout=30,
    )
    if resp.status_code == 409:
        raise GoogleCalendarError('slot_conflict', 409)
    if resp.status_code >= 400:
        raise GoogleCalendarError(f'create_event_failed: {resp.text[:200]}', resp.status_code)
    return resp.json()


def _calendar_events_url(cfg: ECalendarConfig, suffix: str = '') -> str:
    from urllib.parse import quote

    cal_id = quote(cfg.google_calendar_id or 'primary', safe='')
    base = f'{_API_BASE}/calendars/{cal_id}/events'
    if suffix:
        return f'{base}/{quote(suffix, safe="")}'
    return base


def list_upcoming_events(
    cfg: ECalendarConfig,
    *,
    time_min: datetime,
    time_max: datetime,
    max_results: int = 100,
) -> list[dict[str, Any]]:
    """Lista eventos del calendario configurado (singleEvents, ordenados por inicio)."""
    params = {
        'timeMin': time_min.isoformat(),
        'timeMax': time_max.isoformat(),
        'singleEvents': 'true',
        'orderBy': 'startTime',
        'maxResults': str(max(1, min(max_results, 250))),
    }
    resp = requests.get(
        _calendar_events_url(cfg),
        headers=_headers(cfg),
        params=params,
        timeout=30,
    )
    if resp.status_code >= 400:
        raise GoogleCalendarError(f'list_events_failed: {resp.text[:200]}', resp.status_code)
    data = resp.json()
    return list(data.get('items') or [])


def delete_event(cfg: ECalendarConfig, event_id: str) -> None:
    """Elimina un evento del calendario configurado."""
    eid = (event_id or '').strip()
    if not eid:
        raise GoogleCalendarError('missing_event_id', 400)
    resp = requests.delete(
        _calendar_events_url(cfg, eid),
        headers=_headers(cfg),
        params={'sendUpdates': 'all'},
        timeout=30,
    )
    if resp.status_code == 404:
        raise GoogleCalendarError('event_not_found', 404)
    if resp.status_code >= 400:
        raise GoogleCalendarError(f'delete_event_failed: {resp.text[:200]}', resp.status_code)
