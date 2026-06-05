"""Utilidades UTC compatibles con SQLite (naive) y PostgreSQL (aware)."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def utc_seconds_between(later: datetime, earlier: datetime | None) -> float:
    if earlier is None:
        return 0.0
    return (as_utc(later) - as_utc(earlier)).total_seconds()
