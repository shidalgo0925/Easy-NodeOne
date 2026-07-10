"""Navegación nativa EPosOne — UX V3.2 (única nav principal de la app)."""

from __future__ import annotations

from nodeone.core.nav_menu import NavContext
from nodeone.core.platform.app_nav import AppNavItem, AppNavTree, safe_url_for


def _v_eposone(ctx: NavContext) -> bool:
    return (
        ctx.saas_module_enabled('eposone')
        and ctx.nav_can('payments.view')
        and ctx.has_view_endpoint('eposone.eposone_home')
    )


def _v_sales(ctx: NavContext) -> bool:
    return (
        _v_eposone(ctx)
        and ctx.saas_module_enabled('sales')
        and ctx.has_view_endpoint('admin_sales_quotations')
    )


def _v_contador(ctx: NavContext) -> bool:
    return (
        _v_eposone(ctx)
        and ctx.saas_module_enabled('contador')
        and ctx.has_view_endpoint('contador.contador_index')
    )


def _v_analytics(ctx: NavContext) -> bool:
    """Analítica POS vive en EPosOne (UX-T4); no depende del módulo BI plataforma."""
    return _v_eposone(ctx) and ctx.has_view_endpoint('eposone.eposone_analytics')


def _section(slug: str) -> str:
    return safe_url_for('eposone.eposone_section', slug=slug)


def build_nav_tree(ctx: NavContext) -> AppNavTree:
    orders_prefixes = (
        '/admin/eposone/section/orders',
        '/admin/eposone/orders',
    )
    return AppNavTree(
        app_id='eposone',
        nav_area_id='eposone',
        label='EPosOne',
        icon='fas fa-cash-register',
        home_url=safe_url_for('eposone.eposone_home'),
        domains=(
            AppNavItem(
                'dashboard',
                'Dashboard',
                'fas fa-chart-line',
                url=safe_url_for('eposone.eposone_home'),
                visible=_v_eposone,
                active_endpoints=('eposone.eposone_home',),
                active_path_prefixes=('/admin/eposone/dashboard',),
            ),
            AppNavItem(
                'comercial',
                'Comercial',
                'fas fa-receipt',
                children=(
                    AppNavItem(
                        'pedidos',
                        'Pedidos',
                        'fas fa-shopping-basket',
                        url=_section('orders'),
                        visible=_v_eposone,
                        active_path_prefixes=orders_prefixes,
                    ),
                    AppNavItem(
                        'ventas',
                        'Ventas',
                        'fas fa-file-invoice-dollar',
                        url=safe_url_for('admin_sales_quotations'),
                        visible=_v_sales,
                        active_endpoints=(
                            'admin_sales_quotations',
                            'admin_sales_quotation_form',
                            'admin_sales_commercial_contacts',
                        ),
                        active_path_prefixes=('/admin/sales/quotations', '/admin/sales/commercial-contacts'),
                    ),
                    AppNavItem(
                        'clientes',
                        'Clientes',
                        'fas fa-user-friends',
                        url=_section('contacts'),
                        visible=_v_eposone,
                        active_path_prefixes=('/admin/eposone/section/contacts',),
                    ),
                    AppNavItem(
                        'kds',
                        'KDS',
                        'fas fa-utensils',
                        url=_section('kds'),
                        visible=_v_eposone,
                        active_path_prefixes=('/admin/eposone/section/kds',),
                    ),
                    AppNavItem(
                        'delivery',
                        'Delivery',
                        'fas fa-motorcycle',
                        url=_section('delivery'),
                        visible=_v_eposone,
                        active_path_prefixes=('/admin/eposone/section/delivery',),
                    ),
                    AppNavItem(
                        'menu-digital',
                        'Menú digital',
                        'fas fa-qrcode',
                        url=_section('digital-menu'),
                        visible=_v_eposone,
                        active_path_prefixes=('/admin/eposone/section/digital-menu',),
                    ),
                ),
            ),
            AppNavItem(
                'catalogo',
                'Catálogo',
                'fas fa-box-open',
                children=(
                    AppNavItem(
                        'productos',
                        'Productos',
                        'fas fa-box',
                        url=_section('products'),
                        visible=_v_eposone,
                        active_path_prefixes=('/admin/eposone/section/products',),
                    ),
                    AppNavItem(
                        'promociones',
                        'Promociones',
                        'fas fa-tags',
                        url=_section('promotions'),
                        visible=_v_eposone,
                        active_path_prefixes=('/admin/eposone/section/promotions',),
                    ),
                ),
            ),
            AppNavItem(
                'inventario',
                'Inventario',
                'fas fa-warehouse',
                children=(
                    AppNavItem(
                        'existencias',
                        'Existencias',
                        'fas fa-boxes',
                        url=_section('inventory'),
                        visible=lambda c: _v_eposone(c) and not _v_contador(c),
                        active_path_prefixes=('/admin/eposone/section/inventory',),
                    ),
                    AppNavItem(
                        'contador',
                        'Inventario',
                        'fas fa-boxes',
                        url=safe_url_for('contador.contador_index'),
                        visible=_v_contador,
                        active_blueprints=('contador',),
                        active_path_prefixes=('/admin/contador',),
                    ),
                ),
            ),
            AppNavItem(
                'organizacion',
                'Organización',
                'fas fa-sitemap',
                children=(
                    AppNavItem(
                        'sucursales',
                        'Sucursales',
                        'fas fa-store',
                        url=_section('branches'),
                        visible=_v_eposone,
                        active_path_prefixes=('/admin/eposone/section/branches',),
                    ),
                    AppNavItem(
                        'pos-points',
                        'Puntos de Venta',
                        'fas fa-map-marker-alt',
                        url=_section('pos-points'),
                        visible=_v_eposone,
                        active_path_prefixes=('/admin/eposone/section/pos-points',),
                    ),
                    AppNavItem(
                        'terminales',
                        'Dispositivos',
                        'fas fa-desktop',
                        url=_section('terminals'),
                        visible=_v_eposone,
                        active_path_prefixes=('/admin/eposone/section/terminals',),
                    ),
                    AppNavItem(
                        'cajas',
                        'Cajas',
                        'fas fa-cash-register',
                        url=_section('registers'),
                        visible=_v_eposone,
                        active_path_prefixes=('/admin/eposone/section/registers',),
                    ),
                    AppNavItem(
                        'turnos',
                        'Turnos',
                        'fas fa-user-clock',
                        url=_section('shifts'),
                        visible=_v_eposone,
                        active_path_prefixes=('/admin/eposone/section/shifts',),
                    ),
                ),
            ),
            AppNavItem(
                'inteligencia',
                'Inteligencia',
                'fas fa-chart-bar',
                children=(
                    AppNavItem(
                        'reportes',
                        'Analítica POS',
                        'fas fa-chart-line',
                        url=safe_url_for('eposone.eposone_analytics'),
                        visible=_v_analytics,
                        active_endpoints=('eposone.eposone_analytics',),
                        active_path_prefixes=('/admin/eposone/analytics',),
                    ),
                ),
            ),
            AppNavItem(
                'sistema',
                'Sistema',
                'fas fa-cog',
                children=(
                    AppNavItem(
                        'configuracion',
                        'Configuración',
                        'fas fa-sliders-h',
                        url=_section('settings'),
                        visible=_v_eposone,
                        active_path_prefixes=('/admin/eposone/section/settings',),
                    ),
                ),
            ),
        ),
    )
