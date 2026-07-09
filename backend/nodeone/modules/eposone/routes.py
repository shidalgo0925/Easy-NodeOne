"""Rutas HTML de EPosOne (Etapa 6–7)."""

from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from nodeone.core.template_context_gates import user_can_see_tenant_admin_menu
from nodeone.modules.eposone.sections import EPOSONE_SECTIONS, EPOSONE_SECTION_SLUGS

eposone_bp = Blueprint('eposone', __name__, url_prefix='/admin/eposone')


def _require_eposone_admin():
    if not user_can_see_tenant_admin_menu(current_user):
        return redirect(url_for('dashboard'))
    return None


@eposone_bp.route('/')
@eposone_bp.route('/dashboard')
@login_required
def eposone_home():
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.dashboard import CommerceDashboardService
    from nodeone.core.platform.runtime import resolve_organization_id

    kpis = None
    recent_reports: list = []
    oid = resolve_organization_id()
    if oid is not None:
        kpis = CommerceDashboardService.get_snapshot(int(oid))
        recent_reports = CommerceDashboardService.list_recent_report_events(int(oid), limit=8)
    return render_template(
        'eposone/dashboard.html',
        compose_links=_compose_links(),
        kpis=kpis,
        recent_reports=recent_reports,
    )


@eposone_bp.route('/orders/<int:order_id>')
@login_required
def eposone_order_detail(order_id: int):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.order import OrderService
    from nodeone.core.platform.runtime import resolve_organization_id

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    order = OrderService.get(int(oid), int(order_id))
    if order is None:
        abort(404)
    return render_template(
        'eposone/order_detail.html',
        order=order,
    )


@eposone_bp.route('/contacts/create', methods=['POST'])
@login_required
def eposone_contact_create():
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.core.services.contacts import ContactService

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    payload = {
        'contact_type': (request.form.get('contact_type') or 'person').strip(),
        'display_name': (request.form.get('display_name') or '').strip(),
        'first_name': (request.form.get('first_name') or '').strip(),
        'last_name': (request.form.get('last_name') or '').strip(),
        'email': (request.form.get('email') or '').strip(),
        'phone': (request.form.get('phone') or '').strip(),
        'mobile': (request.form.get('mobile') or '').strip(),
        'tax_id': (request.form.get('tax_id') or '').strip(),
        'identification_type': (request.form.get('identification_type') or 'consumer_final').strip(),
        'is_customer': request.form.get('is_customer') == '1',
        'active': True,
    }
    try:
        dto = ContactService.create(int(oid), payload)
    except ContactService.ValidationError as exc:
        flash(str(exc), 'danger')
        return redirect(url_for('eposone.eposone_section', slug='contacts'))
    flash(f'Cliente {dto.display_name} creado correctamente.', 'success')
    return redirect(url_for('eposone.eposone_section', slug='contacts', q=dto.display_name))


