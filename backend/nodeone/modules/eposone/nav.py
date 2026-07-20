"""Navegación nativa EPosOne — Operación vs Infraestructura (V1.0)."""

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
    """Conteo físico (módulo Contador) — no reemplaza Inventario operativo."""
    return (
        _v_eposone(ctx)
        and ctx.saas_module_enabled('contador')
        and ctx.has_view_endpoint('contador.contador_index')
    )


def _section(slug: str) -> str:
    return safe_url_for('eposone.eposone_section', slug=slug)


def build_nav_tree(ctx: NavContext) -> AppNavTree:
    """Operación diaria arriba · Infraestructura y módulos auxiliares aparte."""
    orders_prefixes = (
        '/admin/eposone/section/orders',
        '/admin/eposone/orders',
    )
    infra_prefixes = (
        '/admin/eposone/section/organization',
        '/admin/eposone/section/branches',
        '/admin/eposone/section/pos-points',
        '/admin/eposone/section/registers',
        '/admin/eposone/section/terminals',
        '/admin/eposone/section/licenses',
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
                url=_section('inventory'),
                visible=_v_eposone,
                active_path_prefixes=('/admin/eposone/section/inventory',),
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
                        'turnos',
                        'Turnos',
                        'fas fa-clock',
                        url=_section('shifts'),
                        visible=_v_eposone,
                        active_path_prefixes=('/admin/eposone/section/shifts',),
                    ),
                    AppNavItem(
                        'cajeros',
                        'Cajeros',
                        'fas fa-user-tag',
                        url=_section('cashiers'),
                        visible=_v_eposone,
                        active_path_prefixes=('/admin/eposone/section/cashiers',),
                    ),
                ),
                active_path_prefixes=(
                    '/admin/eposone/section/shifts',
                    '/admin/eposone/section/cashiers',
                ),
            ),
            AppNavItem(
                'infraestructura',
                'Infraestructura',
                'fas fa-server',
                children=(
                    AppNavItem(
                        'organization',
                        'Empresa',
                        'fas fa-building',
                        url=_section('organization'),
                        visible=_v_eposone,
                        active_path_prefixes=('/admin/eposone/section/organization',),
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
                        'cajas',
                        'Cajas',
                        'fas fa-cash-register',
                        url=_section('registers'),
                        visible=_v_eposone,
                        active_path_prefixes=('/admin/eposone/section/registers',),
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
                        'licencias',
                        'Licencias',
                        'fas fa-key',
                        url=_section('licenses'),
                        visible=_v_eposone,
                        active_path_prefixes=('/admin/eposone/section/licenses',),
                    ),
                ),
                active_path_prefixes=infra_prefixes,
            ),
            AppNavItem(
                'mas',
                'Más',
                'fas fa-ellipsis-h',
                children=(
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
                        'Cocina (KDS)',
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
                    AppNavItem(
                        'conteo-fisico',
                        'Conteo físico',
                        'fas fa-clipboard-list',
                        url=safe_url_for('contador.contador_index'),
                        visible=_v_contador,
                        active_blueprints=('contador',),
                        active_path_prefixes=('/admin/contador',),
                    ),
                ),
            ),
        ),
    )
