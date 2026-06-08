"""Menú admin tenant — app launcher SaaS + subnav horizontal por app."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from flask import has_request_context, request, url_for
from werkzeug.routing import BuildError


@dataclass
class NavContext:
    nav_can: Callable[[str], bool]
    saas_module_enabled: Callable[[str], bool]
    saas_module_enabled_chain: Callable[..., bool]
    has_view_endpoint: Callable[[str], bool]
    show_academic_admin_nav: bool
    office365_module_enabled: bool
    show_platform_admin_nav: bool
    is_platform_admin: bool
    is_advisor: bool
    show_tenant_admin_menu: bool


@dataclass
class NavAreaItem:
    id: str
    label: str
    icon: str
    endpoint: str
    url_path: str | None = None
    url_resolver: Callable[[NavContext], str] | None = None
    visible: Callable[[NavContext], bool] | None = None
    active_endpoints: tuple[str, ...] = ()
    active_blueprints: tuple[str, ...] = ()
    active_path_prefixes: tuple[str, ...] = ()
    dropdown_items: tuple['NavAreaItem', ...] = ()


@dataclass
class NavArea:
    id: str
    label: str
    icon: str
    items: tuple[NavAreaItem, ...]
    visible: Callable[[NavContext], bool] | None = None
    show_in_sidebar: bool = True
    zone_endpoints: tuple[str, ...] = ()
    zone_blueprints: tuple[str, ...] = ()
    zone_path_prefixes: tuple[str, ...] = ()


_CRM_EPS = (
    'admin_tenant_contacts',
    'admin_crm_dashboard',
    'admin_crm_kanban',
    'admin_crm_leads',
    'admin_crm_calendar',
    'admin_crm_table',
    'admin_crm_activities',
    'admin_crm_reports',
)

_ANALYTICS_EPS = (
    'admin_analytics',
    'admin_analytics_sales',
    'admin_analytics_crm',
    'admin_analytics_members',
    'admin_analytics_registrations',
)

_CONFIG_EPS = (
    'efactura_admin.efactura_config',
    'admin_crm_settings',
    'admin_communications.admin_communications_settings',
    'admin_configuration_taxes',
    'admin_identity',
    'admin_email',
    'media_admin.admin_media',
    'admin_ai',
    'admin_product_guide',
    'admin_appointments.admin_appointments_dashboard',
    'admin_appointments.create_appointment_type',
    'admin_appointments.edit_appointment_type',
    'admin_users',
)

_RBAC_EPS = (
    'admin_roles_matrix',
    'admin_roles_matrix_cell',
    'admin_roles_list',
    'admin_roles_detail',
    'admin_roles_users',
    'admin_permissions_list',
)

_PLATFORM_EPS = (
    'admin_organizations_list',
    'admin_organization_new',
    'admin_organization_edit',
    'admin_saas_modules_page',
    'admin_saas_catalog_list',
    'admin_saas_catalog_new',
    'admin_saas_catalog_edit',
    'admin_platform_setup',
    'admin_messaging',
    'admin_messaging_detail',
    'admin_backup.admin_backup',
)

_ACCOUNTING_EPS = (
    'accounting_core.accounts_list',
    'accounting_core.journals_list',
    'accounting_core.entries_list',
    'accounting_core.entries_new',
    'accounting_core.entry_detail',
    'accounting_core.receivables_list',
    'accounting_core.receivables_customers_list',
    'accounting_core.adjustments_list',
)

_WORKSHOP_OPS_EPS = (
    'admin_workshop_orders',
    'admin_workshop_order_new',
    'admin_workshop_order_detail',
)

_WORKSHOP_CONFIG_EPS = (
    'admin_workshop_settings',
    'admin_workshop_process_config',
)

_VENTAS_OPS_EPS = (
    'admin_sales_quotations',
    'admin_sales_quotation_form',
    'admin_sales_commercial_contacts',
    'admin_sales_commercial_contact_edit',
    'admin_analytics_sales',
)

_VENTAS_CATALOG_EPS = (
    'admin_sales_catalog',
    'admin_services_catalog.admin_services',
    'admin_services_catalog.admin_service_categories',
    'admin_plans',
    'admin_events.admin_events_index',
)

_VENTAS_CATALOG_PATH_PREFIXES = (
    '/admin/sales/catalog',
    '/admin/services',
    '/admin/service-categories',
    '/admin/plans',
    '/admin/events',
)


def _ep(endpoint: str) -> Callable[[NavContext], bool]:
    return lambda ctx: ctx.has_view_endpoint(endpoint)


def _v_contacts(ctx: NavContext) -> bool:
    return ctx.saas_module_enabled('contacts') and ctx.has_view_endpoint('contacts_admin.contacts_index')


def _v_crm(ctx: NavContext) -> bool:
    return (ctx.saas_module_enabled('crm_contacts') or ctx.saas_module_enabled('crm')) and ctx.nav_can('users.view')


def _v_ventas(ctx: NavContext) -> bool:
    return ctx.nav_can('payments.view') and ctx.saas_module_enabled('sales')


def _v_tienda(ctx: NavContext) -> bool:
    """Vitrina pública /services (compra y reservas del miembro)."""
    return ctx.saas_module_enabled('appointments') and ctx.has_view_endpoint('services.list')


def _v_catalog_productos(ctx: NavContext) -> bool:
    return _v_ventas(ctx) and ctx.has_view_endpoint('admin_services_catalog.admin_services')


def _v_catalog_servicios(ctx: NavContext) -> bool:
    return _v_ventas(ctx) and ctx.has_view_endpoint('admin_services_catalog.admin_service_categories')


def _v_catalog_membresias(ctx: NavContext) -> bool:
    return _v_membresias(ctx) and ctx.has_view_endpoint('admin_plans')


def _v_catalog_eventos(ctx: NavContext) -> bool:
    return _v_eventos(ctx) and ctx.has_view_endpoint('admin_events.admin_events_index')


def _v_catalog_hub(ctx: NavContext) -> bool:
    return any(
        (
            _v_catalog_productos(ctx),
            _v_catalog_servicios(ctx),
            _v_catalog_membresias(ctx),
            _v_catalog_eventos(ctx),
        )
    )


def _first_visible_dropdown_url_from(items: tuple[NavAreaItem, ...], ctx: NavContext) -> str:
    for sub in items:
        if _item_visible(sub, ctx):
            return item_url(sub, ctx)
    return '#'


_CATALOG_DROPDOWN_ITEMS: tuple[NavAreaItem, ...] = (
    NavAreaItem(
        'productos',
        'Productos',
        'fas fa-box',
        'admin_services_catalog.admin_services',
        visible=_v_catalog_productos,
        active_endpoints=('admin_services_catalog.admin_services',),
    ),
    NavAreaItem(
        'servicios',
        'Servicios',
        'fas fa-concierge-bell',
        'admin_services_catalog.admin_service_categories',
        visible=_v_catalog_servicios,
        active_endpoints=('admin_services_catalog.admin_service_categories',),
    ),
    NavAreaItem(
        'membresias',
        'Membresías',
        'fas fa-id-card',
        'admin_plans',
        visible=_v_catalog_membresias,
        active_endpoints=('admin_plans',),
    ),
    NavAreaItem(
        'eventos',
        'Eventos',
        'fas fa-calendar-check',
        'admin_events.admin_events_index',
        visible=_v_catalog_eventos,
        active_blueprints=('admin_events',),
        active_path_prefixes=('/admin/events',),
    ),
)

_WORKSHOP_CONFIG_DROPDOWN_ITEMS: tuple[NavAreaItem, ...] = (
    NavAreaItem(
        'inicio',
        'Inicio',
        'fas fa-home',
        'admin_workshop_settings',
        active_endpoints=('admin_workshop_settings',),
    ),
    NavAreaItem(
        'sla',
        'SLA',
        'fas fa-stopwatch',
        'admin_workshop_process_config',
        visible=_ep('admin_workshop_process_config'),
        active_endpoints=('admin_workshop_process_config',),
    ),
)


def _nav_menu_dropdown(
    item_id: str,
    label: str,
    icon: str,
    children: tuple[NavAreaItem, ...],
    *,
    visible: Callable[[NavContext], bool] | None = None,
) -> NavAreaItem:
    def _default_visible(c: NavContext) -> bool:
        return any(_item_visible(ch, c) for ch in children)

    vis = visible if visible is not None else _default_visible
    first_ep = children[0].endpoint if children else 'dashboard'
    return NavAreaItem(
        item_id,
        label,
        icon,
        first_ep,
        visible=vis,
        url_resolver=lambda ctx, ch=children: _first_visible_dropdown_url_from(ch, ctx),
        dropdown_items=children,
    )


_ANALYTICS_TABLEROS_ITEMS: tuple[NavAreaItem, ...] = (
    NavAreaItem(
        'ventas_kpi',
        'Ventas',
        'fas fa-chart-bar',
        'admin_analytics_sales',
        active_endpoints=('admin_analytics_sales',),
    ),
    NavAreaItem(
        'crm_kpi',
        'CRM',
        'fas fa-handshake',
        'admin_analytics_crm',
        active_endpoints=('admin_analytics_crm',),
    ),
    NavAreaItem(
        'miembros_kpi',
        'Miembros',
        'fas fa-users',
        'admin_analytics_members',
        active_endpoints=('admin_analytics_members',),
    ),
    NavAreaItem(
        'registros_kpi',
        'Registros',
        'fas fa-user-plus',
        'admin_analytics_registrations',
        active_endpoints=('admin_analytics_registrations',),
    ),
)

_CRM_PIPELINE_ITEMS: tuple[NavAreaItem, ...] = (
    NavAreaItem('leads', 'Leads', 'fas fa-user-plus', 'admin_crm_leads', active_endpoints=('admin_crm_leads',)),
    NavAreaItem(
        'pipeline',
        'Pipeline',
        'fas fa-filter',
        'admin_crm_table',
        visible=_ep('admin_crm_table'),
        active_endpoints=('admin_crm_table',),
    ),
    NavAreaItem(
        'oportunidades',
        'Oportunidades',
        'fas fa-bullseye',
        'admin_crm_dashboard',
        active_endpoints=('admin_crm_dashboard',),
    ),
    NavAreaItem(
        'actividades',
        'Actividades',
        'fas fa-tasks',
        'admin_crm_activities',
        active_endpoints=('admin_crm_activities',),
    ),
    NavAreaItem('kanban', 'Kanban', 'fas fa-columns', 'admin_crm_kanban', active_endpoints=('admin_crm_kanban',)),
)

_CONTADOR_DATOS_ITEMS: tuple[NavAreaItem, ...] = (
    NavAreaItem(
        'importar',
        'Importar XLS',
        'fas fa-file-upload',
        'contador.contador_importar',
        visible=lambda c: c.nav_can('contador.admin'),
        active_endpoints=(
            'contador.contador_importar',
            'contador.contador_importar_mapear',
            'contador.contador_importar_subir',
            'contador.contador_importar_automatico',
        ),
    ),
    NavAreaItem(
        'catalogo',
        'Catálogo',
        'fas fa-boxes',
        'contador.contador_catalogo',
        active_endpoints=('contador.contador_catalogo', 'contador.contador_catalogo_nuevo'),
    ),
)

_AGENDA_PLANIFICACION_ITEMS: tuple[NavAreaItem, ...] = (
    NavAreaItem(
        'calendario',
        'Calendario',
        'fas fa-calendar',
        'admin_appointments.calendar_view',
        visible=lambda c: c.nav_can('services.view') and c.has_view_endpoint('admin_appointments.calendar_view'),
        active_endpoints=('admin_appointments.calendar_view',),
    ),
    NavAreaItem(
        'disponibilidad',
        'Disponibilidad',
        'fas fa-clock',
        'admin_appointments.list_service_availability',
        visible=lambda c: c.nav_can('services.view') and c.has_view_endpoint('admin_appointments.list_service_availability'),
        active_endpoints=(
            'admin_appointments.configure_daily_availability',
            'admin_appointments.list_service_availability',
            'admin_appointments.manage_service_availability',
        ),
    ),
)

_MEMBRESIAS_OPERACION_ITEMS: tuple[NavAreaItem, ...] = (
    NavAreaItem('miembros', 'Miembros', 'fas fa-users', 'admin_memberships', active_endpoints=('admin_memberships',)),
    NavAreaItem('beneficios', 'Beneficios', 'fas fa-gift', 'admin_benefits', active_endpoints=('admin_benefits', 'benefits')),
)

_EVENTOS_GESTION_ITEMS: tuple[NavAreaItem, ...] = (
    NavAreaItem(
        'gestion',
        'Gestión de Eventos',
        'fas fa-calendar-alt',
        'admin_events.admin_events_index',
        active_blueprints=('admin_events',),
        active_endpoints=('admin_events.discounts_index',),
    ),
    NavAreaItem(
        'participantes',
        'Participantes',
        'fas fa-users',
        'events.list_events',
        active_blueprints=('events',),
    ),
    NavAreaItem(
        'inscripciones',
        'Inscripciones',
        'fas fa-user-plus',
        'events.list_events',
        active_blueprints=('events',),
    ),
    NavAreaItem(
        'descuentos',
        'Descuentos',
        'fas fa-percent',
        'admin_events.discounts_index',
        visible=lambda c: c.nav_can('payments.view'),
        active_endpoints=('admin_events.discounts_index',),
    ),
)

_EDUCACION_ACADEMICO_ITEMS: tuple[NavAreaItem, ...] = (
    NavAreaItem(
        'programas',
        'Programas (inscripción)',
        'fas fa-book-open',
        'academic_enrollment_admin.list_programs',
        active_blueprints=('academic_enrollment_admin',),
    ),
    NavAreaItem(
        'estudiantes',
        'Estudiantes',
        'fas fa-user-graduate',
        'academic_admin.admin_academic_students',
        active_endpoints=('academic_admin.admin_academic_students',),
    ),
    NavAreaItem(
        'cursos',
        'Cursos',
        'fas fa-book',
        'academic_admin.admin_academic_courses',
        active_endpoints=('academic_admin.admin_academic_courses',),
    ),
    NavAreaItem(
        'matriculas',
        'Matrículas',
        'fas fa-clipboard-list',
        'academic_admin.admin_academic_enrollments',
        active_endpoints=('academic_admin.admin_academic_enrollments',),
    ),
    NavAreaItem(
        'moodle',
        'Moodle',
        'fas fa-plug',
        'academic_admin.admin_academic_moodle',
        active_endpoints=('academic_admin.admin_academic_moodle',),
    ),
)

_PLATAFORMA_SAAS_ITEMS: tuple[NavAreaItem, ...] = (
    NavAreaItem(
        'empresas',
        'Organizaciones',
        'fas fa-building',
        'admin_organizations_list',
        active_endpoints=('admin_organizations_list', 'admin_organization_new', 'admin_organization_edit'),
    ),
    NavAreaItem(
        'modulos',
        'Módulos SaaS',
        'fas fa-puzzle-piece',
        'admin_saas_modules_page',
        active_endpoints=('admin_saas_modules_page',),
    ),
    NavAreaItem(
        'catalogo',
        'Catálogo',
        'fas fa-list',
        'admin_saas_catalog_list',
        active_endpoints=('admin_saas_catalog_list', 'admin_saas_catalog_new', 'admin_saas_catalog_edit'),
    ),
)

_PLATAFORMA_SISTEMA_ITEMS: tuple[NavAreaItem, ...] = (
    NavAreaItem(
        'usuarios',
        'Usuarios',
        'fas fa-users-cog',
        'admin_users',
        visible=lambda c: c.nav_can('users.view'),
        active_endpoints=('admin_users',),
    ),
    NavAreaItem(
        'logs',
        'Logs',
        'fas fa-stream',
        'admin_messaging',
        visible=lambda c: c.nav_can('reports.view') and c.has_view_endpoint('admin_messaging'),
        active_endpoints=('admin_messaging', 'admin_messaging_detail'),
    ),
    NavAreaItem(
        'respaldos',
        'Respaldos',
        'fas fa-database',
        'admin_backup.admin_backup',
        visible=lambda c: c.nav_can('system.settings.view') and c.has_view_endpoint('admin_backup.admin_backup'),
        active_endpoints=('admin_backup.admin_backup',),
    ),
)

_PERMISOS_ADMIN_ITEMS: tuple[NavAreaItem, ...] = (
    NavAreaItem(
        'matriz',
        'Matriz',
        'fas fa-th',
        'admin_roles_matrix',
        active_endpoints=('admin_roles_matrix', 'admin_roles_matrix_cell'),
    ),
    NavAreaItem(
        'roles',
        'Roles',
        'fas fa-user-tag',
        'admin_roles_list',
        visible=_ep('admin_roles_list'),
        active_endpoints=('admin_roles_list', 'admin_roles_detail', 'admin_roles_users'),
    ),
    NavAreaItem(
        'permisos_list',
        'Permisos',
        'fas fa-key',
        'admin_permissions_list',
        visible=_ep('admin_permissions_list'),
        active_endpoints=('admin_permissions_list',),
    ),
)

_MATRIZ_ODOO_NAV_ITEMS: tuple[NavAreaItem, ...] = (
    NavAreaItem(
        'inicio',
        'Inicio',
        'fas fa-home',
        'security_matrix.security_matrix_index',
        active_endpoints=('security_matrix.security_matrix_index',),
    ),
    NavAreaItem(
        'matriz_modulo',
        'Matriz por módulo',
        'fas fa-table',
        'security_matrix.security_matrix_matriz_view',
        active_endpoints=('security_matrix.security_matrix_matriz_view',),
    ),
    NavAreaItem(
        'catalogo',
        'Catálogo',
        'fas fa-list',
        'security_matrix.security_matrix_catalog_view',
        active_endpoints=('security_matrix.security_matrix_catalog_view',),
    ),
)

_COMUNICACION_CANALES_ITEMS: tuple[NavAreaItem, ...] = (
    NavAreaItem(
        'correo',
        'Correo',
        'fas fa-envelope-open',
        'integrations.office365_page',
        visible=lambda c: c.saas_module_enabled('communications') and c.office365_module_enabled,
        active_blueprints=('integrations',),
    ),
    NavAreaItem(
        'chatbots',
        'Chatbots',
        'fas fa-robot',
        'admin_chatbots',
        visible=lambda c: c.saas_module_enabled('chatbot'),
        active_endpoints=('admin_chatbots',),
    ),
    NavAreaItem(
        'notificaciones',
        'Notificaciones',
        'fas fa-bell',
        'admin_notifications',
        active_endpoints=('admin_notifications',),
    ),
)


def _v_analitica(ctx: NavContext) -> bool:
    return ctx.saas_module_enabled('analytics') and ctx.nav_can('analytics.view')


def _v_educacion(ctx: NavContext) -> bool:
    return ctx.show_academic_admin_nav


def _v_membresias(ctx: NavContext) -> bool:
    return ctx.saas_module_enabled('memberships') and ctx.nav_can('memberships.view')


def _v_eventos(ctx: NavContext) -> bool:
    return ctx.saas_module_enabled('events') and ctx.nav_can('reports.view')


def _v_taller(ctx: NavContext) -> bool:
    return ctx.saas_module_enabled('workshop')


def _v_workshop_config(ctx: NavContext) -> bool:
    return _v_taller(ctx)


def _v_contador(ctx: NavContext) -> bool:
    return (
        ctx.saas_module_enabled('contador')
        and ctx.has_view_endpoint('contador.contador_index')
        and (ctx.nav_can('contador.admin') or ctx.nav_can('contador.review') or ctx.nav_can('contador.capture'))
    )


def _v_agenda(ctx: NavContext) -> bool:
    return ctx.saas_module_enabled('appointments')


def _v_comunicacion(ctx: NavContext) -> bool:
    return ctx.nav_can('integrations.view')


def _v_certificados(ctx: NavContext) -> bool:
    """App Certificados (admin): módulo ``certificates``."""
    return ctx.saas_module_enabled('certificates') and ctx.has_view_endpoint(
        'admin_certificate_events'
    )


def _v_portal_mis_certificados(ctx: NavContext) -> bool:
    return (ctx.saas_module_enabled('events') or ctx.saas_module_enabled('certificates')) and ctx.has_view_endpoint(
        'certificates_page.certificates_page'
    )


def _v_email_marketing(ctx: NavContext) -> bool:
    """App Email marketing: solo módulo SaaS ``marketing_email`` (sin integraciones)."""
    return ctx.saas_module_enabled('marketing_email') and ctx.has_view_endpoint('admin_marketing')


def _v_facturas(ctx: NavContext) -> bool:
    return ctx.nav_can('payments.view') and ctx.saas_module_enabled('sales')


def _v_pagos(ctx: NavContext) -> bool:
    return (
        ctx.saas_module_enabled('payments')
        and ctx.nav_can('payments.manage')
        and ctx.has_view_endpoint('payments_admin.admin_payments')
    )


def _v_contabilidad(ctx: NavContext) -> bool:
    return ctx.nav_can('payments.view') and ctx.saas_module_enabled_chain('accounting_core', 'sales')


def _v_fe(ctx: NavContext) -> bool:
    return ctx.saas_module_enabled('efactura') and ctx.has_view_endpoint('efactura_admin.efactura_emissions')


def _v_cxc(ctx: NavContext) -> bool:
    return _v_contabilidad(ctx) and ctx.has_view_endpoint('accounting_core.receivables_list')


def _v_finanzas(ctx: NavContext) -> bool:
    return _v_facturas(ctx) or _v_contabilidad(ctx) or _v_fe(ctx)


def _v_config(ctx: NavContext) -> bool:
    return ctx.nav_can('system.settings.view')


def _v_configuracion(ctx: NavContext) -> bool:
    return _v_config(ctx) or _v_pagos(ctx)


def _v_plataforma(ctx: NavContext) -> bool:
    return ctx.show_platform_admin_nav and ctx.is_platform_admin


def _v_security_matrix(ctx: NavContext) -> bool:
    return (
        ctx.saas_module_enabled('security_matrix')
        and ctx.has_view_endpoint('security_matrix.security_matrix_index')
        and ctx.nav_can('security_matrix.admin')
    )


def _v_en1_roles_matrix(ctx: NavContext) -> bool:
    return (
        ctx.saas_module_enabled('rbac_matrix')
        and ctx.nav_can('roles.view')
        and ctx.has_view_endpoint('admin_roles_matrix')
    )


_FINANZAS_COBRO_ITEMS: tuple[NavAreaItem, ...] = (
    NavAreaItem(
        'facturas',
        'Facturas',
        'fas fa-file-invoice',
        'admin_accounting_invoices',
        url_path='/admin/accounting/invoices',
        visible=_v_facturas,
        active_endpoints=(
            'admin_accounting_invoices',
            'admin_accounting_invoice_new',
            'admin_accounting_invoice_form',
        ),
    ),
    NavAreaItem(
        'cxc',
        'Cuentas por cobrar',
        'fas fa-hand-holding-usd',
        'accounting_core.receivables_list',
        visible=_v_cxc,
        active_endpoints=('accounting_core.receivables_list', 'accounting_core.receivables_customers_list'),
    ),
)

_CONFIG_ORG_ITEMS: tuple[NavAreaItem, ...] = (
    NavAreaItem(
        'branding',
        'Branding',
        'fas fa-palette',
        'admin_identity',
        visible=_v_config,
        active_endpoints=('admin_identity',),
    ),
    NavAreaItem(
        'smtp',
        'SMTP',
        'fas fa-envelope',
        'admin_email',
        visible=_v_config,
        active_endpoints=('admin_email',),
    ),
    NavAreaItem(
        'media',
        'Multimedia',
        'fas fa-photo-video',
        'media_admin.admin_media',
        visible=lambda c: _v_config(c) and c.has_view_endpoint('media_admin.admin_media'),
        active_endpoints=('media_admin.admin_media',),
    ),
)

_CONFIG_FISCAL_ITEMS: tuple[NavAreaItem, ...] = (
    NavAreaItem(
        'impuestos',
        'Impuestos',
        'fas fa-percent',
        'admin_configuration_taxes',
        visible=_ep('admin_configuration_taxes'),
        active_endpoints=('admin_configuration_taxes',),
    ),
    NavAreaItem(
        'pagos',
        'Pagos',
        'fas fa-credit-card',
        'payments_admin.admin_payments',
        url_path='/admin/payments?context=config',
        visible=_v_pagos,
        active_endpoints=('payments_admin.admin_payments',),
        active_path_prefixes=('/admin/payments',),
    ),
    NavAreaItem(
        'fe_proveedor',
        'Proveedor FE',
        'fas fa-receipt',
        'efactura_admin.efactura_config',
        visible=lambda c: c.saas_module_enabled('efactura') and c.has_view_endpoint('efactura_admin.efactura_config'),
        active_endpoints=('efactura_admin.efactura_config',),
    ),
)

_CONFIG_ACCESO_ITEMS: tuple[NavAreaItem, ...] = (
    NavAreaItem(
        'usuarios',
        'Usuarios',
        'fas fa-users-cog',
        'admin_users',
        visible=lambda c: c.nav_can('users.view'),
        active_endpoints=('admin_users',),
    ),
    NavAreaItem(
        'comunicacion_cfg',
        'Comunicación',
        'fas fa-bell',
        'admin_communications.admin_communications_settings',
        visible=_ep('admin_communications.admin_communications_settings'),
        active_endpoints=('admin_communications.admin_communications_settings',),
    ),
)


# Endpoints y rutas de la app Certificados (independiente de Educación).
_CERTIFICADOS_ZONE_ENDPOINTS: tuple[str, ...] = (
    'admin_certificate_events',
    'admin_certificate_templates',
    'admin_certificate_template_editor',
    'admin_certificate_institutional_editor',
)

# Launcher lateral: enlaces fijos (Dashboard va en base.html) y grupos colapsables.
_SIDEBAR_TOP_LEVEL_AREA_IDS: tuple[str, ...] = (
    'tienda',
    'contactos',
)

@dataclass(frozen=True)
class NavLauncherGroup:
    id: str
    label: str
    icon: str
    area_ids: tuple[str, ...]


_SIDEBAR_LAUNCHER_GROUPS: tuple[NavLauncherGroup, ...] = (
    NavLauncherGroup(
        'comercial',
        'Comercial',
        'fas fa-briefcase',
        ('crm', 'taller', 'ventas', 'membresias', 'eventos', 'marketing_email'),
    ),
    NavLauncherGroup(
        'operaciones',
        'Operaciones',
        'fas fa-cogs',
        ('agenda', 'educacion', 'certificados', 'mis_certificados', 'contador'),
    ),
    NavLauncherGroup('finanzas', 'Finanzas', 'fas fa-file-invoice-dollar', ('finanzas',)),
    NavLauncherGroup('inteligencia', 'Inteligencia', 'fas fa-chart-line', ('analitica',)),
    NavLauncherGroup('sistema', 'Sistema', 'fas fa-server', ('plataforma',)),
)


APP_AREAS: tuple[NavArea, ...] = (
    NavArea(
        id='analitica',
        label='Analítica',
        icon='fas fa-chart-line',
        visible=_v_analitica,
        zone_endpoints=_ANALYTICS_EPS,
        items=(
            NavAreaItem(
                'ejecutivo',
                'Ejecutivo',
                'fas fa-chart-pie',
                'admin_analytics',
                active_endpoints=('admin_analytics',),
            ),
            _nav_menu_dropdown('tableros', 'Tableros', 'fas fa-chart-bar', _ANALYTICS_TABLEROS_ITEMS),
        ),
    ),
    NavArea(
        id='crm',
        label='CRM',
        icon='fas fa-handshake',
        visible=_v_crm,
        zone_endpoints=_CRM_EPS,
        items=(
            _nav_menu_dropdown('pipeline', 'CRM', 'fas fa-handshake', _CRM_PIPELINE_ITEMS),
            NavAreaItem(
                'reportes',
                'Reportes',
                'fas fa-chart-bar',
                'admin_crm_reports',
                active_endpoints=('admin_crm_reports',),
            ),
        ),
    ),
    # Taller antes que Ventas: el flujo operativo arranca en la orden de taller → cotización → factura.
    NavArea(
        id='taller',
        label='Taller',
        icon='fas fa-car-side',
        visible=_v_taller,
        zone_path_prefixes=('/admin/workshop',),
        zone_endpoints=_WORKSHOP_OPS_EPS,
        items=(
            NavAreaItem(
                'ordenes',
                'Monitor',
                'fas fa-clipboard-list',
                'admin_workshop_orders',
                active_endpoints=_WORKSHOP_OPS_EPS,
            ),
            NavAreaItem(
                'recepcion',
                'Recepción',
                'fas fa-door-open',
                'admin_workshop_order_new',
                active_endpoints=('admin_workshop_order_new',),
            ),
            NavAreaItem(
                'reportes',
                'Reportes',
                'fas fa-chart-bar',
                'admin_workshop_orders',
                url_path='/admin/workshop/orders',
                active_endpoints=(),
            ),
            _nav_menu_dropdown(
                'configuracion',
                'Configuración',
                'fas fa-cog',
                _WORKSHOP_CONFIG_DROPDOWN_ITEMS,
                visible=_v_workshop_config,
            ),
        ),
    ),
    NavArea(
        id='ventas',
        label='Ventas',
        icon='fas fa-file-invoice-dollar',
        visible=_v_ventas,
        zone_endpoints=_VENTAS_OPS_EPS + _VENTAS_CATALOG_EPS,
        zone_path_prefixes=(
            '/admin/sales/quotations',
            '/admin/sales/commercial-contacts',
        )
        + _VENTAS_CATALOG_PATH_PREFIXES,
        items=(
            NavAreaItem(
                'cotizaciones',
                'Cotizaciones',
                'fas fa-file-alt',
                'admin_sales_quotations',
                url_path='/admin/sales/quotations',
                active_endpoints=(
                    'admin_sales_quotations',
                    'admin_sales_quotation_form',
                    'admin_sales_commercial_contacts',
                    'admin_sales_commercial_contact_edit',
                ),
            ),
            _nav_menu_dropdown(
                'catalogo',
                'Catálogo',
                'fas fa-store',
                _CATALOG_DROPDOWN_ITEMS,
                visible=_v_catalog_hub,
            ),
            NavAreaItem(
                'reportes',
                'Reportes',
                'fas fa-chart-bar',
                'admin_analytics_sales',
                url_path='/admin/analytics/sales?source=ventas',
                visible=lambda c: _v_ventas(c) and _v_analitica(c),
                active_endpoints=('admin_analytics_sales',),
            ),
        ),
    ),
    NavArea(
        id='tienda',
        label='Tienda',
        icon='fas fa-store',
        visible=_v_tienda,
        zone_blueprints=('services',),
        zone_endpoints=('services.list',),
        zone_path_prefixes=('/services',),
        items=(
            NavAreaItem(
                'vitrina',
                'Ver tienda',
                'fas fa-store',
                'services.list',
                active_blueprints=('services',),
                active_path_prefixes=('/services',),
            ),
        ),
    ),
    NavArea(
        id='contador',
        label='Contador',
        icon='fas fa-clipboard-list',
        visible=_v_contador,
        zone_blueprints=('contador', 'contador_api'),
        zone_path_prefixes=('/admin/contador', '/api/contador'),
        items=(
            NavAreaItem(
                'inicio',
                'Inicio',
                'fas fa-home',
                'contador.contador_index',
                active_endpoints=('contador.contador_index',),
            ),
            _nav_menu_dropdown('datos', 'Datos', 'fas fa-database', _CONTADOR_DATOS_ITEMS),
            NavAreaItem(
                'sesiones',
                'Sesiones',
                'fas fa-list-ol',
                'contador.contador_sesiones',
                active_endpoints=(
                    'contador.contador_sesiones',
                    'contador.contador_sesion_new',
                    'contador.contador_sesion_detail',
                    'contador.contador_sesion_captura',
                    'contador.contador_sesion_revision',
                    'contador.contador_sesion_exportar',
                    'contador.contador_line_historial',
                ),
            ),
        ),
    ),
    NavArea(
        id='contactos',
        label='Contactos',
        icon='fas fa-address-book',
        visible=_v_contacts,
        zone_blueprints=('contacts_admin',),
        zone_path_prefixes=('/admin/contacts',),
        items=(
            NavAreaItem(
                'listado',
                'Contactos',
                'fas fa-list',
                'contacts_admin.contacts_index',
                active_endpoints=(
                    'contacts_admin.contacts_index',
                    'contacts_admin.contacts_new',
                    'contacts_admin.contacts_detail',
                    'contacts_admin.contacts_edit',
                ),
                active_blueprints=('contacts_admin',),
            ),
        ),
    ),
    NavArea(
        id='agenda',
        label='Agenda',
        icon='fas fa-calendar-alt',
        visible=_v_agenda,
        zone_blueprints=('appointments', 'admin_appointments'),
        zone_endpoints=(
            'appointments.advisor_queue',
            'admin_appointments.calendar_view',
            'admin_appointments.configure_daily_availability',
            'admin_appointments.list_service_availability',
            'admin_appointments.manage_service_availability',
        ),
        items=(
            NavAreaItem(
                'citas',
                'Citas',
                'fas fa-calendar-check',
                'appointments.appointments_home',
                active_blueprints=('appointments',),
            ),
            _nav_menu_dropdown('planificacion', 'Planificación', 'fas fa-calendar', _AGENDA_PLANIFICACION_ITEMS),
        ),
    ),
    NavArea(
        id='membresias',
        label='Membresías',
        icon='fas fa-crown',
        visible=_v_membresias,
        zone_endpoints=('admin_plans', 'admin_memberships', 'admin_benefits', 'benefits'),
        items=(
            _nav_menu_dropdown('operacion', 'Operación', 'fas fa-users', _MEMBRESIAS_OPERACION_ITEMS),
            NavAreaItem(
                'planes',
                'Planes',
                'fas fa-layer-group',
                'admin_plans',
                visible=lambda c: _v_membresias(c) and not _v_catalog_membresias(c),
                active_endpoints=('admin_plans',),
            ),
        ),
    ),
    NavArea(
        id='eventos',
        label='Eventos',
        icon='fas fa-calendar-check',
        visible=_v_eventos,
        zone_blueprints=('events', 'admin_events'),
        items=(
            _nav_menu_dropdown('gestion', 'Gestión', 'fas fa-calendar-alt', _EVENTOS_GESTION_ITEMS),
            NavAreaItem(
                'reportes',
                'Reportes',
                'fas fa-chart-bar',
                'admin_events.admin_events_index',
                active_blueprints=('admin_events',),
            ),
        ),
    ),
    NavArea(
        id='certificados',
        label='Certificados',
        icon='fas fa-certificate',
        visible=_v_certificados,
        zone_endpoints=_CERTIFICADOS_ZONE_ENDPOINTS,
        zone_path_prefixes=('/admin/certificate',),
        zone_blueprints=(
            'certificates_builder',
            'certificates_api',
            'certificates_public',
        ),
        items=(
            NavAreaItem(
                'eventos',
                'Eventos',
                'fas fa-calendar-alt',
                'admin_certificate_events',
                active_endpoints=('admin_certificate_events',),
            ),
            NavAreaItem(
                'plantillas',
                'Plantillas',
                'fas fa-file-image',
                'admin_certificate_templates',
                active_endpoints=(
                    'admin_certificate_templates',
                    'admin_certificate_template_editor',
                ),
            ),
        ),
    ),
    NavArea(
        id='mis_certificados',
        label='Mis Certificados',
        icon='fas fa-id-card',
        visible=_v_portal_mis_certificados,
        zone_path_prefixes=('/certificates', '/my/certificates'),
        zone_blueprints=('certificates_page', 'my_event_certificates'),
        zone_endpoints=('certificates_page.certificates_page',),
        items=(
            NavAreaItem(
                'portal',
                'Mis Certificados',
                'fas fa-id-card',
                'certificates_page.certificates_page',
                active_endpoints=('certificates_page.certificates_page',),
                active_blueprints=('my_event_certificates',),
                active_path_prefixes=('/certificates', '/my/certificates'),
            ),
        ),
    ),
    NavArea(
        id='marketing_email',
        label='Email marketing',
        icon='fas fa-bullhorn',
        visible=_v_email_marketing,
        zone_path_prefixes=('/admin/marketing',),
        items=(
            NavAreaItem(
                'campanas',
                'Campañas',
                'fas fa-bullhorn',
                'admin_marketing',
                active_path_prefixes=('/admin/marketing',),
            ),
        ),
    ),
    NavArea(
        id='educacion',
        label='Educación',
        icon='fas fa-graduation-cap',
        visible=_v_educacion,
        zone_blueprints=('academic_admin', 'academic_enrollment_admin', 'academic_api'),
        zone_path_prefixes=('/admin/academic', '/admin/academic-enrollment'),
        zone_endpoints=(
            'academic_admin.admin_academic_students',
            'academic_admin.admin_academic_courses',
            'academic_admin.admin_academic_enrollments',
            'academic_admin.admin_academic_moodle',
            'academic_enrollment_admin.list_programs',
            'academic_enrollment_admin.program_new',
            'academic_enrollment_admin.program_edit',
        ),
        items=(
            _nav_menu_dropdown('academico', 'Académico', 'fas fa-book-open', _EDUCACION_ACADEMICO_ITEMS),
        ),
    ),
    NavArea(
        id='finanzas',
        label='Finanzas',
        icon='fas fa-coins',
        visible=_v_finanzas,
        zone_blueprints=('efactura_admin', 'efactura_api', 'accounting_core'),
        zone_path_prefixes=(
            '/admin/accounting',
            '/admin/efactura',
            '/api/admin/efactura',
        ),
        zone_endpoints=_ACCOUNTING_EPS
        + (
            'admin_accounting_invoices',
            'admin_accounting_invoice_new',
            'admin_accounting_invoice_form',
            'efactura_admin.efactura_emissions',
            'efactura_admin.efactura_test_invoice',
            'efactura_admin.efactura_logs',
        ),
        items=(
            _nav_menu_dropdown('cobro', 'Cobro', 'fas fa-hand-holding-usd', _FINANZAS_COBRO_ITEMS),
            NavAreaItem(
                'contabilidad',
                'Contabilidad',
                'fas fa-book',
                'accounting_core.entries_list',
                visible=_v_contabilidad,
                active_endpoints=_ACCOUNTING_EPS,
            ),
            NavAreaItem(
                'fe',
                'Fact. electrónica',
                'fas fa-receipt',
                'efactura_admin.efactura_emissions',
                visible=_v_fe,
                active_blueprints=('efactura_admin', 'efactura_api'),
                active_path_prefixes=('/admin/efactura', '/api/admin/efactura'),
            ),
        ),
    ),
    NavArea(
        id='plataforma',
        label='Plataforma',
        icon='fas fa-cloud',
        visible=_v_plataforma,
        zone_endpoints=_PLATFORM_EPS,
        items=(
            _nav_menu_dropdown('saas', 'SaaS', 'fas fa-cloud', _PLATAFORMA_SAAS_ITEMS),
            _nav_menu_dropdown('administracion', 'Administración', 'fas fa-cogs', _PLATAFORMA_SISTEMA_ITEMS),
            NavAreaItem(
                'guia',
                'Guía',
                'fas fa-route',
                'admin_platform_setup',
                visible=_ep('admin_platform_setup'),
                active_endpoints=('admin_platform_setup',),
            ),
        ),
    ),
    NavArea(
        id='permisos',
        label='Permisos',
        icon='fas fa-th',
        visible=_v_en1_roles_matrix,
        show_in_sidebar=False,
        zone_endpoints=_RBAC_EPS,
        zone_path_prefixes=('/admin/roles',),
        items=(
            _nav_menu_dropdown('admin', 'Administración', 'fas fa-th', _PERMISOS_ADMIN_ITEMS),
        ),
    ),
    NavArea(
        id='matriz_odoo',
        label='Matriz Odoo',
        icon='fas fa-shield-alt',
        visible=_v_security_matrix,
        show_in_sidebar=False,
        zone_blueprints=('security_matrix',),
        zone_path_prefixes=('/admin/security-matrix',),
        items=(
            _nav_menu_dropdown('nav', 'Navegación', 'fas fa-compass', _MATRIZ_ODOO_NAV_ITEMS),
        ),
    ),
    NavArea(
        id='config',
        label='Configuración',
        icon='fas fa-cog',
        visible=lambda c: c.show_tenant_admin_menu and _v_configuracion(c),
        show_in_sidebar=False,
        zone_endpoints=_CONFIG_EPS,
        items=(
            _nav_menu_dropdown('organizacion', 'Organización', 'fas fa-building', _CONFIG_ORG_ITEMS),
            _nav_menu_dropdown('fiscal', 'Fiscal', 'fas fa-percent', _CONFIG_FISCAL_ITEMS),
            _nav_menu_dropdown('acceso', 'Acceso', 'fas fa-users-cog', _CONFIG_ACCESO_ITEMS),
        ),
    ),
    NavArea(
        id='comunicacion',
        label='Comunicación',
        icon='fas fa-comments',
        visible=_v_comunicacion,
        show_in_sidebar=False,
        zone_blueprints=('integrations',),
        zone_endpoints=(
            'admin_chatbots',
            'admin_notifications',
            'office365_admin.admin_office365_requests',
        ),
        items=(
            _nav_menu_dropdown('canales', 'Canales', 'fas fa-comments', _COMUNICACION_CANALES_ITEMS),
        ),
    ),
)


def _item_visible(item: NavAreaItem, ctx: NavContext) -> bool:
    if item.visible is not None and not item.visible(ctx):
        return False
    if item.dropdown_items:
        return any(_item_visible(sub, ctx) for sub in item.dropdown_items)
    if item.url_path:
        return True
    return ctx.has_view_endpoint(item.endpoint)


def _area_visible(area: NavArea, ctx: NavContext) -> bool:
    if area.id != 'plataforma' and not ctx.show_tenant_admin_menu and area.show_in_sidebar:
        return False
    if area.visible is not None and not area.visible(ctx):
        return False
    if not area.show_in_sidebar:
        return True
    return any(_item_visible(it, ctx) for it in area.items)


def item_url(item: NavAreaItem, ctx: NavContext | None = None) -> str:
    if item.url_resolver is not None and ctx is not None:
        return item.url_resolver(ctx)
    if item.url_path:
        return item.url_path
    try:
        return url_for(item.endpoint)
    except (BuildError, RuntimeError):
        return '#'


def area_default_url(area: NavArea, ctx: NavContext) -> str:
    for it in area.items:
        if _item_visible(it, ctx):
            try:
                return item_url(it, ctx)
            except (BuildError, RuntimeError):
                continue
    try:
        return url_for('dashboard')
    except (BuildError, RuntimeError):
        return '/dashboard'


def _endpoint_active(item: NavAreaItem, ctx: NavContext | None = None) -> bool:
    if not has_request_context():
        return False
    if item.dropdown_items and ctx is not None:
        return any(_item_visible(sub, ctx) and _endpoint_active(sub, ctx) for sub in item.dropdown_items)
    ep = getattr(request, 'endpoint', None) or ''
    bp = getattr(request, 'blueprint', None) or ''
    path = (request.path or '') if request else ''
    if item.active_endpoints and ep in item.active_endpoints:
        return True
    if item.active_blueprints and bp in item.active_blueprints:
        if item.id == 'gestion' and ep == 'admin_events.discounts_index':
            return False
        return True
    for prefix in item.active_path_prefixes:
        if path.startswith(prefix):
            return True
    if not item.url_path and ep == item.endpoint:
        return True
    return False


def _area_matches_request(area: NavArea) -> bool:
    if not has_request_context():
        return False
    ep = getattr(request, 'endpoint', None) or ''
    bp = getattr(request, 'blueprint', None) or ''
    path = request.path or ''
    if area.zone_endpoints and ep in area.zone_endpoints:
        return True
    if area.zone_blueprints and bp in area.zone_blueprints:
        return True
    for prefix in area.zone_path_prefixes:
        if path.startswith(prefix):
            return True
    for item in area.items:
        if _endpoint_active(item):
            return True
    return False


def _serialize_bar_child(item: NavAreaItem, ctx: NavContext) -> dict[str, Any]:
    dropdown: list[dict[str, Any]] = []
    for sub in item.dropdown_items:
        if not _item_visible(sub, ctx):
            continue
        dropdown.append(
            {
                'id': sub.id,
                'label': sub.label,
                'icon': sub.icon,
                'url': item_url(sub, ctx),
                'active': _endpoint_active(sub, ctx),
            }
        )
    row: dict[str, Any] = {
        'id': item.id,
        'label': item.label,
        'icon': item.icon,
        'url': item_url(item, ctx),
        'active': _endpoint_active(item, ctx),
    }
    if dropdown:
        row['dropdown'] = dropdown
        row['dropdown_active'] = any(d['active'] for d in dropdown)
        row['active'] = False
    return row


def _active_child_label(children: list[dict[str, Any]]) -> str | None:
    for child in children:
        for sub in child.get('dropdown') or []:
            if sub.get('active'):
                return sub.get('label')
        if child.get('active') and not child.get('dropdown'):
            return child.get('label')
    return None


_ORG_PLATFORM_EPS = (
    'admin_organizations_list',
    'admin_organization_new',
    'admin_organization_edit',
)


def _in_rbac_zone() -> bool:
    if not has_request_context():
        return False
    ep = getattr(request, 'endpoint', None) or ''
    return ep in _RBAC_EPS


def _in_security_matrix_zone() -> bool:
    if not has_request_context():
        return False
    return (getattr(request, 'blueprint', None) or '') == 'security_matrix'


def _payments_nav_area_id(ctx: NavContext) -> str | None:
    """Matriz y panel de pagos: solo zona Configuración (engranaje), no Finanzas."""
    if not has_request_context():
        return None
    path = request.path or ''
    if not path.startswith('/admin/payments'):
        return None
    if _v_configuracion(ctx):
        return 'config'
    return None


def _analytics_sales_nav_area_id(ctx: NavContext) -> str | None:
    """KPI ventas: barra Ventas (operación) vs Analítica (módulo BI)."""
    if not has_request_context():
        return None
    ep = getattr(request, 'endpoint', None) or ''
    if ep != 'admin_analytics_sales':
        return None
    if request.args.get('source') == 'ventas' and _v_ventas(ctx):
        return 'ventas'
    if _v_analitica(ctx):
        return 'analitica'
    if _v_ventas(ctx):
        return 'ventas'
    return None


def _in_config_zone() -> bool:
    if not has_request_context():
        return False
    ep = getattr(request, 'endpoint', None) or ''
    if ep in _CONFIG_EPS:
        return True
    if ep == 'payments_admin.admin_payments':
        return True
    path = request.path or ''
    return path.startswith('/admin/payments')


def _in_contador_zone() -> bool:
    if not has_request_context():
        return False
    ep = getattr(request, 'endpoint', None) or ''
    if ep == 'contador.contador_config':
        return False
    bp = getattr(request, 'blueprint', None) or ''
    path = request.path or ''
    return bp in ('contador', 'contador_api') or path.startswith('/admin/contador') or path.startswith('/api/contador')


def _in_ventas_catalog_zone() -> bool:
    if not has_request_context():
        return False
    ep = getattr(request, 'endpoint', None) or ''
    if ep in _VENTAS_CATALOG_EPS:
        return True
    path = request.path or ''
    for prefix in _VENTAS_CATALOG_PATH_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


def _in_workshop_config_zone() -> bool:
    if not has_request_context():
        return False
    ep = getattr(request, 'endpoint', None) or ''
    if ep in _WORKSHOP_CONFIG_EPS:
        return True
    path = request.path or ''
    return path.startswith('/admin/workshop/settings') or path.startswith('/admin/workshop/process-config')


def _in_comunicacion_zone() -> bool:
    if not has_request_context():
        return False
    ep = getattr(request, 'endpoint', None) or ''
    bp = getattr(request, 'blueprint', None) or ''
    if bp == 'integrations':
        return True
    return ep in (
        'admin_chatbots',
        'admin_notifications',
        'office365_admin.admin_office365_requests',
    )


def _resolve_educacion_zone_area_id(ctx: NavContext) -> str | None:
    """Rutas LMS / inscripción académica pertenecen a Educación, no a Ventas."""
    if not has_request_context():
        return None
    path = request.path or ''
    if path.startswith('/admin/academic') or path.startswith('/admin/academic-enrollment'):
        educacion = next((a for a in APP_AREAS if a.id == 'educacion'), None)
        if educacion is not None and _area_visible(educacion, ctx):
            return 'educacion'
    return None


def resolve_module_bar_area_id(ctx: NavContext) -> str | None:
    """Zona de la barra horizontal (prioridad sobre sidebar para pantallas sin app en launcher)."""
    if not has_request_context():
        return None
    ep = getattr(request, 'endpoint', None) or ''
    edu_area = _resolve_educacion_zone_area_id(ctx)
    if edu_area:
        return edu_area
    if ep in _ORG_PLATFORM_EPS and ctx.is_platform_admin and ctx.show_platform_admin_nav:
        return 'plataforma'
    if not ctx.show_tenant_admin_menu:
        return None
    if _in_rbac_zone() and _v_en1_roles_matrix(ctx):
        return 'permisos'
    if _in_security_matrix_zone() and _v_security_matrix(ctx):
        return 'matriz_odoo'
    if _in_config_zone():
        return 'config'
    if _in_contador_zone() and _v_contador(ctx):
        return 'contador'
    if _in_comunicacion_zone() and _v_comunicacion(ctx):
        return 'comunicacion'
    pay_area = _payments_nav_area_id(ctx)
    if pay_area:
        return pay_area
    sales_area = _analytics_sales_nav_area_id(ctx)
    if sales_area:
        return sales_area
    return resolve_active_area_id(ctx)


def resolve_active_area_id(ctx: NavContext) -> str | None:
    if not has_request_context():
        return None
    ep = getattr(request, 'endpoint', None) or ''
    edu_area = _resolve_educacion_zone_area_id(ctx)
    if edu_area:
        return edu_area
    if ep == 'dashboard' and not ctx.show_tenant_admin_menu:
        return None
    if ep in _ORG_PLATFORM_EPS and ctx.is_platform_admin and ctx.show_platform_admin_nav:
        plataforma = next((a for a in APP_AREAS if a.id == 'plataforma'), None)
        if plataforma is not None and _area_visible(plataforma, ctx):
            return 'plataforma'
    pay_area = _payments_nav_area_id(ctx)
    if pay_area:
        return pay_area
    sales_area = _analytics_sales_nav_area_id(ctx)
    if sales_area:
        return sales_area
    for area in APP_AREAS:
        if area.show_in_sidebar and not _area_visible(area, ctx):
            continue
        if not area.show_in_sidebar and area.visible is not None and not area.visible(ctx):
            continue
        if _area_matches_request(area):
            return area.id
    return None


def _area_by_id(area_id: str) -> NavArea | None:
    return next((a for a in APP_AREAS if a.id == area_id), None)


def _serialize_sidebar_area(area: NavArea, ctx: NavContext) -> dict[str, Any]:
    return {
        'id': area.id,
        'label': area.label,
        'icon': area.icon,
        'url': area_default_url(area, ctx),
    }


def visible_sidebar_launcher(
    ctx: NavContext,
    *,
    active_sidebar_area_id: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Top-level: Tienda, Contactos (sin grupo).
    Resto: grupos colapsables Comercial, Operaciones, Finanzas, Inteligencia, Sistema.
    """
    top: list[dict[str, Any]] = []
    for area_id in _SIDEBAR_TOP_LEVEL_AREA_IDS:
        area = _area_by_id(area_id)
        if area is None or not area.show_in_sidebar or not _area_visible(area, ctx):
            continue
        top.append(_serialize_sidebar_area(area, ctx))

    groups: list[dict[str, Any]] = []
    for grp in _SIDEBAR_LAUNCHER_GROUPS:
        children: list[dict[str, Any]] = []
        for area_id in grp.area_ids:
            area = _area_by_id(area_id)
            if area is None or not area.show_in_sidebar or not _area_visible(area, ctx):
                continue
            children.append(_serialize_sidebar_area(area, ctx))
        if not children:
            continue
        open_group = bool(
            active_sidebar_area_id
            and any(c['id'] == active_sidebar_area_id for c in children)
        )
        if not open_group and active_sidebar_area_id is None:
            open_group = True
        groups.append(
            {
                'id': grp.id,
                'label': grp.label,
                'icon': grp.icon,
                'areas': children,
                'open': open_group,
            }
        )
    return top, groups


