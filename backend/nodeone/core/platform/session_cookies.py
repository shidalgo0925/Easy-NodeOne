"""Cookie de sesión host-only (por Host).

Tras retirar el Portal en ``app.easytech.services``, ya no se comparte
``Domain=.easytech.services``: esa cookie impedía que el login en hosts de
producto (p. ej. eposone.*) mantuviera la sesión tras el redirect.

Opt-in: ``NODEONE_SESSION_COOKIE_DOMAIN`` (p. ej. ``.easytech.services``).
"""

from __future__ import annotations

import os
import re

from flask.sessions import SecureCookieSessionInterface


_ETS_ROOT = 'easytech.services'
_COOKIE_NAME_RE = re.compile(r'^([^=]+)=')
_LEGACY_ETS_DOMAIN = '.' + _ETS_ROOT


def cookie_domain_for_host(host: str | None) -> str | None:
    """Domain de cookie: None (host-only) salvo ``NODEONE_SESSION_COOKIE_DOMAIN``."""
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
    """Host-only por defecto; Domain solo si hay env opt-in."""

    def get_cookie_domain(self, app):
        return cookie_domain_for_request()


def _rewrite_set_cookie_domain(header_value: str, domain: str, cookie_names: frozenset[str]) -> str:
    m = _COOKIE_NAME_RE.match(header_value or '')
    if not m:
        return header_value
    name = m.group(1).strip()
    if name not in cookie_names:
        return header_value
    parts = [p.strip() for p in header_value.split(';')]
    out = [parts[0]]
    seen_domain = False
    for p in parts[1:]:
        if p.lower().startswith('domain='):
            out.append(f'Domain={domain}')
            seen_domain = True
        else:
            out.append(p)
    if not seen_domain:
        out.append(f'Domain={domain}')
    return '; '.join(out)


def _strip_set_cookie_domain(header_value: str, cookie_names: frozenset[str]) -> str:
    m = _COOKIE_NAME_RE.match(header_value or '')
    if not m:
        return header_value
    name = m.group(1).strip()
    if name not in cookie_names:
        return header_value
    parts = [p.strip() for p in header_value.split(';')]
    out = [parts[0]]
    for p in parts[1:]:
        if p.lower().startswith('domain='):
            continue
        out.append(p)
    return '; '.join(out)


def _expire_legacy_ets_domain_cookie(name: str, *, secure: bool) -> str:
    """Invalida cookie legada Domain=.easytech.services (host-only no la reemplaza)."""
    parts = [
        f'{name}=',
        f'Domain={_LEGACY_ETS_DOMAIN.lstrip(".")}',
        'Expires=Thu, 01 Jan 1970 00:00:00 GMT',
        'Max-Age=0',
        'Path=/',
        'HttpOnly',
        'SameSite=Lax',
    ]
    if secure:
        parts.append('Secure')
    return '; '.join(parts)


def register_host_aware_session_cookies(app) -> None:
    """Session host-only + limpia Domain legado ETS; Domain opt-in vía env."""
    app.session_interface = HostAwareSessionInterface()
    # Evitar que Flask/Flask-Login hereden un Domain de config.
    app.config['SESSION_COOKIE_DOMAIN'] = cookie_domain_for_request()
    app.config['REMEMBER_COOKIE_DOMAIN'] = app.config['SESSION_COOKIE_DOMAIN']

    session_cookie = app.config.get('SESSION_COOKIE_NAME') or 'session'
    remember_cookie = app.config.get('REMEMBER_COOKIE_NAME') or 'remember_token'
    names = frozenset({session_cookie, remember_cookie})

    @app.before_request
    def _sync_cookie_domain_config():
        domain = cookie_domain_for_request()
        app.config['SESSION_COOKIE_DOMAIN'] = domain
        app.config['REMEMBER_COOKIE_DOMAIN'] = domain

    @app.after_request
    def _normalize_session_cookie_domain(response):
        domain = cookie_domain_for_request()
        try:
            raw = list(response.headers.getlist('Set-Cookie') or [])
        except Exception:
            return response

        secure = bool(app.config.get('SESSION_COOKIE_SECURE'))
        try:
            from flask import has_request_context, request

            if has_request_context() and (request.is_secure or (request.headers.get('X-Forwarded-Proto') or '').lower() == 'https'):
                secure = True
        except Exception:
            pass

        host = ''
        try:
            from flask import has_request_context, request

            if has_request_context():
                host = (request.host or '').split(':')[0].strip().lower()
        except Exception:
            host = ''

        is_ets = host == _ETS_ROOT or host.endswith('.' + _ETS_ROOT)
        out: list[str] = []
        touched = False

        if domain:
            for v in raw:
                nv = _rewrite_set_cookie_domain(v, domain, names)
                out.append(nv)
                touched = touched or nv != v
        else:
            for v in raw:
                nv = _strip_set_cookie_domain(v, names)
                out.append(nv)
                touched = touched or nv != v
            # Expira cookie legada compartida (solo en hosts ETS).
            if is_ets and raw:
                for name in names:
                    if any(v.startswith(f'{name}=') for v in raw):
                        out.append(_expire_legacy_ets_domain_cookie(name, secure=secure))
                        touched = True

        if not touched:
            return response
        try:
            del response.headers['Set-Cookie']
        except Exception:
            pass
        for v in out:
            response.headers.add('Set-Cookie', v)
        return response
