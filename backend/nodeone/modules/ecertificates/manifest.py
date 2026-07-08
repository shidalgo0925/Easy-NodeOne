"""ECertificates — aplicación de plataforma (integración Etapa 5)."""

MODULE = {
    'id': 'ecertificates',
    'name': 'ECertificates',
    'saas_codes': ('certificates',),
    'nav_area_id': 'certificados',
    'depends_on': ('eevents', 'emembership'),
    'integration_order': 4,
    'register': 'nodeone.modules.certificates.register.register_certificates_blueprints',
    'legacy_modules': (
        'nodeone.modules.certificates',
        'nodeone.modules.admin_certificate_pages',
        'nodeone.modules.certificates_builder',
    ),
    'zone_endpoints': (
        'admin_certificate_events',
        'admin_certificate_templates',
        'admin_certificate_template_editor',
        'admin_certificate_institutional_editor',
    ),
    'zone_blueprints': (
        'certificates_builder',
        'certificates_api',
        'certificates_public',
    ),
    'public_endpoints': (
        '/verify/<code>',
        '/certificates/verify/<code>',
    ),
    'notes': (
        'Requiere EEvents y EMembership en plataforma o en_migracion antes del cutover.',
    ),
}
