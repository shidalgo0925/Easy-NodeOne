"""Sesión de instalación /start — ready token firmado (ADR-035 Standalone)."""

from __future__ import annotations

from typing import Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

READY_SALT = 'eposone-start-ready-v1'
READY_MAX_AGE = 7 * 24 * 3600  # 7 días


def _serializer():
    from flask import current_app

    secret = current_app.config.get('SECRET_KEY') or 'dev-insecure'
    return URLSafeTimedSerializer(str(secret), salt=READY_SALT)


def issue_ready_token(
    *,
    user_id: int,
    organization_id: int,
    activation_token_id: int | None,
    customer_id: int | None = None,
) -> str:
    payload = {
        'uid': int(user_id),
        'oid': int(organization_id),
        'aid': int(activation_token_id) if activation_token_id else None,
        'src': 'eposone_start',
    }
    if customer_id:
        payload['cid'] = int(customer_id)
    return _serializer().dumps(payload)


def load_ready_token(token: str, *, max_age: int = READY_MAX_AGE) -> dict[str, Any]:
    try:
        data = _serializer().loads(token, max_age=max_age)
    except SignatureExpired as exc:
        raise ValueError('ready_token_expired') from exc
    except BadSignature as exc:
        raise ValueError('ready_token_invalid') from exc
    if not isinstance(data, dict) or data.get('src') != 'eposone_start':
        raise ValueError('ready_token_invalid')
    return data
