"""Formatos de fecha/hora EPosOne en zona de negocio (America/Panama)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from nodeone.core.commerce.dashboard import business_timezone


def to_business_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, datetime):
        return None
    tz = business_timezone()
    if value.tzinfo is None:
        # Timestamps Order Domain se persisten en UTC naive.
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(tz)


def format_business_dt(value: Any, fmt: str = '%d/%m %H:%M') -> str:
    local = to_business_dt(value)
    if local is None:
        return '—'
    return local.strftime(fmt)
