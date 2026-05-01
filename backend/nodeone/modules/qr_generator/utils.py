from __future__ import annotations

import re
import threading
import time
from collections import deque

from nodeone.modules.qr_generator.schemas import (
    MAX_CONTENT_LEN,
    RATE_LIMIT_MAX_REQUESTS,
    RATE_LIMIT_WINDOW_SEC,
)

_BAD_SCHEMES = re.compile(r'^\s*(javascript|data|vbscript):', re.I)

_ts_lock = threading.Lock()
_ts_by_key: dict[str, deque[float]] = {}


def sanitize_content(raw: str) -> str:
    return (raw or '').strip()


def validate_qr_content(text: str) -> tuple[str | None, str | None]:
    s = sanitize_content(text)
    if not s:
        return None, 'El contenido está vacío.'
    if len(s) > MAX_CONTENT_LEN:
        return None, f'El contenido supera {MAX_CONTENT_LEN} caracteres.'
    if _BAD_SCHEMES.match(s):
        return None, 'Esquema no permitido.'
    low = s.lower()
    if low.startswith('http://'):
        return None, 'Las URLs deben usar https://.'
    if low.startswith('https://'):
        return s, None
    return s, None


def rate_limit_hit(user_id: int | None, ip: str) -> bool:
    uid = int(user_id or 0)
    key = f'{uid}:{ip or "unknown"}'
    now = time.monotonic()
    window = float(RATE_LIMIT_WINDOW_SEC)
    max_req = int(RATE_LIMIT_MAX_REQUESTS)
    with _ts_lock:
        dq = _ts_by_key.get(key)
        if dq is None:
            dq = deque()
            _ts_by_key[key] = dq
        while dq and now - dq[0] > window:
            dq.popleft()
        if len(dq) >= max_req:
            return True
        dq.append(now)
    return False