def visible_areas(ctx: NavContext) -> list[dict[str, Any]]:
    """Lista plana de apps visibles (compatibilidad)."""
    active_id = sidebar_highlight_area_id(resolve_active_area_id(ctx))
    top, groups = visible_sidebar_launcher(ctx, active_sidebar_area_id=active_id)
    flat = list(top)
    for grp in groups:
        flat.extend(grp['areas'])
    return flat


def visible_area_children(area_id: str | None, ctx: NavContext) -> list[dict[str, Any]]:
    if not area_id:
        return []
    area = next((a for a in APP_AREAS if a.id == area_id), None)
    if area is None:
        return []
    if area.visible is not None and not area.visible(ctx):
        return []
    if area.show_in_sidebar:
        if area.id != 'plataforma' and not ctx.show_tenant_admin_menu:
            return []
        if not any(_item_visible(it, ctx) for it in area.items):
            return []
    children: list[dict[str, Any]] = []
    for item in area.items:
        if not _item_visible(item, ctx):
            continue
        children.append(_serialize_bar_child(item, ctx))
    return children


def build_nav_context(
    *,
    nav_can: Callable[[str], bool],
    saas_module_enabled: Callable[[str], bool],
    saas_module_enabled_chain: Callable[..., bool],
    has_view_endpoint: Callable[[str], bool],
    show_academic_admin_nav: bool,
    office365_module_enabled: bool,
    show_platform_admin_nav: bool,
    is_platform_admin: bool,
    is_advisor: bool,
    show_tenant_admin_menu: bool,
) -> NavContext:
    return NavContext(
        nav_can=nav_can,
        saas_module_enabled=saas_module_enabled,
        saas_module_enabled_chain=saas_module_enabled_chain,
        has_view_endpoint=has_view_endpoint,
        show_academic_admin_nav=show_academic_admin_nav,
        office365_module_enabled=office365_module_enabled,
        show_platform_admin_nav=show_platform_admin_nav,
        is_platform_admin=is_platform_admin,
        is_advisor=is_advisor,
        show_tenant_admin_menu=show_tenant_admin_menu,
    )


