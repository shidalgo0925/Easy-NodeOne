"""ADR-017 Hito 2 — elegir plantilla auth según superficie Portal."""

from __future__ import annotations


def resolve_auth_template(name: str) -> str:
    """``login.html`` → ``ets_portal/login.html`` en Host portal."""
    base = (name or '').strip()
    if not base:
        return 'login.html'
    if '/' in base:
        return base
    try:
        from nodeone.core.platform.context_resolver import current_app_context

        if current_app_context().surface == 'portal':
            return f'ets_portal/{base}'
    except Exception:
        pass
    return base
