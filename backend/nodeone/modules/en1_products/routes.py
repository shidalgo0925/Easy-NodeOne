"""ADR-039 F1 — módulo Productos EN1 (formaliza core_product; sin tercer catálogo)."""

from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models.saas import SaasOrganization
from nodeone.core.master.constants import MasterDataError
from nodeone.core.master.product import CoreProductService
from nodeone.core.platform.module_registry import is_module_enabled

en1_products_bp = Blueprint('en1_products', __name__, url_prefix='/admin/products')


def _org_id() -> int:
    from app import admin_data_scope_organization_id, default_organization_id

    try:
        oid = int(admin_data_scope_organization_id())
    except Exception:
        oid = int(default_organization_id())
    if SaasOrganization.query.get(int(oid)) is None:
        return int(default_organization_id())
    return int(oid)


def _platform_admin() -> bool:
    return bool(current_user.is_authenticated and getattr(current_user, 'is_admin', False))


def _can_admin() -> bool:
    if not current_user.is_authenticated:
        return False
    if _platform_admin():
        return True
    from app import _user_has_any_admin_permission

    return bool(_user_has_any_admin_permission(current_user))


def _guard():
    if not _can_admin():
        flash('No tenés permisos de administración.', 'error')
        return redirect(url_for('dashboard'))
    if not is_module_enabled(_org_id(), 'products'):
        flash('El módulo Productos no está habilitado para esta organización.', 'error')
        return redirect(url_for('dashboard'))
    return None


@en1_products_bp.before_request
def _before():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.path))
    return _guard()


def _kind_from_row(ptype: str, tracks: bool) -> str:
    p = (ptype or '').strip().lower()
    if p == 'service':
        return 'SERVICE'
    if tracks:
        return 'STOCKABLE'
    return 'NON_STOCKABLE'


def _apply_kind(data: dict, kind: str) -> None:
    k = (kind or 'NON_STOCKABLE').strip().upper()
    if k == 'SERVICE':
        data['product_type'] = 'service'
        data['tracks_inventory'] = False
    elif k == 'STOCKABLE':
        data['product_type'] = 'good'
        data['tracks_inventory'] = True
    else:
        data['product_type'] = 'good'
        data['tracks_inventory'] = False


def _form_data(*, for_create: bool) -> dict:
    data = {
        'name': request.form.get('name'),
        'description': request.form.get('description'),
        'barcode': request.form.get('barcode'),
        'category': request.form.get('category'),
        'uom': request.form.get('uom') or 'und',
        'unit_price': request.form.get('unit_price') or 0,
        'cost_price': request.form.get('cost_price'),
        'fiscal_category': request.form.get('fiscal_category'),
        'status': request.form.get('status') or 'active',
        'source_app_id': 'en1_products',
        'min_stock': request.form.get('min_stock'),
    }
    if for_create:
        data['product_ref'] = request.form.get('product_ref')
    _apply_kind(data, request.form.get('product_kind') or 'NON_STOCKABLE')
    return data


@en1_products_bp.route('/', methods=['GET'])
@login_required
def products_index():
    oid = _org_id()
    q = (request.args.get('q') or '').strip() or None
    status = (request.args.get('status') or '').strip() or None
    items = CoreProductService.search(oid, query=q, status=status, limit=200)
    return render_template(
        'admin/en1_products/index.html',
        products=items,
        q=q or '',
        status=status or '',
        organization_id=oid,
    )


@en1_products_bp.route('/new', methods=['GET', 'POST'])
@login_required
def products_new():
    oid = _org_id()
    if request.method == 'POST':
        try:
            dto = CoreProductService.create(oid, _form_data(for_create=True))
            flash(f'Producto {dto.product_ref} creado.', 'success')
            return redirect(url_for('en1_products.products_edit', product_ref=dto.product_ref))
        except MasterDataError as e:
            flash(str(e), 'error')
    return render_template(
        'admin/en1_products/form.html',
        mode='new',
        product=None,
        organization_id=oid,
        product_kind='NON_STOCKABLE',
    )


@en1_products_bp.route('/<product_ref>/edit', methods=['GET', 'POST'])
@login_required
def products_edit(product_ref: str):
    oid = _org_id()
    dto = CoreProductService.get_by_ref(oid, product_ref)
    if dto is None:
        abort(404)
    if request.method == 'POST':
        try:
            dto = CoreProductService.update(oid, product_ref, _form_data(for_create=False))
            flash('Producto actualizado.', 'success')
            return redirect(url_for('en1_products.products_edit', product_ref=dto.product_ref))
        except MasterDataError as e:
            flash(str(e), 'error')
            dto = CoreProductService.get_by_ref(oid, product_ref) or dto
    return render_template(
        'admin/en1_products/form.html',
        mode='edit',
        product=dto,
        organization_id=oid,
        product_kind=_kind_from_row(dto.product_type, dto.tracks_inventory),
    )


@en1_products_bp.route('/<product_ref>/deactivate', methods=['POST'])
@login_required
def products_deactivate(product_ref: str):
    oid = _org_id()
    try:
        CoreProductService.deactivate(oid, product_ref)
        flash('Producto desactivado.', 'success')
    except MasterDataError as e:
        flash(str(e), 'error')
    return redirect(url_for('en1_products.products_index'))


def register_en1_products_blueprints(app):
    if 'en1_products' not in app.blueprints:
        app.register_blueprint(en1_products_bp)