def sidebar_highlight_area_id(area_id: str | None) -> str | None:
    """Sub-áreas (sin icono en sidebar) resaltan el módulo padre en el launcher."""
    if area_id == 'taller_config':
        return 'taller'
    if area_id == 'ventas_catalog':
        return 'ventas'
    return area_id


def active_area_label(area_id: str | None) -> str | None:
    if not area_id:
        return None
    area = next((a for a in APP_AREAS if a.id == area_id), None)
    return area.label if area else None


def nav_launcher_payload(**kwargs) -> dict[str, Any]:
    try:
        from flask import g, has_request_context

        if has_request_context() and getattr(g, '_nav_launcher_payload_built', False):
            cached = getattr(g, '_nav_launcher_payload_result', None)
            if isinstance(cached, dict):
                return cached
    except Exception:
        pass

    ctx = build_nav_context(**kwargs)
    bar_area_id = resolve_module_bar_area_id(ctx)
    active_id = bar_area_id or resolve_active_area_id(ctx)
    sidebar_area_id = sidebar_highlight_area_id(active_id)
    top_areas, launcher_groups = visible_sidebar_launcher(
        ctx, active_sidebar_area_id=sidebar_area_id
    )
    areas = list(top_areas)
    for grp in launcher_groups:
        areas.extend(grp['areas'])
    if bar_area_id is None and len(areas) == 1:
        bar_area_id = areas[0]['id']
        active_id = bar_area_id
    children = visible_area_children(active_id, ctx)
    active_child_label = _active_child_label(children)
    show_bar = bool(children) and (
        len(children) > 1 or any(c.get('dropdown') for c in children)
    ) and (
        ctx.show_tenant_admin_menu
        or (active_id == 'plataforma' and ctx.show_platform_admin_nav and ctx.is_platform_admin)
    )
    result = {
        'nav_app_areas': areas,
        'nav_sidebar_top_areas': top_areas,
        'nav_sidebar_groups': launcher_groups,
        'nav_active_area_id': active_id,
        'nav_sidebar_area_id': sidebar_area_id,
        'nav_active_area_label': active_area_label(active_id),
        'nav_area_children': children,
        'nav_single_area_mode': len(areas) == 1,
        'nav_show_module_bar': show_bar,
        'nav_active_child_label': active_child_label,
    }
    try:
        from flask import g, has_request_context

        if has_request_context():
            g._nav_launcher_payload_built = True
            g._nav_launcher_payload_result = result
    except Exception:
        pass
    return result
