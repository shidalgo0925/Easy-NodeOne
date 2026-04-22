"""Utilidades sin dependencias de BD (testables en cualquier Python)."""

from __future__ import annotations

import secrets
from datetime import datetime


def verify_landing_api_key(provided: str, expected: str) -> bool:
    if not expected or not provided:
        return False
    return secrets.compare_digest(provided.strip(), expected)


def normalize_idempotency_key(raw: str | None) -> str | None:
    if not raw:
        return None
    s = raw.strip()
    if not s:
        return None
    return s[:128]


def parse_preferred_start_utc(s_date: str, s_time: str) -> datetime | None:
    """
    Combina fecha YYYY-MM-DD y hora HH:MM opcional (naive).
    Sin hora → 09:00.
    """
    d = (s_date or '').strip()[:10]
    t = (s_time or '').strip()[:8]
    if not d or len(d) < 10:
        return None
    try:
        if t and ':' in t:
            parts = t.split(':')
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            sec = int(parts[2]) if len(parts) > 2 else 0
            base = datetime.strptime(d, '%Y-%m-%d')
            return base.replace(hour=h, minute=m, second=sec, microsecond=0)
        return datetime.strptime(d, '%Y-%m-%d').replace(
            hour=9, minute=0, second=0, microsecond=0
        )
    except (ValueError, TypeError, IndexError):
        return None
