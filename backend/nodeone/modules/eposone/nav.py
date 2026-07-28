"""Navegación nativa EPosOne — Operación / Admin negocio / Plataforma (SA).

EP1: el menú no se recorta por host. Visibilidad = producto + rol + licencia (features).
"""

from __future__ import annotations

from nodeone.core.nav_menu import NavContext
from nodeone.core.platform.app_nav import AppNavItem, AppNavTree, safe_url_for


def _v_eposone(ctx: NavContext) -> bool:
    return (
        ctx.saas_module_enabled('eposone')
        and ctx.nav_can('payments.view')
        and ctx.has_view_endpoint('eposone.eposone_home')
    )


def _v_tenant_business_admin(ctx: NavContext) -> bool:
    """Admin del negocio (tenant) — no requiere ser SA."""
    return _v_eposone(ctx) and bool(getattr(ctx, 'show_tenant_admin_menu', False))


def _v_platform_sa(ctx: NavContext) -> bool:
    """SA ETS — contexto plataforma separado dentro del producto."""
    return _v_eposone(ctx) and bool(getattr(ctx, 'is_platform_admin', False))


def _v_platform_lab(ctx: NavContext) -> bool:
    """Lab QA: solo platform admin (User.is_admin), no admin tenant."""
    return _v_platform_sa(ctx)


