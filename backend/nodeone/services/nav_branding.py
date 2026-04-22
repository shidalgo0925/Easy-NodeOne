"""Helpers de branding para logo/nav (extraído de app.py)."""

import os


def platform_nav_logo_relpath():
    """
    Logo de barra/favicon fijo de producto (Easy NodeOne).
    El upload de branding en /admin puede escribir el logo del tenant en public/emails/logos;
    el nombre por defecto del asset de producto es distinto (logo-easy-nodeone / logo-primary).
    """
    import app as M

    try:
        from nodeone.config.settings import settings

        bn = settings.LOGO_BASENAME
    except Exception:
        bn = 'logo-primary'

    static_dir = os.path.join(os.path.dirname(M.__file__), '..', 'static')
    p = os.path.join(static_dir, 'images', 'logo-easy-nodeone.svg')
    if os.path.exists(p):
        return 'images/logo-easy-nodeone.svg'
    p2 = os.path.join(static_dir, 'images', f'{bn}.svg')
    if os.path.exists(p2):
        return f'images/{bn}.svg'
    return f'images/{bn}.svg'


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
    """
    Texto de marca en la barra superior: nombre de la empresa (SaasOrganization) del contexto activo
    (subdominio / sesión vía resolve_current_organization). Así se muestra p. ej. «Relatic» en lugar del
    nombre genérico del producto cuando corresponde.

    Forzar siempre la marca del producto (APP_BRAND_NAME): NODEONE_NAV_FORCE_PRODUCT_NAME=1
    """
    import app as M

    if os.environ.get('NODEONE_NAV_FORCE_PRODUCT_NAME', '').strip().lower() in ('1', 'true', 'yes', 'on'):
        return (M.app.config.get('APP_BRAND_NAME') or 'Easy NodeOne').strip() or 'Easy NodeOne'

    def _name_for_org_id(oid):
        if oid is None:
            return None
        try:
            oid = int(oid)
        except (TypeError, ValueError):
            return None
        if oid < 1:
            return None
        org = M.SaasOrganization.query.get(oid)
        if org is None or not (org.name or '').strip():
            return None
        return (org.name or '').strip()

    try:
        if M.has_request_context():
            from flask import request
            from flask_login import current_user

            from utils.organization import resolve_current_organization

            # Admin de plataforma: el nombre debe coincidir con el selector de empresa (sesión), no con el
            # subdominio del host (p. ej. dev con tonydev.* mientras trabaja sobre otra org en el panel).
            if getattr(current_user, 'is_authenticated', False) and getattr(current_user, 'is_admin', False):
                n = _name_for_org_id(resolve_current_organization())
                if n:
                    return n
            else:
                try:
                    host_oid = M._organization_id_from_request_host(request)
                except Exception:
                    host_oid = None
                n = _name_for_org_id(host_oid)
                if n:
                    return n
                n = _name_for_org_id(resolve_current_organization())
                if n:
                    return n
    except Exception:
        pass

    try:
        mode = (M.app.config.get('BRAND_MODE') or 'GLOBAL').strip().upper()
        if mode != 'GLOBAL':
            if M.single_tenant_default_only() and not (
                getattr(M.current_user, 'is_authenticated', False) and getattr(M.current_user, 'is_admin', False)
            ):
                n = _name_for_org_id(M.default_organization_id())
            else:
                try:
                    oid = M.get_current_organization_id()
                except RuntimeError:
                    oid = None
                n = _name_for_org_id(oid)
            if n:
                return n
    except Exception:
        pass

    return (M.app.config.get('APP_BRAND_NAME') or 'Easy NodeOne').strip() or 'Easy NodeOne'

