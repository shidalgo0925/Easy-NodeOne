"""Recuperación de contraseña — token hasheado, un uso, rate limit (sin deps nuevas)."""

from __future__ import annotations

import hashlib
import secrets
import threading
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Any

from models.password_reset import PasswordResetToken
from models.users import User

# Mensaje único (anti-enumeración)
GENERIC_REQUEST_MESSAGE = (
    'Si existe una cuenta asociada a ese correo, recibirás un enlace para restablecer tu contraseña.'
)

TOKEN_TTL_MINUTES = 45
MIN_PASSWORD_LENGTH = 8
RATE_LIMIT_WINDOW_SEC = 3600
RATE_LIMIT_MAX_PER_EMAIL = 5
RATE_LIMIT_MAX_PER_IP = 15

_ts_lock = threading.Lock()
_ts_by_key: dict[str, deque[float]] = {}


class PasswordResetError(ValueError):
    """Error de validación en recuperación de contraseña."""


def hash_token(raw_token: str) -> str:
    return hashlib.sha256((raw_token or '').encode('utf-8')).hexdigest()


def password_fingerprint(user: User) -> str:
    """Huella de password_hash para invalidar sesiones tras cambio."""
    raw = (getattr(user, 'password_hash', None) or '').encode('utf-8')
    return hashlib.sha256(raw).hexdigest()[:24]


def validate_new_password(password: str, confirm: str) -> None:
    pwd = (password or '').strip()
    conf = (confirm or '').strip()
    if not pwd:
        raise PasswordResetError('password_required')
    if len(pwd) < MIN_PASSWORD_LENGTH:
        raise PasswordResetError('password_too_short')
    if pwd != conf:
        raise PasswordResetError('password_mismatch')


def _rate_limit_hit(key: str, max_req: int) -> bool:
    now = time.monotonic()
    window = float(RATE_LIMIT_WINDOW_SEC)
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


def is_rate_limited(*, email: str, ip: str | None) -> bool:
    email_key = f'email:{(email or "").strip().lower()}'
    ip_key = f'ip:{(ip or "unknown").strip()}'
    if _rate_limit_hit(email_key, RATE_LIMIT_MAX_PER_EMAIL):
        return True
    if _rate_limit_hit(ip_key, RATE_LIMIT_MAX_PER_IP):
        return True
    return False


def _client_ip(request) -> str | None:
    if request is None:
        return None
    forwarded = (request.headers.get('X-Forwarded-For') or '').split(',')[0].strip()
    return forwarded or (request.remote_addr or None)


def _user_agent(request) -> str | None:
    if request is None:
        return None
    ua = (request.headers.get('User-Agent') or '').strip()
    return ua[:500] if ua else None


def issue_reset_token(
    user: User,
    *,
    request: Any = None,
) -> str:
    """Invalida tokens previos del usuario, crea uno nuevo y devuelve el token en claro (solo para el correo)."""
    from app import db

    now = datetime.utcnow()
    # Invalidar activos previos
    prev = (
        PasswordResetToken.query.filter_by(user_id=int(user.id))
        .filter(PasswordResetToken.used_at.is_(None))
        .filter(PasswordResetToken.expires_at > now)
        .all()
    )
    for row in prev:
        row.used_at = now

    # Limpiar columnas legacy en User
    user.password_reset_token = None
    user.password_reset_token_expires = None
    user.password_reset_sent_at = now

    raw = secrets.token_urlsafe(32)
    row = PasswordResetToken(
        user_id=int(user.id),
        token_hash=hash_token(raw),
        expires_at=now + timedelta(minutes=TOKEN_TTL_MINUTES),
        used_at=None,
        created_at=now,
        ip=_client_ip(request),
        user_agent=_user_agent(request),
    )
    db.session.add(row)
    db.session.commit()
    return raw


def find_valid_token(raw_token: str) -> tuple[PasswordResetToken, User] | None:
    token = (raw_token or '').strip()
    if not token:
        return None
    th = hash_token(token)
    row = PasswordResetToken.query.filter_by(token_hash=th).first()
    if row is None:
        return None
    if row.used_at is not None:
        return None
    if row.expires_at < datetime.utcnow():
        return None
    user = User.query.get(int(row.user_id))
    if user is None or not user.is_active:
        return None
    return row, user


def find_valid_token_with_legacy(raw_token: str) -> tuple[PasswordResetToken | None, User] | None:
    """Resuelve token hasheado o legacy plaintext en User."""
    found = find_valid_token(raw_token)
    if found is not None:
        return found

    token = (raw_token or '').strip()
    if not token:
        return None
    user = User.query.filter_by(password_reset_token=token).first()
    if user is None or not user.is_active:
        return None
    if user.password_reset_token_expires and user.password_reset_token_expires < datetime.utcnow():
        from app import db

        user.password_reset_token = None
        user.password_reset_token_expires = None
        db.session.commit()
        return None
    return None, user


def consume_token_and_set_password(
    raw_token: str,
    new_password: str,
    confirm_password: str,
) -> User:
    from app import db

    validate_new_password(new_password, confirm_password)
    resolved = find_valid_token_with_legacy(raw_token)
    if resolved is None:
        raise PasswordResetError('token_invalid')

    row, user = resolved
    user.set_password(new_password.strip())
    user.must_change_password = False
    user.password_reset_token = None
    user.password_reset_token_expires = None
    user.password_reset_sent_at = None

    now = datetime.utcnow()
    if row is not None:
        row.used_at = now
        # Invalidar otros tokens activos del mismo usuario
        others = (
            PasswordResetToken.query.filter_by(user_id=int(user.id))
            .filter(PasswordResetToken.used_at.is_(None))
            .filter(PasswordResetToken.id != row.id)
            .all()
        )
        for other in others:
            other.used_at = now
    else:
        # Legacy: marcar cualquier token hasheado activo
        actives = (
            PasswordResetToken.query.filter_by(user_id=int(user.id))
            .filter(PasswordResetToken.used_at.is_(None))
            .all()
        )
        for other in actives:
            other.used_at = now

    db.session.commit()
    return user


def build_reset_url(base_url: str, raw_token: str) -> str:
    base = (base_url or '').rstrip('/')
    return f'{base}/reset-password?token={raw_token}'
