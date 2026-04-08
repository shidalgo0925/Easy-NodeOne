"""Acceso a funciones de administración tenant (RBAC panel), sin lógica en vistas."""


def user_has_any_rbac_admin_permission(user):
    """
    True si el usuario tiene al menos un rol con algún permiso (alineado con admin_required).
    """
    if not user or not getattr(user, 'id', None):
        return False
    from sqlalchemy import text

    from nodeone.core.db import db

    r = db.session.execute(
        text(
            'SELECT 1 FROM user_role ur JOIN role_permission rp ON rp.role_id = ur.role_id '
            'WHERE ur.user_id = :uid LIMIT 1'
        ),
        {'uid': user.id},
    ).fetchone()
    return r is not None


def user_can_access_taxes_api(user, organization_id):
    """
    API /taxes y /api/taxes: mismo criterio que el panel admin de impuestos.
    - Admin plataforma o RBAC con acceso admin (app.admin_required).
    - O módulo Ventas activo para la org (cotizaciones / líneas con impuesto).
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    import app as M

    if getattr(user, 'is_admin', False):
        return True
    try:
        if M._user_has_any_admin_permission(user):
            return True
    except Exception:
        pass
    from nodeone.services.org_scope import has_saas_module_enabled

    try:
        oid = int(organization_id)
    except (TypeError, ValueError):
        oid = None
    if oid is not None and has_saas_module_enabled(oid, 'sales'):
        return True
    return False
