"""EAppointments — aplicación de plataforma (integración Etapa 5)."""

MODULE = {
    'id': 'eappointments',
    'name': 'EAppointments',
    'saas_codes': ('appointments',),
    'nav_area_id': 'agenda',
    'depends_on': (),
    'integration_order': 5,
    'register': (
        'nodeone.core.features.register_appointments_blueprints',
        'nodeone.core.features.register_ecalendar_blueprint',
        'nodeone.core.features.register_ecalendar_admin_routes',
    ),
    'legacy_modules': (
        'nodeone.modules.appointments',
        'nodeone.modules.ecalendar',
    ),
    'zone_blueprints': ('appointments', 'admin_appointments', 'ecalendar'),
    'zone_endpoints': (
        'appointments.appointments_home',
        'appointments.advisor_queue',
        'admin_appointments.admin_appointments_dashboard',
        'admin_appointments.calendar_view',
        'admin_ecalendar_settings_page',
        'admin_ecalendar_appointments_page',
    ),
}