@eposone_bp.route('/orders/new', methods=['GET', 'POST'])
@login_required
def eposone_order_new():
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    from nodeone.core.commerce.order import OrderService, OrderValidationError
    from nodeone.core.platform.runtime import resolve_organization_id
    from nodeone.core.services.contacts import ContactService
    from nodeone.core.services.product import ProductService

    oid = resolve_organization_id()
    if oid is None:
        abort(400)
    contacts, _ = ContactService.search(int(oid), limit=100)
    products = ProductService.search(int(oid), limit=100)
    form_data = {
        'contact_id': '',
        'product_ref': '',
        'description': '',
        'quantity': '1',
        'unit_price': '',
        'notes': '',
    }

    if request.method == 'POST':
        form_data = {
            'contact_id': (request.form.get('contact_id') or '').strip(),
            'product_ref': (request.form.get('product_ref') or '').strip(),
            'description': (request.form.get('description') or '').strip(),
            'quantity': (request.form.get('quantity') or '1').strip(),
            'unit_price': (request.form.get('unit_price') or '').strip(),
            'notes': (request.form.get('notes') or '').strip(),
        }
        try:
            qty = float(form_data['quantity'] or 1)
            unit_price = float(form_data['unit_price'] or 0)
        except ValueError:
            flash('Cantidad o precio no válidos.', 'danger')
            return render_template(
                'eposone/order_new.html',
                contacts=contacts,
                products=products,
                form_data=form_data,
            )
        line: dict = {
            'description': form_data['description'],
            'quantity': qty,
            'unit_price': unit_price,
        }
        if form_data['product_ref']:
            line['product_ref'] = form_data['product_ref']
        body: dict = {'lines': [line]}
        if form_data['notes']:
            body['notes'] = form_data['notes']
        if form_data['contact_id']:
            body['contact_id'] = int(form_data['contact_id'])
        try:
            dto = OrderService.create(int(oid), body, source_app_id='eposone')
        except OrderValidationError as exc:
            flash(str(exc).replace('_', ' '), 'danger')
            return render_template(
                'eposone/order_new.html',
                contacts=contacts,
                products=products,
                form_data=form_data,
            )
        flash(f'Pedido {dto.order_ref} creado.', 'success')
        return redirect(url_for('eposone.eposone_order_detail', order_id=dto.id))

    return render_template(
        'eposone/order_new.html',
        contacts=contacts,
        products=products,
        form_data=form_data,
    )


