"""Menú admin tenant — áreas (app launcher) + ítems por área.

La app activa se infiere de URL/endpoint; sin sesión ni BD.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from flask import has_request_context, request, url_for


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
    'admin_organizations_list',
    'admin_organization_new',
    'admin_organization_edit',
)

_PLATFORM_EPS = (
    'admin_organizations_list',
    'admin_organization_new',
    'admin_organization_edit',
    'admin_saas_modules_page',
    'admin_saas_catalog_list',
    'admin_saas_catalog_new',
    'admin_saas_catalog_edit',
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


def _v_contacts(ctx: NavContext) -> bool:
    return ctx.saas_module_enabled('contacts') and ctx.has_view_endpoint('contacts_admin.contacts_index')


def _v_crm(ctx: NavContext) -> bool:
    return (ctx.saas_module_enabled('crm_contacts') or ctx.saas_module_enabled('crm')) and ctx.nav_can('users.view')


def _v_servicios(ctx: NavContext) -> bool:
    return ctx.saas_module_enabled('appointments')


def _v_ventas(ctx: NavContext) -> bool:
    return ctx.nav_can('payments.view') and ctx.saas_module_enabled('sales')


def _v_comercial(ctx: NavContext) -> bool:
    return _v_contacts(ctx) or _v_crm(ctx) or _v_servicios(ctx) or _v_ventas(ctx)


def _v_analitica(ctx: NavContext) -> bool:
    return ctx.saas_module_enabled('analytics') and ctx.nav_can('analytics.view')


def _v_educacion(ctx: NavContext) -> bool:
    return ctx.show_academic_admin_nav


def _v_membresias(ctx: NavContext) -> bool:
    return ctx.nav_can('memberships.view')


def _v_eventos(ctx: NavContext) -> bool:
    return ctx.saas_module_enabled('events') and ctx.nav_can('reports.view')


def _v_taller(ctx: NavContext) -> bool:
    return ctx.saas_module_enabled('workshop')


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


def _v_operaciones(ctx: NavContext) -> bool:
    return _v_taller(ctx) or _v_contador(ctx) or _v_agenda(ctx) or _v_comunicacion(ctx)


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


def _v_finanzas(ctx: NavContext) -> bool:
    return _v_facturas(ctx) or _v_pagos(ctx) or _v_contabilidad(ctx) or _v_fe(ctx)


def _v_config(ctx: NavContext) -> bool:
    return ctx.nav_can('system.settings.view')


def _v_plataforma(ctx: NavContext) -> bool:
    return ctx.show_platform_admin_nav and ctx.is_platform_admin


def _comunicacion_url(ctx: NavContext) -> str:
    if ctx.saas_module_enabled('communications') and ctx.office365_module_enabled:
        return url_for('integrations.office365_page')
    if ctx.saas_module_enabled('marketing_email'):
        return url_for('admin_marketing')
    return url_for('admin_notifications')


def _v_logs(ctx: NavContext) -> bool:
    return ctx.nav_can('reports.view')


def _v_backup(ctx: NavContext) -> bool:
    return ctx.nav_can('system.settings.view')


def _v_sistema(ctx: NavContext) -> bool:
    return _v_logs(ctx) or _v_backup(ctx)


def _v_security_matrix(ctx: NavContext) -> bool:
    return (
        ctx.saas_module_enabled('security_matrix')
        and ctx.has_view_endpoint('security_matrix.security_matrix_index')
        and ctx.nav_can('security_matrix.admin')
    )


def _v_en1_roles_matrix(ctx: NavContext) -> bool:
    return ctx.nav_can('roles.view') and ctx.has_view_endpoint('admin_roles_matrix')


def _v_administracion(ctx: NavContext) -> bool:
    return _v_security_matrix(ctx) or _v_en1_roles_matrix(ctx)


APP_AREAS: tuple[NavArea, ...] = (
    NavArea(
        id='analitica',
        label='Analítica',
        icon='fas fa-chart-line',
        visible=_v_analitica,
        zone_endpoints=(
            'admin_analytics',
            'admin_analytics_sales',
            'admin_analytics_crm',
            'admin_analytics_members',
            'admin_analytics_registrations',
        ),
        items=(
            NavAreaItem(
                'ejecutivo',
                'Ejecutivo',
                'fas fa-chart-pie',
                'admin_analytics',
                active_endpoints=('admin_analytics',),
            ),
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
        ),
    ),
    NavArea(
        id='comercial',
        label='Comercial',
        icon='fas fa-briefcase',
        visible=_v_comercial,
        zone_endpoints=_CRM_EPS
        + ('admin_sales_quotations', 'contacts_admin.contacts_index', 'contacts_admin.contacts_new'),
        zone_blueprints=('contacts_admin', 'services'),
        zone_path_prefixes=('/admin/contacts', '/admin/sales'),
        items=(
            NavAreaItem(
                'contactos',
                'Contactos',
                'fas fa-address-book',
                'contacts_admin.contacts_index',
                visible=_v_contacts,
                active_blueprints=('contacts_admin',),
                active_path_prefixes=('/admin/contacts',),
            ),
            NavAreaItem(
                'crm',
                'CRM',
                'fas fa-handshake',
                'admin_crm_dashboard',
                visible=_v_crm,
                active_endpoints=_CRM_EPS,
            ),
            NavAreaItem(
                'servicios',
                'Servicios',
                'fas fa-th-large',
                'services.list',
                visible=_v_servicios,
                active_blueprints=('services',),
            ),
            NavAreaItem(
                'ventas',
                'Ventas',
                'fas fa-file-invoice-dollar',
                'admin_sales_quotations',
                url_path='/admin/sales/quotations',
                visible=_v_ventas,
                active_endpoints=('admin_sales_quotations',),
            ),
        ),
    ),
    NavArea(
        id='educacion',
        label='Educación',
        icon='fas fa-graduation-cap',
        visible=_v_educacion,
        zone_blueprints=('academic_admin', 'academic_enrollment_admin'),
        zone_endpoints=(
            'admin_certificate_events',
            'admin_certificate_templates',
            'admin_certificate_template_editor',
        ),
        items=(
            NavAreaItem(
                'programas',
                'Programas',
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
                'inscripciones',
                'Inscripciones',
                'fas fa-file-signature',
                'academic_admin.admin_academic_enrollments',
                active_endpoints=('academic_admin.admin_academic_enrollments',),
            ),
            NavAreaItem(
                'certificados',
                'Certificados',
                'fas fa-certificate',
                'admin_certificate_events',
                visible=lambda c: c.saas_module_enabled('certificates'),
                active_endpoints=(
                    'admin_certificate_events',
                    'admin_certificate_templates',
                    'admin_certificate_template_editor',
                ),
            ),
        ),
    ),
    NavArea(
        id='membresias',
        label='Membresías',
        icon='fas fa-crown',
        visible=_v_membresias,
        zone_endpoints=('admin_plans', 'admin_memberships', 'admin_benefits', 'benefits'),
        items=(
            NavAreaItem(
                'miembros',
                'Miembros',
                'fas fa-users',
                'admin_memberships',
                active_endpoints=('admin_memberships',),
            ),
            NavAreaItem(
                'beneficios',
                'Beneficios',
                'fas fa-gift',
                'admin_benefits',
                active_endpoints=('admin_benefits', 'benefits'),
            ),
            NavAreaItem(
                'planes',
                'Planes',
                'fas fa-layer-group',
                'admin_plans',
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
            NavAreaItem(
                'gestion_eventos',
                'Gestión',
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
        ),
    ),
    NavArea(
        id='operaciones',
        label='Operaciones',
        icon='fas fa-cogs',
        visible=_v_operaciones,
        zone_blueprints=('contador', 'contador_api', 'appointments', 'admin_appointments', 'integrations'),
        zone_path_prefixes=('/admin/contador', '/api/contador', '/admin/workshop'),
        zone_endpoints=(
            'admin_workshop_orders',
            'admin_workshop_order_new',
            'admin_workshop_order_detail',
            'admin_workshop_process_config',
            'admin_marketing',
            'admin_chatbots',
            'admin_notifications',
            'office365_admin.admin_office365_requests',
            'appointments.advisor_queue',
        ),
        items=(
            NavAreaItem(
                'taller',
                'Taller',
                'fas fa-car-side',
                'admin_workshop_orders',
                visible=_v_taller,
                active_endpoints=(
                    'admin_workshop_orders',
                    'admin_workshop_order_new',
                    'admin_workshop_order_detail',
                    'admin_workshop_process_config',
                ),
            ),
            NavAreaItem(
                'contador',
                'Contador',
                'fas fa-clipboard-list',
                'contador.contador_index',
                visible=_v_contador,
                active_blueprints=('contador', 'contador_api'),
                active_path_prefixes=('/admin/contador', '/api/contador'),
            ),
            NavAreaItem(
                'agenda',
                'Agenda',
                'fas fa-calendar-alt',
                'appointments.appointments_home',
                visible=_v_agenda,
                active_blueprints=('appointments', 'admin_appointments'),
                active_endpoints=('appointments.advisor_queue',),
            ),
            NavAreaItem(
                'comunicacion',
                'Comunicación',
                'fas fa-comments',
                'admin_notifications',
                url_resolver=_comunicacion_url,
                visible=_v_comunicacion,
                active_endpoints=(
                    'admin_marketing',
                    'admin_chatbots',
                    'admin_notifications',
                    'office365_admin.admin_office365_requests',
                ),
                active_blueprints=('integrations',),
            ),
        ),
    ),
    NavArea(
        id='finanzas',
        label='Finanzas',
        icon='fas fa-coins',
        visible=_v_finanzas,
        zone_blueprints=('payments_admin', 'efactura_admin', 'efactura_api', 'accounting_core'),
        zone_path_prefixes=('/admin/payments', '/admin/accounting/invoices', '/admin/efactura', '/api/admin/efactura'),
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
                'pagos',
                'Pagos',
                'fas fa-credit-card',
                'payments_admin.admin_payments',
                visible=_v_pagos,
                active_blueprints=('payments_admin',),
                active_path_prefixes=('/admin/payments',),
            ),
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
                'Facturación Electrónica',
                'fas fa-receipt',
                'efactura_admin.efactura_emissions',
                visible=_v_fe,
                active_blueprints=('efactura_admin', 'efactura_api'),
                active_path_prefixes=('/admin/efactura', '/api/admin/efactura'),
            ),
        ),
    ),
    NavArea(
        id='administracion',
        label='Administración',
        icon='fas fa-shield-alt',
        visible=_v_administracion,
        zone_blueprints=('security_matrix',),
        zone_path_prefixes=('/admin/security-matrix',),
        zone_endpoints=('admin_roles_matrix', 'admin_roles_matrix_cell'),
        items=(
            NavAreaItem(
                'matriz_odoo',
                'Matriz Odoo',
                'fas fa-table',
                'security_matrix.security_matrix_index',
                visible=_v_security_matrix,
                active_blueprints=('security_matrix',),
                active_path_prefixes=('/admin/security-matrix',),
            ),
            NavAreaItem(
                'permisologia_en1',
                'Permisología EN1',
                'fas fa-th',
                'admin_roles_matrix',
                visible=_v_en1_roles_matrix,
                active_endpoints=('admin_roles_matrix', 'admin_roles_matrix_cell'),
                active_path_prefixes=('/admin/roles/matrix',),
            ),
        ),
    ),
    NavArea(
        id='configuracion',
        label='Configuración',
        icon='fas fa-cog',
        visible=_v_config,
        show_in_sidebar=False,
        zone_endpoints=_CONFIG_EPS,
        items=(
            NavAreaItem(
                'branding',
                'Branding',
                'fas fa-palette',
                'admin_identity',
                active_endpoints=('admin_identity',),
            ),
            NavAreaItem(
                'email',
                'Email / SMTP',
                'fas fa-envelope',
                'admin_email',
                active_endpoints=('admin_email',),
            ),
            NavAreaItem(
                'usuarios',
                'Usuarios',
                'fas fa-users-cog',
                'admin_users',
                visible=lambda c: c.nav_can('users.view'),
                active_endpoints=('admin_users',),
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
            NavAreaItem(
                'empresas',
                'Empresas',
                'fas fa-building',
                'admin_organizations_list',
                active_endpoints=('admin_organizations_list', 'admin_organization_new', 'admin_organization_edit'),
            ),
            NavAreaItem(
                'modulos',
                'Módulos',
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
        ),
    ),
    NavArea(
        id='sistema',
        label='Sistema',
        icon='fas fa-server',
        visible=_v_sistema,
        zone_endpoints=('admin_messaging', 'admin_messaging_detail', 'admin_backup.admin_backup'),
        items=(
            NavAreaItem(
                'logs',
                'Logs',
                'fas fa-stream',
                'admin_messaging',
                visible=_v_logs,
                active_endpoints=('admin_messaging', 'admin_messaging_detail'),
            ),
            NavAreaItem(
                'respaldos',
                'Respaldos',
                'fas fa-database',
                'admin_backup.admin_backup',
                visible=_v_backup,
                active_endpoints=('admin_backup.admin_backup',),
            ),
        ),
    ),
)


def _item_visible(item: NavAreaItem, ctx: NavContext) -> bool:
    if item.visible is not None and not item.visible(ctx):
        return False
    if item.url_path:
        return True
    return ctx.has_view_endpoint(item.endpoint)


def _area_visible(area: NavArea, ctx: NavContext) -> bool:
    if area.id != 'plataforma' and not ctx.show_tenant_admin_menu:
        return False
    if area.visible is not None and not area.visible(ctx):
        return False
    return any(_item_visible(it, ctx) for it in area.items)


def item_url(item: NavAreaItem, ctx: NavContext | None = None) -> str:
    if item.url_resolver is not None and ctx is not None:
        return item.url_resolver(ctx)
    if item.url_path:
        return item.url_path
    return url_for(item.endpoint)


def area_default_url(area: NavArea, ctx: NavContext) -> str:
    for it in area.items:
        if _item_visible(it, ctx):
            return item_url(it, ctx)
    return url_for('dashboard')


def _endpoint_active(item: NavAreaItem) -> bool:
    if not has_request_context():
        return False
    ep = getattr(request, 'endpoint', None) or ''
    bp = getattr(request, 'blueprint', None) or ''
    path = (request.path or '') if request else ''
    if item.active_endpoints and ep in item.active_endpoints:
        return True
    if item.active_blueprints and bp in item.active_blueprints:
        if item.id == 'gestion_eventos' and ep == 'admin_events.discounts_index':
            return False
        return True
    for prefix in item.active_path_prefixes:
        if path.startswith(prefix):
            return True
    if ep == item.endpoint:
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


_ORG_PLATFORM_EPS = (
    'admin_organizations_list',
    'admin_organization_new',
    'admin_organization_edit',
)


def resolve_active_area_id(ctx: NavContext) -> str | None:
    if not has_request_context():
        return None
    ep = getattr(request, 'endpoint', None) or ''
    if ep == 'dashboard':
        return None
    if ep in _ORG_PLATFORM_EPS and ctx.is_platform_admin and ctx.show_platform_admin_nav:
        plataforma = next((a for a in APP_AREAS if a.id == 'plataforma'), None)
        if plataforma is not None and _area_visible(plataforma, ctx):
            return 'plataforma'
    for area in APP_AREAS:
        if not _area_visible(area, ctx):
            continue
        if _area_matches_request(area):
            return area.id
    return None


def visible_areas(ctx: NavContext) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for area in APP_AREAS:
        if not area.show_in_sidebar:
            continue
        if not _area_visible(area, ctx):
            continue
        out.append(
            {
                'id': area.id,
                'label': area.label,
                'icon': area.icon,
                'url': area_default_url(area, ctx),
            }
        )
    return out


def visible_area_children(area_id: str | None, ctx: NavContext) -> list[dict[str, Any]]:
    if not area_id:
        return []
    area = next((a for a in APP_AREAS if a.id == area_id), None)
    if area is None or not _area_visible(area, ctx):
        return []
    children: list[dict[str, Any]] = []
    for item in area.items:
        if not _item_visible(item, ctx):
            continue
        children.append(
            {
                'id': item.id,
                'label': item.label,
                'icon': item.icon,
                'url': item_url(item, ctx),
                'active': _endpoint_active(item),
            }
        )
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


def active_area_label(area_id: str | None) -> str | None:
    if not area_id:
        return None
    area = next((a for a in APP_AREAS if a.id == area_id), None)
    return area.label if area else None


def nav_launcher_payload(**kwargs) -> dict[str, Any]:
    ctx = build_nav_context(**kwargs)
    areas = visible_areas(ctx)
    active_id = resolve_active_area_id(ctx)
    if len(areas) == 1 and active_id is None:
        active_id = areas[0]['id']
    children = visible_area_children(active_id, ctx)
    return {
        'nav_app_areas': areas,
        'nav_active_area_id': active_id,
        'nav_active_area_label': active_area_label(active_id),
        'nav_area_children': children,
        'nav_single_area_mode': len(areas) == 1,
    }
