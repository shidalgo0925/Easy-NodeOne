"""Rutas Portal — Bienvenido + Mis Productos.

Se sirven en Host portal, producto y plataforma EN1. En producto, misma sesión
(«Cambiar producto» sin saltar a app.easytech).
"""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_required

from nodeone.core.platform.context_resolver import current_app_context
from nodeone.modules.ets_portal.portal_service import PortalService

ets_portal_bp = Blueprint('ets_portal', __name__, url_prefix='/portal')


def _brand_kwargs() -> dict:
    try:
        ctx = current_app_context()
        return {
            'brand_name': ctx.display_name,
            'brand_preset': ctx.brand_preset,
            'brand_theme': ctx.theme_overlay(),
        }
    except Exception:
        return {
            'brand_name': 'Easy NodeOne',
            'brand_preset': 'en1',
            'brand_theme': {},
        }


def _require_portal_surface():
    """Permite portal / producto / plataforma; el resto → dashboard."""
    try:
        if current_app_context().surface in ('portal', 'product', 'platform'):
            return None
    except Exception:
        return None
    try:
        return redirect(url_for('dashboard'))
    except Exception:
        return redirect('/')


@ets_portal_bp.route('/')
@login_required
def home():
    gate = _require_portal_surface()
    if gate is not None:
        return gate
    products = PortalService.list_products_for_current_tenant()
    return render_template(
        'ets_portal/home.html',
        portal_products=products,
        **_brand_kwargs(),
    )


@ets_portal_bp.route('/products')
@login_required
def products():
    gate = _require_portal_surface()
    if gate is not None:
        return gate
    products_list = PortalService.list_products_for_current_tenant()
    return render_template(
        'ets_portal/products.html',
        portal_products=products_list,
        **_brand_kwargs(),
    )


@ets_portal_bp.route('/open/<product_code>')
@login_required
def open_product(product_code: str):
    gate = _require_portal_surface()
    if gate is not None:
        return gate
    code = (product_code or '').strip().lower()
    owned = {p['product_code'] for p in PortalService.list_products_for_current_tenant()}
    if code not in owned:
        flash('No tienes acceso a ese producto.', 'error')
        return redirect(url_for('ets_portal.products'))
    url = PortalService.open_url_for_product(code)
    if not url:
        flash('El producto no tiene dominio configurado.', 'error')
        return redirect(url_for('ets_portal.products'))
    return redirect(url)


def register_ets_portal_blueprint(app) -> None:
    if 'ets_portal' not in app.blueprints:
        app.register_blueprint(ets_portal_bp)
