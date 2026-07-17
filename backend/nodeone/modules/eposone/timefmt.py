"""Formatos de fecha/hora EPosOne vía TimeZoneService (política oficial UTC/IANA)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from nodeone.core.timezone_service import TimeZoneService


def to_business_dt(value: Any, tz: Any = None) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, datetime):
        return None
    zone = tz or TimeZoneService.business_zoneinfo(
        TimeZoneService.resolve_organization()
    )
    if isinstance(zone, str):
        zone = TimeZoneService.zoneinfo(zone)
    if value.tzinfo is None:
        # Timestamps Order Domain se persisten en UTC naive.
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(zone)


def format_business_dt(value: Any, fmt: str = '%d/%m %H:%M', tz: Any = None) -> str:
    local = to_business_dt(value, tz=tz)
    if local is None:
        return '—'
    return local.strftime(fmt)
