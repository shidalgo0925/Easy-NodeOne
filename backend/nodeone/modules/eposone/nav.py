"""Navegación nativa EPosOne — UX Roadmap V1.0 Sprint 7 (operativa)."""

from __future__ import annotations

from nodeone.core.nav_menu import NavContext
from nodeone.core.platform.app_nav import AppNavItem, AppNavTree, safe_url_for


def _v_eposone(ctx: NavContext) -> bool:
    return (
        ctx.saas_module_enabled('eposone')
        and ctx.nav_can('payments.view')
        and ctx.has_view_endpoint('eposone.eposone_home')
    )


def _v_contador(ctx: NavContext) -> bool:
    return (
        _v_eposone(ctx)
        and ctx.saas_module_enabled('contador')
        and ctx.has_view_endpoint('contador.contador_index')
    )


def _v_analytics(ctx: NavContext) -> bool:
    """Analítica POS vive en EPosOne; no depende del módulo BI plataforma."""
    return _v_eposone(ctx) and ctx.has_view_endpoint('eposone.eposone_analytics')


def _section(slug: str) -> str:
    return safe_url_for('eposone.eposone_section', slug=slug)


def build_nav_tree(ctx: NavContext) -> AppNavTree:
    """Menú operativo corto — elementos técnicos bajo Configuración."""
    orders_prefixes = (
        '/admin/eposone/section/orders',
        '/admin/eposone/orders',
    )
    use_contador = _v_contador(ctx)
    inventario_url = (
        safe_url_for('contador.contador_index') if use_contador else _section('inventory')
    )
    inventario_prefixes = (
        ('/admin/contador',) if use_contador else ('/admin/eposone/section/inventory',)
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
                'pedidos',
                'Pedidos',
                'fas fa-receipt',
                url=_section('orders'),
                visible=_v_eposone,
                active_path_prefixes=orders_prefixes,
            ),
            AppNavItem(
                'productos',
                'Productos',
                'fas fa-box-open',
                url=_section('products'),
                visible=_v_eposone,
                active_path_prefixes=('/admin/eposone/section/products',),
            ),
            AppNavItem(
                'inventario',
                'Inventario',
                'fas fa-warehouse',
                url=inventario_url,
                visible=_v_eposone,
                active_blueprints=('contador',) if use_contador else (),
                active_path_prefixes=inventario_prefixes,
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
                'caja',
                'Caja',
                'fas fa-cash-register',
                children=(
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
                'reportes',
                'Reportes',
                'fas fa-chart-bar',
                url=safe_url_for('eposone.eposone_analytics'),
                visible=_v_analytics,
                active_endpoints=('eposone.eposone_analytics',),
                active_path_prefixes=('/admin/eposone/analytics',),
            ),
            AppNavItem(
                'configuracion',
                'Configuración',
                'fas fa-cog',
                children=(
                    AppNavItem(
                        'ajustes',
                        'Ajustes generales',
                        'fas fa-sliders-h',
                        url=_section('settings'),
                        visible=_v_eposone,
                        active_path_prefixes=('/admin/eposone/section/settings',),
                    ),
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
                        'Puntos de venta',
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
                        'promociones',
                        'Promociones',
                        'fas fa-tags',
                        url=_section('promotions'),
                        visible=_v_eposone,
                        active_path_prefixes=('/admin/eposone/section/promotions',),
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
        ),
    )
