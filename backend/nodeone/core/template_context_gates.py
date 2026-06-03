"""Gates para context processors: evitar queries en vistas que no usan los datos."""

from __future__ import annotations


def user_can_see_tenant_admin_menu(user) -> bool:
    """Misma regla que inject_admin_nav_context.show_tenant_admin_menu (sin side effects)."""
    from flask import session

    if not getattr(user, 'is_authenticated', False):
        return False
    if session.get('require_org_selection'):
        return False
    if getattr(user, 'is_admin', False):
        return True
    try:
        from app import _user_has_any_admin_permission

        return bool(_user_has_any_admin_permission(user))
    except Exception:
        return False


def should_load_member_portal_context(user) -> bool:
    """Sidebar miembro / dashboard campus: no aplica a admin tenant ni anónimos."""
    return user_can_see_tenant_admin_menu(user) is False and getattr(user, 'is_authenticated', False)


def should_count_events_portal_badge(*, user, events_module_enabled: bool) -> bool:
    if not events_module_enabled or not getattr(user, 'is_authenticated', False):
        return False
    return should_load_member_portal_context(user)


def should_load_academic_member_context(*, user, academic_module_enabled: bool) -> bool:
    if not academic_module_enabled or not getattr(user, 'is_authenticated', False):
        return False
    return should_load_member_portal_context(user)


def cached_orgs_for_session_after_login(user):
    from flask import g, has_request_context

    if not has_request_context():
        from nodeone.services.post_login_organization import organizations_for_session_after_login

        return organizations_for_session_after_login(user)
    cached = getattr(g, '_orgs_for_session_after_login', None)
    if cached is not None:
        return cached
    from nodeone.services.post_login_organization import organizations_for_session_after_login

    cached = organizations_for_session_after_login(user)
    g._orgs_for_session_after_login = cached
    return cached