@eposone_bp.route('/section/<slug>')
@login_required
def eposone_section(slug: str):
    denied = _require_eposone_admin()
    if denied is not None:
        return denied
    key = (slug or '').strip().lower()
    if key not in EPOSONE_SECTION_SLUGS:
        abort(404)
    title, description = EPOSONE_SECTIONS[key]
    if key == 'orders':
        from nodeone.core.commerce.order import OrderService
        from nodeone.core.platform.runtime import resolve_organization_id

        oid = resolve_organization_id()
        orders: list = []
        orders_total = 0
        status_filter = (request.args.get('status') or '').strip() or None
        if oid is not None:
            orders, orders_total = OrderService.search(
                int(oid),
                status=status_filter,
                limit=50,
            )
        return render_template(
            'eposone/orders.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            orders=orders,
            orders_total=orders_total,
            status_filter=status_filter or '',
        )
    if key == 'contacts':
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.core.services.contacts import ContactService

        oid = resolve_organization_id()
        contacts: list = []
        contacts_total = 0
        q = (request.args.get('q') or '').strip()
        if oid is not None:
            contacts, contacts_total = ContactService.search(int(oid), q=q, limit=50)
        return render_template(
            'eposone/contacts.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            contacts=contacts,
            contacts_total=contacts_total,
            search_q=q,
        )
    if key == 'products':
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.core.services.product import ProductService

        oid = resolve_organization_id()
        products: list = []
        if oid is not None:
            products = ProductService.search(int(oid), limit=100)
        return render_template(
            'eposone/products.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            products=products,
            products_total=len(products),
        )
    if key == 'kds':
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.modules.eposone.kds_service import KdsService

        oid = resolve_organization_id()
        tickets: list = []
        if oid is not None:
            tickets = KdsService.list_tickets(int(oid), limit=30)
        return render_template(
            'eposone/kds.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            tickets=tickets,
        )
    if key == 'delivery':
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.modules.eposone.delivery_service import EposoneDeliveryService
        from models.eposone_delivery import EposoneDelivery

        oid = resolve_organization_id()
        deliveries: list = []
        if oid is not None:
            rows = (
                EposoneDelivery.query.filter_by(organization_id=int(oid))
                .order_by(EposoneDelivery.id.desc())
                .limit(30)
                .all()
            )
            deliveries = [EposoneDeliveryService.to_detail_dict(r) for r in rows]
        return render_template(
            'eposone/delivery.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            deliveries=deliveries,
        )
    if key == 'digital-menu':
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.modules.eposone.digital_menu_service import DigitalMenuService

        oid = resolve_organization_id()
        menus: list = []
        if oid is not None:
            menus = [
                {
                    **m.to_dict(),
                    'public_url': DigitalMenuService.public_menu_url(m.public_token),
                }
                for m in DigitalMenuService.list_menus(int(oid))
            ]
        return render_template(
            'eposone/digital_menu.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            menus=menus,
        )
    if key == 'branches':
        from nodeone.core.master.constants import ORG_UNIT_TYPE_BRANCH
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.core.services.org_unit import OrgUnitService

        oid = resolve_organization_id()
        branches: list = []
        if oid is not None:
            branches = OrgUnitService.list_units(int(oid), unit_type=ORG_UNIT_TYPE_BRANCH)
        return render_template(
            'eposone/branches.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            branches=branches,
            branches_total=len(branches),
        )
    if key == 'inventory':
        from nodeone.core.commerce.stock import StockService
        from nodeone.core.master.constants import ORG_UNIT_TYPE_WAREHOUSE
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.core.services.org_unit import OrgUnitService

        oid = resolve_organization_id()
        warehouses: list = []
        stock_balances: list = []
        if oid is not None:
            warehouses = OrgUnitService.list_units(int(oid), unit_type=ORG_UNIT_TYPE_WAREHOUSE)
            stock_balances = StockService.list_balances(int(oid), limit=100)
        return render_template(
            'eposone/warehouses.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            warehouses=warehouses,
            warehouses_total=len(warehouses),
            stock_balances=stock_balances,
            stock_balances_total=len(stock_balances),
        )
    if key == 'registers':
        from nodeone.core.master.constants import ORG_UNIT_TYPE_REGISTER
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.core.services.org_unit import OrgUnitService

        oid = resolve_organization_id()
        registers: list = []
        if oid is not None:
            registers = OrgUnitService.list_units(int(oid), unit_type=ORG_UNIT_TYPE_REGISTER)
        return render_template(
            'eposone/registers.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            registers=registers,
            registers_total=len(registers),
        )
    if key == 'terminals':
        from nodeone.core.commerce.pos import PosTerminalService
        from nodeone.core.master.constants import ORG_UNIT_TYPE_POS_TERMINAL
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.core.services.org_unit import OrgUnitService

        oid = resolve_organization_id()
        pos_units: list = []
        devices: list = []
        if oid is not None:
            pos_units = OrgUnitService.list_units(int(oid), unit_type=ORG_UNIT_TYPE_POS_TERMINAL)
            devices = PosTerminalService.list_terminals(int(oid), limit=50)
        return render_template(
            'eposone/terminals.html',
            section_slug=key,
            section_title=title,
            section_description=description,
            pos_units=pos_units,
            pos_units_total=len(pos_units),
            devices=devices,
            devices_total=len(devices),
        )
    return render_template(
        'eposone/section.html',
        section_slug=key,
        section_title=title,
        section_description=description,
    )


def _compose_links() -> list[dict[str, str]]:
    """Enlaces a capacidades Core disponibles (sin importar apps académicas)."""
    from flask import current_app

    from nodeone.core.platform.runtime import has_saas_module, resolve_organization_id

    oid = resolve_organization_id()
    links: list[dict[str, str]] = []

    def _add(label: str, endpoint: str, module_code: str | None = None) -> None:
        if endpoint not in current_app.view_functions:
            return
        if module_code and not has_saas_module(module_code, oid):
            return
        try:
            links.append({'label': label, 'url': url_for(endpoint)})
        except Exception:
            pass

    _add('Clientes (CRM completo)', 'contacts_admin.contacts_index', 'contacts')
    _add('Cotizaciones / ventas', 'admin_sales_quotations', 'sales')
    try:
        links.append({'label': 'Catálogo productos', 'url': url_for('eposone.eposone_section', slug='products')})
    except Exception:
        pass
    _add('Productos (legacy)', 'admin_services_catalog.admin_services', 'sales')
    _add('Inventario (contador)', 'contador.contador_index', 'contador')
    _add('Reportes ventas', 'admin_analytics_sales', 'analytics')
    return links
