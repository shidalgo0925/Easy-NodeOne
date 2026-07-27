"""Reintentos con backoff — Etapa 13."""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from nodeone.core.sync.constants import DEFAULT_BASE_RETRY_SECONDS, DEFAULT_MAX_RETRIES


def max_event_retries() -> int:
    raw = (os.environ.get('NODEONE_EVENT_BUS_MAX_RETRIES') or '').strip()
    if not raw:
        return DEFAULT_MAX_RETRIES
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_MAX_RETRIES


def max_sync_operation_retries() -> int:
    raw = (os.environ.get('NODEONE_SYNC_MAX_RETRIES') or '').strip()
    if not raw:
        return DEFAULT_MAX_RETRIES
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_MAX_RETRIES


def compute_next_retry_at(retry_count: int, *, base_seconds: int = DEFAULT_BASE_RETRY_SECONDS) -> datetime:
    """Backoff exponencial: base * 2^(retry-1), tope 1 h."""
    attempt = max(1, int(retry_count))
    delay = min(base_seconds * (2 ** (attempt - 1)), 3600)
    return datetime.utcnow() + timedelta(seconds=delay)


def is_ready_for_retry(next_retry_at: datetime | None) -> bool:
    if next_retry_at is None:
        return True
    return next_retry_at <= datetime.utcnow()
