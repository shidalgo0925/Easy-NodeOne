"""ADR-017 Hito 1 — Portal Público del Producto (landing por host)."""

from __future__ import annotations

from flask import render_template, url_for

from nodeone.modules.product_landing.content import landing_content_for


def render_product_public_landing():
    """Renderiza la landing comercial del producto del Host actual."""
    from nodeone.core.platform.context_resolver import current_app_context
    from nodeone.core.platform.product_registry import ProductRegistry
    from nodeone.services.nav_branding import brand_context_logo_relpath

    app_ctx = current_app_context()
    product = app_ctx.product
    brand = app_ctx.brand
    defn = ProductRegistry.get(product.code)
    content = landing_content_for(
        product.code,
        display_name=brand.display_name or (defn.name if defn else product.code),
        tagline=brand.tagline or (defn.tagline if defn else ''),
        description=(defn.description if defn else '') or '',
    )
    logo = brand_context_logo_relpath() or brand.logo_url or (defn.logo_url if defn else '') or ''
    favicon = (defn.favicon_url if defn and defn.favicon_url else '') or logo
    login_url = url_for('auth.login', next='/')
    return render_template(
        content['template'],
        landing=content,
        brand_name=brand.display_name or (defn.name if defn else product.code),
        brand_logo=logo,
        brand_favicon=favicon,
        brand_logo_wide=bool(content.get('logo_wide')),
        product_code=product.code,
        login_url=login_url,
        theme={
            'primary': brand.theme_primary,
            'primary_dark': brand.theme_primary_dark,
            'accent': brand.theme_accent,
            'background': brand.theme_background,
        },
    )
