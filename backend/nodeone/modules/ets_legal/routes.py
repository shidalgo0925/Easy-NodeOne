"""Blueprint público /legal/* — centro legal ETS."""

from __future__ import annotations

from flask import Blueprint, abort, render_template

from nodeone.modules.ets_legal.pages import LEGAL_PAGES, get_legal_page

ets_legal_bp = Blueprint('ets_legal', __name__, url_prefix='/legal')


def _brand_bits() -> dict:
    try:
        from nodeone.core.platform.context_resolver import current_app_context

        ctx = current_app_context()
        return {
            'brand_name': ctx.display_name or 'Easy Technology Services',
            'product_code': (ctx.product.code if ctx.product else '') or '',
        }
    except Exception:
        return {'brand_name': 'Easy Technology Services', 'product_code': ''}


@ets_legal_bp.route('/')
def legal_index():
    bits = _brand_bits()
    return render_template(
        'ets_legal/index.html',
        pages=LEGAL_PAGES,
        brand_name=bits['brand_name'],
        product_code=bits['product_code'],
    )


@ets_legal_bp.route('/<slug>')
def legal_page(slug: str):
    page = get_legal_page(slug)
    if page is None:
        abort(404)
    bits = _brand_bits()
    return render_template(
        f'ets_legal/pages/{page.slug}.html',
        page=page,
        pages=LEGAL_PAGES,
        brand_name=bits['brand_name'],
        product_code=bits['product_code'],
    )


def register_ets_legal_blueprint(app) -> None:
    if 'ets_legal' not in app.blueprints:
        app.register_blueprint(ets_legal_bp)
