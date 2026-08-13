"""ADR-039 F3 — UI Inventario EN1 (sobre inventory_service / core_stock_*)."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models.saas import SaasOrganization
from nodeone.core.commerce.stock import StockService
from nodeone.core.platform import inventory_service as inv
from nodeone.core.platform.inventory_service import ADJUSTMENT_REASONS, InventoryError
from nodeone.core.platform.module_registry import is_module_enabled

en1_inventory_bp = Blueprint('en1_inventory', __name__, url_prefix='/admin/inventory')


def _org_id() -> int:
    from app import admin_data_scope_organization_id, default_organization_id

    try:
        oid = int(admin_data_scope_organization_id())
    except Exception:
        oid = int(default_organization_id())
    if SaasOrganization.query.get(int(oid)) is None:
        return int(default_organization_id())
    return int(oid)


def _can_admin() -> bool:
    if not current_user.is_authenticated:
        return False
    if getattr(current_user, 'is_admin', False):
        return True
    from app import _user_has_any_admin_permission

    return bool(_user_has_any_admin_permission(current_user))


def _guard():
    if not _can_admin():
        flash('No tenés permisos de administración.', 'error')
        return redirect(url_for('dashboard'))
    oid = _org_id()
    if not is_module_enabled(oid, 'inventory'):
        flash('El módulo Inventario no está habilitado para esta organización.', 'error')
        return redirect(url_for('dashboard'))
    if not is_module_enabled(oid, 'products'):
        flash('Inventario requiere el módulo Productos activo.', 'error')
        return redirect(url_for('dashboard'))
    inv.ensure_default_warehouse(oid)
    return None


@en1_inventory_bp.before_request
def _before():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.path))
    return _guard()


@en1_inventory_bp.route('/', methods=['GET'])
@login_required
def inventory_home():
    return redirect(url_for('en1_inventory.inventory_balances'))


@en1_inventory_bp.route('/balances', methods=['GET'])
@login_required
def inventory_balances():
    oid = _org_id()
    wh = request.args.get('warehouse_id', type=int)
    ref = (request.args.get('product_ref') or '').strip() or None
    warehouses = inv.list_warehouses(oid)
    if wh is None and warehouses:
        wh = int(warehouses[0]['id'])
    balances = StockService.list_balances(
        oid, warehouse_org_unit_id=wh, product_ref=ref, limit=300
    )
    return render_template(
        'admin/en1_inventory/balances.html',
        balances=balances,
        warehouses=warehouses,
        warehouse_id=wh,
        product_ref=ref or '',
        organization_id=oid,
        stock_policy=inv.get_stock_policy(oid),
    )


@en1_inventory_bp.route('/movements', methods=['GET'])
@login_required
def inventory_movements():
    oid = _org_id()
    wh = request.args.get('warehouse_id', type=int)
    ref = (request.args.get('product_ref') or '').strip() or None
    warehouses = inv.list_warehouses(oid)
    if wh is None and warehouses:
        wh = int(warehouses[0]['id'])
    movements = StockService.list_movements(
        oid, warehouse_org_unit_id=wh, product_ref=ref, limit=200
    )
    return render_template(
        'admin/en1_inventory/movements.html',
        movements=movements,
        warehouses=warehouses,
        warehouse_id=wh,
        product_ref=ref or '',
        organization_id=oid,
    )


@en1_inventory_bp.route('/receipt', methods=['GET', 'POST'])
@login_required
def inventory_receipt():
    oid = _org_id()
    warehouses = inv.list_warehouses(oid)
    if request.method == 'POST':
        try:
            inv.record_movement(
                oid,
                product_ref=request.form.get('product_ref') or '',
                kind='RECEIPT',
                quantity=float(request.form.get('quantity') or 0),
                warehouse_org_unit_id=request.form.get('warehouse_id', type=int),
                notes=request.form.get('notes'),
                source_system='EN1',
            )
            flash('Entrada registrada.', 'success')
            return redirect(url_for('en1_inventory.inventory_balances'))
        except (InventoryError, ValueError, TypeError) as e:
            flash(str(e), 'error')
    return render_template(
        'admin/en1_inventory/receipt.html',
        warehouses=warehouses,
        organization_id=oid,
    )


@en1_inventory_bp.route('/adjust', methods=['GET', 'POST'])
@login_required
def inventory_adjust():
    oid = _org_id()
    warehouses = inv.list_warehouses(oid)
    if request.method == 'POST':
        direction = (request.form.get('direction') or 'out').strip().lower()
        kind = 'ADJUSTMENT_IN' if direction == 'in' else 'ADJUSTMENT_OUT'
        try:
            inv.record_movement(
                oid,
                product_ref=request.form.get('product_ref') or '',
                kind=kind,
                quantity=float(request.form.get('quantity') or 0),
                warehouse_org_unit_id=request.form.get('warehouse_id', type=int),
                reason=request.form.get('reason') or 'other',
                notes=request.form.get('notes'),
                source_system='EN1',
            )
            flash('Ajuste registrado.', 'success')
            return redirect(url_for('en1_inventory.inventory_balances'))
        except (InventoryError, ValueError, TypeError) as e:
            flash(str(e), 'error')
    return render_template(
        'admin/en1_inventory/adjust.html',
        warehouses=warehouses,
        reasons=sorted(ADJUSTMENT_REASONS),
        organization_id=oid,
    )


@en1_inventory_bp.route('/kardex', methods=['GET'])
@login_required
def inventory_kardex():
    oid = _org_id()
    ref = (request.args.get('product_ref') or '').strip()
    wh = request.args.get('warehouse_id', type=int)
    warehouses = inv.list_warehouses(oid)
    if wh is None and warehouses:
        wh = int(warehouses[0]['id'])
    rows = inv.kardex(oid, ref, warehouse_org_unit_id=wh) if ref else []
    on_hand = inv.get_on_hand(oid, ref, warehouse_org_unit_id=wh) if ref else None
    return render_template(
        'admin/en1_inventory/kardex.html',
        rows=rows,
        product_ref=ref,
        warehouses=warehouses,
        warehouse_id=wh,
        on_hand=on_hand,
        organization_id=oid,
    )


@en1_inventory_bp.route('/warehouses', methods=['GET'])
@login_required
def inventory_warehouses():
    oid = _org_id()
    inv.ensure_default_warehouse(oid)
    return render_template(
        'admin/en1_inventory/warehouses.html',
        warehouses=inv.list_warehouses(oid),
        organization_id=oid,
    )


def register_en1_inventory_blueprints(app):
    if 'en1_inventory' not in app.blueprints:
        app.register_blueprint(en1_inventory_bp)
