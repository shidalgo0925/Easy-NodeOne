"""Cookie de sesión host-only (igual que appprd / EN1).

No se fuerza ``Domain=.easytech.services``: eso rompía el login en hosts de
producto (eposone) tras el redirect. Opt-in: ``NODEONE_SESSION_COOKIE_DOMAIN``.

En hosts ``*.easytech.services`` solo se *añade* un Set-Cookie de expiración
de la cookie legada con Domain padre (sin reescribir la cookie host-only).
"""

from __future__ import annotations

import os

from flask.sessions import SecureCookieSessionInterface


_ETS_ROOT = 'easytech.services'


def cookie_domain_for_host(host: str | None) -> str | None:
    """None = host-only (comportamiento appprd). Env opt-in para Domain compartido."""
    env = (os.environ.get('NODEONE_SESSION_COOKIE_DOMAIN') or '').strip()
    return env or None


def cookie_domain_for_request() -> str | None:
    try:
        from flask import has_request_context, request

        if not has_request_context():
            return None
        return cookie_domain_for_host(request.host)
    except Exception:
        return None


class HostAwareSessionInterface(SecureCookieSessionInterface):
    """Misma política que Flask por defecto, salvo Domain opt-in por env."""

    def get_cookie_domain(self, app):
        domain = cookie_domain_for_request()
        if domain is not None:
            return domain
        # Host-only explícito (no heredar SESSION_COOKIE_DOMAIN de config).
        return None


def _expire_legacy_ets_domain_cookie(name: str, *, secure: bool) -> str:
    parts = [
        f'{name}=',
        f'Domain={_ETS_ROOT}',
        'Expires=Thu, 01 Jan 1970 00:00:00 GMT',
        'Max-Age=0',
        'Path=/',
        'HttpOnly',
        'SameSite=Lax',
    ]
    if secure:
        parts.append('Secure')
    return '; '.join(parts)


def _request_is_ets_host() -> bool:
    try:
        from flask import has_request_context, request

        if not has_request_context():
            return False
        host = (request.host or '').split(':')[0].strip().lower()
        return host == _ETS_ROOT or host.endswith('.' + _ETS_ROOT)
    except Exception:
        return False


def _request_wants_secure_cookie(app) -> bool:
    if bool(app.config.get('SESSION_COOKIE_SECURE')):
        return True
    try:
        from flask import has_request_context, request

        if not has_request_context():
            return False
        if request.is_secure:
            return True
        return (request.headers.get('X-Forwarded-Proto') or '').split(',')[0].strip().lower() == 'https'
    except Exception:
        return False


def register_host_aware_session_cookies(app) -> None:
    """Host-only como appprd; limpia cookie Domain legada en ETS sin tocar la nueva."""
    app.session_interface = HostAwareSessionInterface()
    # Alinear con appprd: sin Domain de sesión/remember salvo env.
    if not (os.environ.get('NODEONE_SESSION_COOKIE_DOMAIN') or '').strip():
        app.config['SESSION_COOKIE_DOMAIN'] = None
        app.config['REMEMBER_COOKIE_DOMAIN'] = None

    session_cookie = app.config.get('SESSION_COOKIE_NAME') or 'session'
    remember_cookie = app.config.get('REMEMBER_COOKIE_NAME') or 'remember_token'
    names = (session_cookie, remember_cookie)

    @app.after_request
    def _expire_legacy_ets_parent_domain_cookies(response):
        # Solo hosts producto ETS; no mutar Set-Cookie existentes (appprd no pasa por aquí).
        if cookie_domain_for_request() is not None:
            return response
        if not _request_is_ets_host():
            return response
        secure = _request_wants_secure_cookie(app)
        for name in names:
            response.headers.add(
                'Set-Cookie',
                _expire_legacy_ets_domain_cookie(name, secure=secure),
            )
        return response
