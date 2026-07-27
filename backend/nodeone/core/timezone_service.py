"""EN1 Platform — TimeZoneService (política oficial UTC / IANA).

Persistencia y APIs: UTC.
Presentación: zona efectiva del usuario (o de la empresa).
Ningún módulo debe implementar conversiones propias.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE = 'America/Panama'
_UTC = timezone.utc

COMMON_IANA_TIMEZONES: tuple[str, ...] = (
    'America/Panama',
    'America/Bogota',
    'America/Lima',
    'America/Mexico_City',
    'America/New_York',
    'America/Chicago',
    'America/Denver',
    'America/Los_Angeles',
    'America/Sao_Paulo',
    'America/Argentina/Buenos_Aires',
    'Europe/Madrid',
    'Europe/London',
    'UTC',
)

_DATE_FMT_MAP = {
    'DD/MM/YYYY': '%d/%m/%Y',
    'MM/DD/YYYY': '%m/%d/%Y',
    'YYYY-MM-DD': '%Y-%m-%d',
}
_TIME_FMT_MAP = {
    '24h': '%H:%M',
    '12h': '%I:%M %p',
}


class TimeZoneService:
    """Único punto oficial de conversión y resolución de zona horaria."""

    @staticmethod
    def validate_iana(name: str | None, *, fallback: str = DEFAULT_TIMEZONE) -> str:
        raw = (name or '').strip() or fallback
        try:
            ZoneInfo(raw)
            return raw
        except (ZoneInfoNotFoundError, KeyError, ValueError):
            return TimeZoneService.validate_iana(fallback, fallback=DEFAULT_TIMEZONE)

    @staticmethod
    def zoneinfo(name: str | None = None) -> ZoneInfo:
        return ZoneInfo(TimeZoneService.validate_iana(name))

    @staticmethod
    def _prefs_from_user(user: Any) -> dict[str, Any]:
        if user is None:
            return {}
        try:
            from models.users import UserSettings

            uid = getattr(user, 'id', None)
            if uid is None:
                return {}
            row = UserSettings.query.filter_by(user_id=int(uid)).first()
            if not row or not row.preferences:
                return {}
            import json

            data = json.loads(row.preferences)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def org_timezone_name(organization: Any = None) -> str:
        if organization is not None:
            name = getattr(organization, 'timezone', None)
            if name:
                return TimeZoneService.validate_iana(str(name))
        env = (os.environ.get('EPOSONE_DEFAULT_TIMEZONE') or '').strip()
        if env:
            return TimeZoneService.validate_iana(env)
        return DEFAULT_TIMEZONE

    @staticmethod
    def effective_timezone_name(
        user: Any = None,
        organization: Any = None,
        *,
        prefs: dict[str, Any] | None = None,
    ) -> str:
        """Orden: user.preferences.timezone → org.timezone → America/Panama."""
        p = prefs if prefs is not None else TimeZoneService._prefs_from_user(user)
        user_tz = (p.get('timezone') or '').strip() if isinstance(p, dict) else ''
        if user_tz:
            return TimeZoneService.validate_iana(user_tz)
        return TimeZoneService.org_timezone_name(organization)

    @staticmethod
    def effective_timezone(
        user: Any = None,
        organization: Any = None,
        *,
        prefs: dict[str, Any] | None = None,
    ) -> ZoneInfo:
        return ZoneInfo(
            TimeZoneService.effective_timezone_name(
                user=user, organization=organization, prefs=prefs
            )
        )

    @staticmethod
    def business_zoneinfo(organization: Any = None) -> ZoneInfo:
        """Zona operativa de negocio (org o env). Sin usuario."""
        return ZoneInfo(TimeZoneService.org_timezone_name(organization))

    @staticmethod
    def resolve_organization(organization: Any = None, organization_id: int | None = None) -> Any:
        if organization is not None:
            return organization
        oid = organization_id
        if oid is None:
            try:
                from flask import has_request_context, session

                if has_request_context():
                    raw = session.get('organization_id')
                    if raw is not None:
                        oid = int(raw)
            except Exception:
                oid = None
        if oid is None:
            return None
        try:
            from models.saas import SaasOrganization

            return SaasOrganization.query.filter_by(id=int(oid)).first()
        except Exception:
            return None

    @staticmethod
    def utc_now_naive() -> datetime:
        return datetime.now(_UTC).replace(tzinfo=None)

    @staticmethod
    def ensure_utc_naive(dt: datetime | None) -> datetime | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt
        return dt.astimezone(_UTC).replace(tzinfo=None)

    @staticmethod
    def to_utc_naive(dt: datetime) -> datetime:
        out = TimeZoneService.ensure_utc_naive(dt)
        if out is None:
            raise ValueError('datetime required')
        return out

    @staticmethod
    def local_to_utc_naive(local_dt: datetime, tz: ZoneInfo | str) -> datetime:
        zone = tz if isinstance(tz, ZoneInfo) else TimeZoneService.zoneinfo(tz)
        if local_dt.tzinfo is None:
            aware = local_dt.replace(tzinfo=zone)
        else:
            aware = local_dt.astimezone(zone)
        return aware.astimezone(_UTC).replace(tzinfo=None)

    @staticmethod
    def utc_naive_to_local(dt: datetime | None, tz: ZoneInfo | str) -> datetime | None:
        if dt is None:
            return None
        zone = tz if isinstance(tz, ZoneInfo) else TimeZoneService.zoneinfo(tz)
        naive = TimeZoneService.ensure_utc_naive(dt)
        if naive is None:
            return None
        return naive.replace(tzinfo=_UTC).astimezone(zone)

    @staticmethod
    def day_bounds_utc_naive(
        date_ymd: str | date | datetime,
        tz: ZoneInfo | str,
    ) -> tuple[datetime, datetime]:
        """Inicio inclusive y fin exclusive del día local, en UTC naive."""
        zone = tz if isinstance(tz, ZoneInfo) else TimeZoneService.zoneinfo(tz)
        if isinstance(date_ymd, datetime):
            d = date_ymd.date()
        elif isinstance(date_ymd, date):
            d = date_ymd
        else:
            raw = str(date_ymd or '').strip()[:10]
            d = datetime.strptime(raw, '%Y-%m-%d').date()
        start_local = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=zone)
        end_local = start_local + timedelta(days=1)
        return (
            TimeZoneService.local_to_utc_naive(start_local, zone),
            TimeZoneService.local_to_utc_naive(end_local, zone),
        )

    @staticmethod
    def offset_iso(tz: ZoneInfo | str, at: datetime | None = None) -> str:
        zone = tz if isinstance(tz, ZoneInfo) else TimeZoneService.zoneinfo(tz)
        moment = at or datetime.now(_UTC)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=_UTC)
        local = moment.astimezone(zone)
        off = local.utcoffset()
        if off is None:
            return '+00:00'
        total = int(off.total_seconds())
        sign = '+' if total >= 0 else '-'
        total = abs(total)
        hours, rem = divmod(total, 3600)
        minutes = rem // 60
        return f'{sign}{hours:02d}:{minutes:02d}'

    @staticmethod
    def to_api_iso(dt: datetime | None) -> str | None:
        if dt is None:
            return None
        naive = TimeZoneService.ensure_utc_naive(dt)
        if naive is None:
            return None
        return naive.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'

    @staticmethod
    def strftime_pattern(date_format: str | None = None, time_format: str | None = None) -> str:
        d = _DATE_FMT_MAP.get((date_format or 'DD/MM/YYYY').strip(), '%d/%m/%Y')
        t = _TIME_FMT_MAP.get((time_format or '24h').strip(), '%H:%M')
        return f'{d} {t}'

    @staticmethod
    def format_local(
        dt_utc_naive: datetime | None,
        tz: ZoneInfo | str,
        date_fmt: str | None = None,
        time_fmt: str | None = None,
        *,
        pattern: str | None = None,
    ) -> str:
        local = TimeZoneService.utc_naive_to_local(dt_utc_naive, tz)
        if local is None:
            return '—'
        fmt = pattern or TimeZoneService.strftime_pattern(date_fmt, time_fmt)
        return local.strftime(fmt)

    @staticmethod
    def sync_session_timezone(
        user: Any = None,
        organization: Any = None,
        *,
        prefs: dict[str, Any] | None = None,
    ) -> str:
        """Escribe session['timezone'] y session['utc_offset']. Devuelve IANA efectiva."""
        from flask import has_request_context, session

        org = TimeZoneService.resolve_organization(organization)
        name = TimeZoneService.effective_timezone_name(user=user, organization=org, prefs=prefs)
        zone = ZoneInfo(name)
        if has_request_context():
            session['timezone'] = name
            session['utc_offset'] = TimeZoneService.offset_iso(zone)
        return name
