"""Scope/admin helpers de organización (extraído de app.py)."""


def org_id_for_module_visibility():
    """
    Flags de módulo en plantillas y guards públicos (¿módulo encendido?).
    Misma resolución que tenant_data / SaaS guards (host, sesión, membresía).
    No usar para queries de datos filtradas por sesión: ahí va get_current_organization_id().
    """
    from utils.organization import resolve_current_organization

    return int(resolve_current_organization())


def has_saas_module_enabled(organization_id, module_code):
    import app as M

    if not module_code:
        return True
    if not M._enable_multi_tenant_catalog():
        return True
    if organization_id is None:
        return False
    try:
        oid = int(organization_id)
    except (TypeError, ValueError):
        return False
    mod = M.SaasModule.query.filter_by(code=module_code).first()
    if mod is None:
        # Sin fila en catálogo: no se puede evaluar permiso → denegar (multi-tenant SaaS).
        return False
    link = M.SaasOrgModule.query.filter_by(organization_id=oid, module_id=mod.id).first()
    if link is not None:
        return bool(link.enabled)
    return bool(mod.is_core)


def apply_session_organization_after_login(user, req):
    """Tras login: delega en finalize_post_login_organization (cards / última empresa / una sola)."""
    from nodeone.services.post_login_organization import finalize_post_login_organization

    return finalize_post_login_organization(user, req)


def admin_can_view_all_organizations():
    import app as M

    return bool(
        getattr(M.current_user, 'is_authenticated', False) and getattr(M.current_user, 'is_admin', False)
    )


def platform_admin_data_scope_organization_id():
    import app as M

    if not M.has_request_context():
        return None
    v = M.session.get('platform_admin_scope_org_id')
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def current_user_can_view_org_users():
    """
    Regla de visibilidad de usuarios en listados/admin:
    - Plataforma admin (is_admin): puede ver todos en el scope activo.
    - RBAC tenant: requiere users.view para ver otros usuarios.
    - Sin ese permiso: solo su propio usuario.
    """
    import app as M

    if not M.has_request_context() or not getattr(M.current_user, 'is_authenticated', False):
        return False
    if getattr(M.current_user, 'is_admin', False):
        return True
    try:
        return bool(M.current_user.has_permission('users.view'))
    except Exception:
        return False


def admin_scope_user_ids_only():
    """
    Subquery de IDs de usuario permitidos por scope+permiso.
    Siempre aplica organization_id; sin users.view devuelve solo current_user.id.
    """
    import app as M

    from nodeone.services.user_organization import user_ids_query_in_organization

    scope_oid = int(M.admin_data_scope_organization_id())
    q = user_ids_query_in_organization(scope_oid)
    if not current_user_can_view_org_users():
        q = q.filter(M.User.id == int(getattr(M.current_user, 'id', 0) or 0))
    return q


def admin_data_scope_organization_id():
    """Listados admin: is_admin → sesión (selector); resto en single-tenant → user.organization_id."""
    import app as M

    if M.has_request_context() and getattr(M.current_user, 'is_authenticated', False):
        if M.single_tenant_default_only() and not getattr(M.current_user, 'is_admin', False):
            return int(getattr(M.current_user, 'organization_id', None) or M.default_organization_id())
    oid = None
    try:
        oid = M.get_current_organization_id()
    except RuntimeError:
        # Multi-tenant: sesión sin organization_id (sesión antigua / flujo incompleto).
        oid = None
    if oid is not None:
        return int(oid)
    # Sin org en sesión: misma resolución que paneles admin por host (p. ej. apps.relatic.org → org Relatic).
    try:
        from utils.organization import get_admin_effective_organization_id

        return int(get_admin_effective_organization_id())
    except Exception:
        return int(M.default_organization_id())

