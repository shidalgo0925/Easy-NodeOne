from __future__ import annotations

import io
import json
import re
import threading
import time
from collections import deque

from nodeone.modules.qr_generator.schemas import (
    DEFAULT_BG,
    DEFAULT_BORDER_MODULES,
    DEFAULT_FILL,
    MAX_CONTENT_LEN,
    MAX_LOGO_BYTES,
    MAX_LOGO_SIDE_PX,
    MIN_BORDER_MODULES,
    MAX_BORDER_MODULES,
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


_HEX_6 = re.compile(r'^#[0-9a-fA-F]{6}$')
_HEX_3 = re.compile(r'^#[0-9a-fA-F]{3}$')


def normalize_hex_color(raw: str | None, default: str) -> str:
    s = (raw or '').strip()
    if not s:
        return default
    if _HEX_6.match(s):
        return s.lower()
    if _HEX_3.match(s):
        return '#' + ''.join(c * 2 for c in s[1:])
    return default


def effective_error_level(requested: str, has_logo: bool) -> str:
    order = ('L', 'M', 'Q', 'H')
    if not has_logo:
        return requested if requested in order else 'M'
    r = requested if requested in order else 'M'
    ri, qi = order.index(r), order.index('Q')
    return order[max(ri, qi)]


def validate_logo_bytes(raw: bytes | None) -> tuple[bytes | None, str | None]:
    if not raw:
        return None, None
    if len(raw) > MAX_LOGO_BYTES:
        return None, f'El logo supera {MAX_LOGO_BYTES // 1000} KB.'
    try:
        from PIL import Image as PILImage
    except Exception:
        return None, 'Pillow no disponible; no se puede validar el logo.'
    try:
        im = PILImage.open(io.BytesIO(raw))
        im.verify()
        im = PILImage.open(io.BytesIO(raw))
        im.load()
        w, h = im.size
        if max(w, h) > MAX_LOGO_SIDE_PX:
            return None, f'El logo supera {MAX_LOGO_SIDE_PX}px en el lado mayor.'
    except Exception:
        return None, 'Imagen de logo no válida.'
    return raw, None


def parse_border(raw: object) -> int:
    try:
        b = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_BORDER_MODULES
    return max(MIN_BORDER_MODULES, min(MAX_BORDER_MODULES, b))


def build_style_for_generate(
    fill: str,
    bg: str,
    transparent: bool,
    border: int,
    logo_bytes: bytes | None,
) -> dict:
    return {
        'fill': fill,
        'bg': bg,
        'transparent': bool(transparent),
        'border': int(border),
        'logo_bytes': logo_bytes,
    }


def encode_style_json(style: dict) -> str | None:
    """Persistencia en DB (sin logo_bytes en claro; usa logo_b64)."""
    d = {
        'fill': style.get('fill') or DEFAULT_FILL,
        'bg': style.get('bg') or DEFAULT_BG,
        'transparent': bool(style.get('transparent')),
        'border': int(style.get('border') or DEFAULT_BORDER_MODULES),
    }
    lb = style.get('logo_bytes')
    if lb:
        import base64

        d['logo_b64'] = base64.b64encode(lb).decode('ascii')
    return json.dumps(d, separators=(',', ':'))


def decode_style_json(raw: str | None) -> dict:
    """Devuelve dict apto para generate_file (incl. logo_bytes si hubo logo guardado)."""
    if not raw or not str(raw).strip():
        return {}
    try:
        d = json.loads(raw)
    except Exception:
        return {}
    import base64

    out = {
        'fill': normalize_hex_color(d.get('fill'), DEFAULT_FILL),
        'bg': normalize_hex_color(d.get('bg'), DEFAULT_BG),
        'transparent': bool(d.get('transparent')),
        'border': parse_border(d.get('border')),
    }
    b64 = d.get('logo_b64')
    if isinstance(b64, str) and b64.strip():
        try:
            out['logo_bytes'] = base64.b64decode(b64)
        except Exception:
            pass
    return out
