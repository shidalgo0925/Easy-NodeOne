"""ADR-039 — módulo Productos EN1 (core_product) · UX inventario unificado."""

from __future__ import annotations

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models.saas import SaasOrganization
from nodeone.core.master.constants import MasterDataError
from nodeone.core.master.product import CoreProductService
from nodeone.core.platform.module_registry import is_module_enabled
from nodeone.modules.eposone.fiscal_categories import FISCAL_CATEGORIES_PA, FISCAL_CATEGORY_DEFAULT

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


def _ui_type_from_row(ptype: str, tracks: bool) -> tuple[str, bool]:
    """(base_type goods|service, tracks_inventory)."""
    p = (ptype or '').strip().lower()
    if p == 'service':
        return 'service', False
    return 'good', bool(tracks)


def _apply_ui_type(data: dict) -> None:
    base = (request.form.get('product_base_type') or 'good').strip().lower()
    tracks = (request.form.get('tracks_inventory') or '').strip().lower() in (
        '1',
        'true',
        'on',
        'yes',
    )
    if base == 'service':
        data['product_type'] = 'service'
        data['tracks_inventory'] = False
    else:
        data['product_type'] = 'good'
        data['tracks_inventory'] = tracks


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
        'image_url': (request.form.get('image_url') or '').strip() or None,
    }
    if for_create:
        data['product_ref'] = request.form.get('product_ref')
    _apply_ui_type(data)
    return data


def _parse_tracks_filter(raw: str | None) -> bool | None:
    v = (raw or '').strip().lower()
    if v in ('1', 'true', 'yes', 'si', 'sí'):
        return True
    if v in ('0', 'false', 'no'):
        return False
    return None


def _type_label(ptype: str, tracks: bool) -> str:
    p = (ptype or '').strip().lower()
    if p == 'service':
        return 'Servicio'
    if tracks:
        return 'Bien · inventariable'
    return 'Bien'


@en1_products_bp.route('/', methods=['GET'])
@login_required
def products_index():
    oid = _org_id()
    try:
        from nodeone.core.master.product_bridge import backfill_org

        backfill_org(oid, limit=300)
    except Exception:
        pass
    q = (request.args.get('q') or '').strip() or None
    status = (request.args.get('status') or '').strip() or None
    ptype = (request.args.get('product_type') or '').strip().lower() or None
    if ptype and ptype not in ('good', 'service'):
        ptype = None
    tracks = _parse_tracks_filter(request.args.get('tracks_inventory'))
    items = CoreProductService.search(
        oid,
        query=q,
        status=status,
        product_type=ptype,
        tracks_inventory=tracks,
        limit=200,
    )
    filters_open = bool(
        q or status or ptype or request.args.get('tracks_inventory')
    )
    return render_template(
        'admin/en1_products/index.html',
        products=items,
        q=q or '',
        status=status or '',
        product_type=ptype or '',
        tracks_inventory=(
            ''
            if tracks is None
            else ('1' if tracks else '0')
        ),
        filters_open=filters_open,
        organization_id=oid,
        type_label=_type_label,
    )


@en1_products_bp.route('/upload-image', methods=['POST'])
@login_required
def products_upload_image():
    """Sube imagen de producto → static/uploads/catalog/products/."""
    from models.core_master import CoreProduct
    from nodeone.core.db import db
    from nodeone.services.catalog_image_storage import save_catalog_product_image

    oid = _org_id()
    f = request.files.get('image_file') or request.files.get('file')
    url, err = save_catalog_product_image(f, organization_id=oid)
    if err:
        return jsonify({'success': False, 'error': err}), 400
    if not url:
        return jsonify({'success': False, 'error': 'Seleccioná un archivo de imagen.'}), 400

    pref = (request.form.get('product_ref') or request.args.get('product_ref') or '').strip()
    persisted = False
    if pref:
        row = CoreProduct.query.filter_by(organization_id=oid, product_ref=pref).first()
        if row is None:
            return jsonify({'success': False, 'error': 'Producto no encontrado.'}), 404
        row.image_url = url
        try:
            db.session.commit()
            persisted = True
            try:
                from nodeone.core.master.product_bridge import ensure_from_product

                ensure_from_product(oid, product_ref=pref)
            except Exception:
                pass
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400

    return jsonify(
        {
            'success': True,
            'image_url': url,
            'product_ref': pref or None,
            'persisted': persisted,
        }
    )


