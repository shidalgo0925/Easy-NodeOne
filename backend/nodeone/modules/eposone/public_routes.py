"""Rutas públicas menú digital — Etapa 17."""

from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request, url_for

from nodeone.core.commerce.order import OrderValidationError
from nodeone.modules.eposone.digital_menu_service import DigitalMenuService, resolve_public_menu_brand_logo

eposone_public_bp = Blueprint('eposone_public', __name__)


@eposone_public_bp.route('/m/eposone/<token>')
def public_menu_page(token: str):
    menu = DigitalMenuService.get_by_token(token)
    if menu is None:
        return render_template('eposone/public_menu_not_found.html'), 404
    brand_logo = resolve_public_menu_brand_logo(menu.organization_id)
    brand_logo_url = url_for('static', filename=brand_logo) if brand_logo else None
    brand_favicon = None
    if brand_logo:
        import os

        from nodeone.services.tenant_email_logo_storage import _static_root_abs

        oid = int(menu.organization_id)
        root = _static_root_abs()
        for cand in (
            f'uploads/eposone/brands/org{oid}-favicon.png',
            f'uploads/eposone/brands/org{oid}-favicon-32.png',
            brand_logo,
        ):
            if os.path.isfile(os.path.join(root, cand.replace('/', os.sep))):
                brand_favicon = cand
                break
    brand_favicon_url = url_for('static', filename=brand_favicon) if brand_favicon else brand_logo_url
    return render_template(
        'eposone/public_menu.html',
        menu=menu.to_dict(include_token=False),
        token=token,
        brand_logo_url=brand_logo_url,
        brand_favicon_url=brand_favicon_url,
    )


@eposone_public_bp.route('/api/public/eposone/menu/<token>', methods=['GET'])
def public_menu_api(token: str):
    menu = DigitalMenuService.get_by_token(token)
    if menu is None:
        return jsonify({'error': 'menu_not_found'}), 404
    return jsonify({'menu': menu.to_dict(include_token=False)})


@eposone_public_bp.route('/api/public/eposone/menu/<token>/orders', methods=['POST'])
def public_menu_place_order(token: str):
    body = request.get_json(silent=True) or {}
    cart = body.get('lines') if isinstance(body.get('lines'), list) else body.get('cart')
    if not isinstance(cart, list):
        return jsonify({'error': 'lines_required'}), 400
    try:
        order = DigitalMenuService.place_order_from_token(
            token,
            cart,
            notes=body.get('notes'),
        )
    except OrderValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'order': order.to_dict()}), 201
