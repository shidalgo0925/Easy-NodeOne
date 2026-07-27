"""Rutas Portal ETS MVP — Bienvenido + Mis Productos."""

from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from nodeone.core.platform.context_resolver import current_app_context
from nodeone.modules.ets_portal.portal_service import PortalService

ets_portal_bp = Blueprint('ets_portal', __name__, url_prefix='/portal')


def _require_portal_surface():
    """Portal ETS: host portal, o producto (ADR-017 Hito 4 → Mis Productos)."""
    ctx = current_app_context()
    if ctx.surface in ('portal', 'product'):
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
        brand_name=current_app_context().display_name,
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
        brand_name=current_app_context().display_name,
    )


@ets_portal_bp.route('/open/<product_code>')
@login_required
def open_product(product_code: str):
    gate = _require_portal_surface()
    if gate is not None:
        return gate
    code = (product_code or '').strip().lower()
    # Solo productos del tenant actual
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
