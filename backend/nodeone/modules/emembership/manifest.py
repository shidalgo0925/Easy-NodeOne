"""EMembership — aplicación de plataforma (integración Etapa 5)."""

MODULE = {
    'id': 'emembership',
    'name': 'EMembership',
    'saas_codes': ('memberships',),
    'nav_area_id': 'membresias',
    'depends_on': (),
    'integration_order': 1,
    'register': 'nodeone.core.features.register_admin_dashboard_memberships_routes',
    'legacy_modules': (
        '_app.modules.members',
        'nodeone.modules.admin_dashboard_memberships',
        'nodeone.modules.public_membership',
    ),
    'zone_endpoints': (
        'admin_plans',
        'admin_memberships',
        'admin_benefits',
        'admin_dashboard',
        'benefits',
    ),
}
