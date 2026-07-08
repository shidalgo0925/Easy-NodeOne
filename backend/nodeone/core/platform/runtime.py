"""
Facades del Core — punto de entrada para apps (Etapa 2).

Las apps nuevas deben usar estas funciones en lugar de importar el monolito ``app``.
"""

from __future__ import annotations

from typing import Any


def resolve_organization_id() -> int | None:
    """Organización activa del request o None si no hay contexto HTTP."""
    from flask import has_request_context
    from utils.organization import resolve_current_organization

    if not has_request_context():
        return None
    org_id = resolve_current_organization()
    if org_id is None:
        return None
    return int(org_id)


def has_saas_module(module_code: str, organization_id: int | None = None) -> bool:
    """Módulo SaaS habilitado para la org (caché por request si hay contexto)."""
    from nodeone.services.saas_module_cache import has_saas_module_enabled_cached

    oid = organization_id if organization_id is not None else resolve_organization_id()
    return bool(has_saas_module_enabled_cached(oid, (module_code or '').strip()))


def has_permission(user: Any, permission_code: str) -> bool:
    """RBAC granular; delega en ``User.has_permission``."""
    if user is None:
        return False
    checker = getattr(user, 'has_permission', None)
    if not callable(checker):
        return False
    return bool(checker((permission_code or '').strip()))
