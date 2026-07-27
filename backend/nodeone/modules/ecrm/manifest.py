"""ECRM — aplicación de plataforma (integración Etapa 5)."""

MODULE = {
    'id': 'ecrm',
    'name': 'ECRM',
    'saas_codes': ('crm', 'crm_contacts'),
    'nav_area_id': 'crm',
    'depends_on': ('contacts',),
    'integration_order': 2,
    'register': (
        'nodeone.core.features.register_admin_crm_routes',
        'nodeone.core.features.register_crm_api_blueprint',
    ),
    'legacy_modules': (
        'nodeone.modules.admin_crm',
        'nodeone.modules.crm_api',
    ),
    'zone_endpoints': (
        'admin_crm_dashboard',
        'admin_crm_kanban',
        'admin_crm_leads',
        'admin_crm_calendar',
        'admin_crm_table',
        'admin_crm_activities',
        'admin_crm_reports',
        'admin_crm_settings',
    ),
}
