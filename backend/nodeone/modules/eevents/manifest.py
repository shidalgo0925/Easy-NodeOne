"""EEvents — aplicación de plataforma (integración Etapa 5)."""

MODULE = {
    'id': 'eevents',
    'name': 'EEvents',
    'saas_codes': ('events',),
    'nav_area_id': 'eventos',
    'depends_on': ('contacts',),
    'integration_order': 3,
    'register': 'nodeone.core.features.register_events_blueprints',
    'legacy_modules': (
        'nodeone.modules.events',
        'nodeone.modules.admin_events',
    ),
    'zone_blueprints': ('events', 'admin_events', 'events_api'),
    'zone_endpoints': (
        'admin_events.admin_events_index',
        'admin_events.discounts_index',
        'events.list_events',
    ),
}
