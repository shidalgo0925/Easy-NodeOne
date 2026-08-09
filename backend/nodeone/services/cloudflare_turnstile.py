"""Cloudflare Turnstile — verificación anti-bot en formularios públicos.

Env (opcionales; si faltan, el widget no se muestra y no se exige):
  CLOUDFLARE_TURNSTILE_SITE_KEY
  CLOUDFLARE_TURNSTILE_SECRET_KEY
  CLOUDFLARE_TURNSTILE_ENABLED=1   # forzar off con 0 aunque haya keys
"""

from __future__ import annotations

import os
from typing import Any

import requests

_VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
_TIMEOUT_SEC = 8


def turnstile_site_key() -> str:
    return (os.environ.get('CLOUDFLARE_TURNSTILE_SITE_KEY') or '').strip()


def turnstile_secret_key() -> str:
    return (os.environ.get('CLOUDFLARE_TURNSTILE_SECRET_KEY') or '').strip()


def turnstile_enabled() -> bool:
    flag = (os.environ.get('CLOUDFLARE_TURNSTILE_ENABLED') or '').strip().lower()
    if flag in ('0', 'false', 'no', 'off'):
        return False
    if flag in ('1', 'true', 'yes', 'on'):
        return bool(turnstile_site_key() and turnstile_secret_key())
    # Default: activo solo si ambas keys están
    return bool(turnstile_site_key() and turnstile_secret_key())


def turnstile_template_vars() -> dict[str, Any]:
    enabled = turnstile_enabled()
    return {
        'turnstile_enabled': enabled,
        'turnstile_site_key': turnstile_site_key() if enabled else '',
    }


def verify_turnstile_token(token: str, *, remote_ip: str | None = None) -> tuple[bool, str]:
    """Verifica el token con Cloudflare. Retorna (ok, mensaje_error)."""
    if not turnstile_enabled():
        return True, ''
    tok = (token or '').strip()
    if not tok:
        return False, 'Completá la verificación de seguridad e intentá de nuevo.'
    secret = turnstile_secret_key()
    payload: dict[str, str] = {'secret': secret, 'response': tok}
    if remote_ip:
        payload['remoteip'] = str(remote_ip)
    try:
        resp = requests.post(_VERIFY_URL, data=payload, timeout=_TIMEOUT_SEC)
        data = resp.json() if resp.ok else {}
    except Exception:
        return False, 'No se pudo validar la verificación de seguridad. Reintentá.'
    if bool(data.get('success')):
        return True, ''
    return False, 'Verificación de seguridad fallida. Reintentá.'


def require_turnstile_from_request(request) -> tuple[bool, str]:
    """Lee ``cf-turnstile-response`` del form y verifica."""
    if not turnstile_enabled():
        return True, ''
    token = (request.form.get('cf-turnstile-response') or '').strip()
    ip = None
    try:
        ip = request.headers.get('CF-Connecting-IP') or request.remote_addr
    except Exception:
        ip = None
    return verify_turnstile_token(token, remote_ip=ip)
