"""Helpers de branding para logo/nav (extraído de app.py)."""

import os


def platform_nav_logo_relpath():
    """
    Logo de barra/favicon fijo de producto (Easy NodeOne).
    El upload de branding en /admin escribe logo-relatic.* en public/emails/logos y copia a
    images/logo-relatic.* — puede pisar el icono global. Este nombre no lo toca el upload.
    """
    import app as M

    static_dir = os.path.join(os.path.dirname(M.__file__), '..', 'static')
    p = os.path.join(static_dir, 'images', 'logo-easy-nodeone.svg')
    if os.path.exists(p):
        return 'images/logo-easy-nodeone.svg'
    p2 = os.path.join(static_dir, 'images', 'logo-relatic.svg')
    if os.path.exists(p2):
        return 'images/logo-relatic.svg'
    return 'images/logo-relatic.svg'


def nav_theme_logo_relpath():
    """Ruta bajo static/ del logo configurado en organization_settings de la org activa (sesión)."""
    import app as M

    try:
        s = M.OrganizationSettings.get_settings_for_session()
        u = (s.logo_url or '').strip()
        if u:
            return u.lstrip('/')
    except Exception:
        pass
    return None


def get_nav_logo():
    import app as M

    rel = nav_theme_logo_relpath()
    if rel:
        return rel
    if M.single_tenant_default_only() and os.environ.get('NODEONE_NAV_USE_PLATFORM_LOGO', '1').strip().lower() not in (
        '0', 'false', 'no', 'off',
    ):
        return platform_nav_logo_relpath()
    return M.get_system_logo()


def get_nav_logo_cache_key():
    import app as M

    rel = nav_theme_logo_relpath()
    if rel:
        p = os.path.join(os.path.dirname(M.__file__), '..', 'static', rel)
        if os.path.exists(p):
            try:
                oid = 0
                try:
                    if M.has_request_context() and getattr(M.current_user, 'is_authenticated', False):
                        gco = M.get_current_organization_id()
                        oid = int(gco) if gco is not None else 0
                except Exception:
                    pass
                return int(os.path.getmtime(p)) + oid * 1_000_000_000
            except OSError:
                pass
        return 0
    if M.single_tenant_default_only() and os.environ.get('NODEONE_NAV_USE_PLATFORM_LOGO', '1').strip().lower() not in (
        '0', 'false', 'no', 'off',
    ):
        rel = platform_nav_logo_relpath()
        p = os.path.join(os.path.dirname(M.__file__), '..', 'static', rel)
        if os.path.exists(p):
            try:
                return int(os.path.getmtime(p))
            except OSError:
                pass
        return 0
    return M.get_logo_cache_key()


def get_nav_brand_name():
    """Una sola regla: BRAND_MODE GLOBAL vs TENANT (sesión)."""
    import app as M

    try:
        mode = (M.app.config.get('BRAND_MODE') or 'GLOBAL').strip().upper()
        if mode == 'GLOBAL':
            return (M.app.config.get('APP_BRAND_NAME') or 'Easy NodeOne').strip() or 'Easy NodeOne'
        if M.single_tenant_default_only() and not (
            getattr(M.current_user, 'is_authenticated', False) and getattr(M.current_user, 'is_admin', False)
        ):
            oid = M.default_organization_id()
        else:
            oid = M.get_current_organization_id()
        if oid is None:
            return (M.app.config.get('APP_BRAND_NAME') or 'Easy NodeOne').strip() or 'Easy NodeOne'
        org = M.SaasOrganization.query.get(oid)
        if org and (org.name or '').strip():
            return (org.name or '').strip()
    except Exception:
        pass
    return (M.app.config.get('APP_BRAND_NAME') or 'Easy NodeOne').strip() or 'Easy NodeOne'

