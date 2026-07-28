"""Cookie de sesión compartida entre hosts de producto ETS (*.easytech.services).

En hosts EN1 (*.easynodeone.com) la cookie sigue siendo host-only.
"""

from __future__ import annotations

import os
import re

from flask.sessions import SecureCookieSessionInterface


_ETS_ROOT = 'easytech.services'
_COOKIE_NAME_RE = re.compile(r'^([^=]+)=')


def cookie_domain_for_host(host: str | None) -> str | None:
    """`.easytech.services` si el request es del ecosistema ETS; si no, None."""
    h = (host or '').split(':')[0].strip().lower()
    if not h:
        return None
    if h == _ETS_ROOT or h.endswith('.' + _ETS_ROOT):
        return '.' + _ETS_ROOT
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
    """Domain de cookie según Host (ETS compartido / EN1 host-only)."""

    def get_cookie_domain(self, app):
        domain = cookie_domain_for_request()
        if domain is not None:
            return domain
        return super().get_cookie_domain(app)


def _rewrite_set_cookie_domain(header_value: str, domain: str, cookie_names: frozenset[str]) -> str:
    m = _COOKIE_NAME_RE.match(header_value or '')
    if not m:
        return header_value
    name = m.group(1).strip()
    if name not in cookie_names:
        return header_value
    # Re-parse loosely: if Domain already present, replace; else append.
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


def register_host_aware_session_cookies(app) -> None:
    """Activa interface de sesión + Domain en remember cookie (Flask-Login)."""
    app.session_interface = HostAwareSessionInterface()

    session_cookie = app.config.get('SESSION_COOKIE_NAME') or 'session'
    remember_cookie = app.config.get('REMEMBER_COOKIE_NAME') or 'remember_token'
    names = frozenset({session_cookie, remember_cookie})

    @app.after_request
    def _ensure_ets_cookie_domain(response):
        domain = cookie_domain_for_request()
        if not domain:
            return response
        # Alinea REMEMBER (Flask-Login no usa SessionInterface).
        try:
            raw = response.headers.getlist('Set-Cookie')
        except Exception:
            return response
        if not raw:
            return response
        rewritten = [_rewrite_set_cookie_domain(v, domain, names) for v in raw]
        if rewritten == list(raw):
            return response
        # Replace all Set-Cookie headers
        try:
            del response.headers['Set-Cookie']
        except Exception:
            pass
        for v in rewritten:
            response.headers.add('Set-Cookie', v)
        return response