def _v_feature(feature: str):
    """Visible si tiene EPosOne; el lock lo resuelve required_feature en serialize."""

    def _inner(ctx: NavContext) -> bool:
        return _v_eposone(ctx)

    return _inner


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
    """Operación · Administración del negocio (tenant) · Plataforma (SA) · Más."""
    orders_prefixes = (
        '/admin/eposone/section/orders',
        '/admin/eposone/orders',
    )
    admin_prefixes = (
        '/admin/eposone/section/organization',
        '/admin/eposone/section/branches',
        '/admin/eposone/section/pos-points',
        '/admin/eposone/section/registers',
        '/admin/eposone/section/cashiers',
        '/admin/identity',
        '/admin/company',
        '/admin/users',
        '/admin/payments',
        '/admin/configuration/taxes',
        '/admin/sales/taxes',
        '/admin/eposone/plan',
    )
    device_prefixes = (
        '/admin/eposone/section/terminals',
        '/admin/eposone/section/shifts',
    )
    platform_prefixes = (
        '/admin/organizations',
        '/admin/saas',
        '/admin/configuration',
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
                'administracion',
                'Administración',
                'fas fa-building',
                children=(
                    AppNavItem(
                        'organization',
                        'Empresa',
                        'fas fa-building',
                        url=_section('organization'),
                        visible=_v_tenant_business_admin,
                        active_path_prefixes=('/admin/eposone/section/organization',),
                    ),
                    AppNavItem(
                        'branding',
                        'Branding',
                        'fas fa-palette',
                        url=safe_url_for('admin_company_setup', step='branding'),
                        visible=_v_tenant_business_admin,
                        active_endpoints=('admin_company_setup', 'admin_identity'),
                        active_path_prefixes=('/admin/identity', '/admin/company'),
                    ),
                    AppNavItem(
                        'sucursales',
                        'Sucursales',
                        'fas fa-store',
                        url=_section('branches'),
                        visible=_v_tenant_business_admin,
                        active_path_prefixes=('/admin/eposone/section/branches',),
                    ),
                    AppNavItem(
                        'pos-points',
                        'Puntos de venta',
                        'fas fa-map-marker-alt',
                        url=_section('pos-points'),
                        visible=_v_tenant_business_admin,
                        active_path_prefixes=('/admin/eposone/section/pos-points',),
                    ),
                    AppNavItem(
                        'cajas',
                        'Cajas',
                        'fas fa-cash-register',
                        url=_section('registers'),
                        visible=_v_tenant_business_admin,
                        active_path_prefixes=('/admin/eposone/section/registers',),
                    ),
                    AppNavItem(
                        'cajeros',
                        'Cajeros',
                        'fas fa-user-tag',
                        url=_section('cashiers'),
                        visible=_v_tenant_business_admin,
                        active_path_prefixes=('/admin/eposone/section/cashiers',),
                    ),
                    AppNavItem(
                        'usuarios-org',
                        'Usuarios',
                        'fas fa-users-cog',
                        url=safe_url_for('admin_users'),
                        visible=_v_tenant_business_admin,
                        active_endpoints=('admin_users',),
                        active_path_prefixes=('/admin/users',),
                    ),
                    AppNavItem(
                        'metodos-pago',
                        'Métodos de pago',
                        'fas fa-credit-card',
                        url=safe_url_for('payments_admin.admin_payments'),
                        visible=_v_tenant_business_admin,
                        active_endpoints=('payments_admin.admin_payments',),
                        active_path_prefixes=('/admin/payments',),
                    ),
                    AppNavItem(
                        'impuestos',
                        'Impuestos',
                        'fas fa-percentage',
                        url=safe_url_for('admin_configuration_taxes'),
                        visible=_v_tenant_business_admin,
                        required_feature='fiscal',
                        active_endpoints=('admin_configuration_taxes', 'admin_sales_taxes'),
                        active_path_prefixes=(
                            '/admin/configuration/taxes',
                            '/admin/sales/taxes',
                        ),
                    ),
                    AppNavItem(
                        'mi-plan',
                        'Mi plan',
                        'fas fa-crown',
                        url=safe_url_for('eposone.eposone_my_plan'),
                        visible=_v_tenant_business_admin,
                        active_endpoints=('eposone.eposone_my_plan', 'eposone.eposone_plan_upgrade'),
                        active_path_prefixes=('/admin/eposone/plan',),
                    ),
                    AppNavItem(
                        'licencia-producto',
                        'Licencias de caja',
                        'fas fa-key',
                        url=_section('licenses'),
                        visible=_v_tenant_business_admin,
                        active_path_prefixes=('/admin/eposone/section/licenses',),
                    ),
                ),
                active_path_prefixes=admin_prefixes,
            ),            AppNavItem(
                'eposone-ops',
                'EPosOne',
                'fas fa-tablet-alt',
                children=(
                    AppNavItem(
                        'install-device',
                        'Instalar dispositivo',
                        'fas fa-mobile-alt',
                        url=_section('registers') + '?install=1',
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
                        'turnos',
                        'Turnos',
                        'fas fa-clock',
                        url=_section('shifts'),
                        visible=_v_eposone,
                        active_path_prefixes=('/admin/eposone/section/shifts',),
                    ),
                ),
                active_path_prefixes=device_prefixes,
            ),
            AppNavItem(
                'plataforma-ets',
                'Plataforma',
                'fas fa-cloud',
                children=(
                    AppNavItem(
                        'orgs-global',
                        'Organizaciones',
                        'fas fa-sitemap',
                        url=safe_url_for('admin_organizations_list'),
                        visible=_v_platform_sa,
                        active_endpoints=('admin_organizations_list',),
                        active_path_prefixes=('/admin/organizations',),
                    ),
                    AppNavItem(
                        'saas-modules',
                        'Módulos SaaS',
                        'fas fa-cubes',
                        url=safe_url_for('admin_saas_modules_page'),
                        visible=_v_platform_sa,
                        active_endpoints=('admin_saas_modules_page',),
                        active_path_prefixes=('/admin/saas',),
                    ),
                ),
                active_path_prefixes=platform_prefixes,
            ),
            AppNavItem(
                'lab-wipe',
                'Lab · Wipe día',
                'fas fa-flask',
                url=safe_url_for('eposone.eposone_lab_wipe_today'),
                visible=_v_platform_lab,
                active_endpoints=('eposone.eposone_lab_wipe_today',),
                active_path_prefixes=('/admin/eposone/lab/wipe-today',),
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
                        visible=_v_feature('promotions'),
                        required_feature='promotions',
                        active_path_prefixes=('/admin/eposone/section/promotions',),
                    ),
                    AppNavItem(
                        'kds',
                        'Cocina (KDS)',
                        'fas fa-utensils',
                        url=_section('kds'),
                        visible=_v_feature('kds'),
                        required_feature='kds',
                        active_path_prefixes=('/admin/eposone/section/kds',),
                    ),
                    AppNavItem(
                        'delivery',
                        'Delivery',
                        'fas fa-motorcycle',
                        url=_section('delivery'),
                        visible=_v_feature('delivery'),
                        required_feature='delivery',
                        active_path_prefixes=('/admin/eposone/section/delivery',),
                    ),
                    AppNavItem(
                        'analytics',
                        'Analytics',
                        'fas fa-chart-pie',
                        url=safe_url_for('eposone.eposone_plan_upgrade', feature='analytics'),
                        visible=_v_eposone,
                        required_feature='analytics',
                        active_path_prefixes=('/admin/eposone/plan/upgrade',),
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
