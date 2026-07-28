"""URLs canónicas del Portal de cuenta EN1/ETS (ADR-013 / ADR-017).

Mis Productos y la cuenta comercial viven SOLO en el host portal
(``app.easytech.services``). Los hosts de producto (``eposone.*``, …)
nunca sirven esa superficie: redirigen aquí.

Regla: un producto solo conoce su propio entitlement; el catálogo del
cliente y el cambio de producto se delegan al Portal EN1.
"""

from __future__ import annotations


def portal_account_domain() -> str:
    """Dominio canónico del Portal de cuenta (Product Registry ``portal``)."""
    try:
        from nodeone.core.platform.product_registry import ProductRegistry

        definition = ProductRegistry.get('portal')
        domain = (getattr(definition, 'primary_domain', None) or '').strip()
        if domain:
            return domain
    except Exception:
        pass
    return 'app.easytech.services'


def portal_account_base_url() -> str:
    return f'https://{portal_account_domain()}'


def portal_home_url() -> str:
    return f'{portal_account_base_url()}/portal/'


def portal_products_url() -> str:
    return f'{portal_account_base_url()}/portal/products'


def absolute_portal_path(path: str) -> str:
    """Convierte ``/portal/...`` relativo en URL absoluta del Portal canónico."""
    p = (path or '').strip() or '/portal/'
    if not p.startswith('/'):
        p = f'/{p}'
    if not p.startswith('/portal'):
        p = f'/portal{p}' if p.startswith('/') else f'/portal/{p}'
    base = portal_account_base_url().rstrip('/')
    return f'{base}{p}'
