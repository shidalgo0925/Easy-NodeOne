"""URLs canónicas del Portal de cuenta EN1 (ADR-013 / ADR-017).

Mis Productos vive en la plataforma EN1 (``appprd.easynodeone.com``).
El host comercial ``app.easytech.services`` quedó fuera de uso (redirige a EN1).

En hosts de producto, ``/portal/*`` se sirve en el mismo host (misma sesión)
para «Cambiar producto» sin re-login.
"""

from __future__ import annotations

import os


def portal_account_domain() -> str:
    """Dominio canónico del Portal de cuenta (env → Product Registry → appprd)."""
    env = (os.environ.get('NODEONE_PORTAL_ACCOUNT_DOMAIN') or '').strip().lower()
    if env:
        return env.lstrip('.')
    try:
        from nodeone.core.platform.product_registry import ProductRegistry

        definition = ProductRegistry.get('portal')
        domain = (getattr(definition, 'primary_domain', None) or '').strip()
        if domain and 'easytech.services' not in domain.lower():
            return domain
    except Exception:
        pass
    return 'appprd.easynodeone.com'


def portal_account_base_url() -> str:
    return f'https://{portal_account_domain()}'


def portal_home_url() -> str:
    return f'{portal_account_base_url()}/portal/'


def portal_products_url() -> str:
    return f'{portal_account_base_url()}/portal/products'


def absolute_portal_path(path: str) -> str:
    """Convierte ``/portal/...`` relativo en URL absoluta del Portal canónico EN1."""
    p = (path or '').strip() or '/portal/'
    if not p.startswith('/'):
        p = f'/{p}'
    if not p.startswith('/portal'):
        p = f'/portal{p}' if p.startswith('/') else f'/portal/{p}'
    base = portal_account_base_url().rstrip('/')
    return f'{base}{p}'


def portal_products_href() -> str:
    """Href «Cambiar producto»: mismo host si hay request; si no, canónico EN1."""
    try:
        from flask import has_request_context, url_for

        if has_request_context():
            return url_for('ets_portal.products')
    except Exception:
        pass
    return portal_products_url()