@en1_products_bp.route('/new', methods=['GET', 'POST'])
@login_required
def products_new():
    oid = _org_id()
    if request.method == 'POST':
        try:
            dto = CoreProductService.create(oid, _form_data(for_create=True))
            try:
                from nodeone.core.master.product_bridge import ensure_from_product

                ensure_from_product(oid, product_ref=dto.product_ref)
            except Exception:
                pass
            flash(f'Producto {dto.product_ref} creado.', 'success')
            return redirect(url_for('en1_products.products_edit', product_ref=dto.product_ref))
        except MasterDataError as e:
            flash(str(e), 'error')
    base_type, tracks = 'good', False
    if request.method == 'POST':
        base_type = (request.form.get('product_base_type') or 'good').strip().lower()
        tracks = (request.form.get('tracks_inventory') or '').strip().lower() in (
            '1',
            'true',
            'on',
            'yes',
        )
        if base_type == 'service':
            tracks = False
    return render_template(
        'admin/en1_products/form.html',
        mode='new',
        product=None,
        organization_id=oid,
        product_base_type=base_type,
        tracks_inventory=tracks,
        fiscal_categories=FISCAL_CATEGORIES_PA,
        fiscal_default=FISCAL_CATEGORY_DEFAULT,
        image_url=(request.form.get('image_url') or '').strip() if request.method == 'POST' else '',
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
            try:
                from nodeone.core.master.product_bridge import ensure_from_product

                ensure_from_product(oid, product_ref=dto.product_ref)
            except Exception:
                pass
            flash('Producto actualizado.', 'success')
            return redirect(url_for('en1_products.products_edit', product_ref=dto.product_ref))
        except MasterDataError as e:
            flash(str(e), 'error')
            dto = CoreProductService.get_by_ref(oid, product_ref) or dto
    base_type, tracks = _ui_type_from_row(dto.product_type, dto.tracks_inventory)
    if request.method == 'POST':
        base_type = (request.form.get('product_base_type') or base_type).strip().lower()
        tracks = (request.form.get('tracks_inventory') or '').strip().lower() in (
            '1',
            'true',
            'on',
            'yes',
        )
        if base_type == 'service':
            tracks = False
    return render_template(
        'admin/en1_products/form.html',
        mode='edit',
        product=dto,
        organization_id=oid,
        product_base_type=base_type,
        tracks_inventory=tracks,
        fiscal_categories=FISCAL_CATEGORIES_PA,
        fiscal_default=FISCAL_CATEGORY_DEFAULT,
        image_url=(
            (request.form.get('image_url') or '').strip()
            if request.method == 'POST'
            else (dto.image_url or '')
        ),
    )


@en1_products_bp.route('/<product_ref>/deactivate', methods=['POST'])
@login_required
def products_deactivate(product_ref: str):
    oid = _org_id()
    try:
        CoreProductService.deactivate(oid, product_ref)
        try:
            from nodeone.core.master.product_bridge import ensure_from_product

            ensure_from_product(oid, product_ref=product_ref)
        except Exception:
            pass
        flash('Producto desactivado.', 'success')
    except MasterDataError as e:
        flash(str(e), 'error')
    return redirect(url_for('en1_products.products_index'))


def register_en1_products_blueprints(app):
    if 'en1_products' not in app.blueprints:
        app.register_blueprint(en1_products_bp)
