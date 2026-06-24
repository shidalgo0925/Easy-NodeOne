"""Módulo certificados — mapa de responsabilidades."""

MODULE = {
    'id': 'certificates',
    'name': 'Certificates',
    'depends_on': ['events', 'membership'],
    'register': 'nodeone.modules.certificates.register.register_certificates_blueprints',
    'routes': {
        'api': 'nodeone.modules.certificates.api_routes',
        'templates': 'nodeone.modules.certificates.template_routes',
        'builder': 'nodeone.modules.certificates.builder.routes',
        'pages': 'nodeone.modules.admin_certificate_pages.routes',
    },
    'routes_legacy_shims': [
        'certificate_routes',
        'certificate_template_routes',
        'certificates_builder.routes',
    ],
    'services': [
        'nodeone.services.certificate_assets',
        'nodeone.services.certificate_membership_rules',
        'nodeone.services.certificate_render',
        'nodeone.services.certificate_http',
        'nodeone.services.certificate_visual_templates',
        'nodeone.services.certificate_org',
        'nodeone.modules.events.services.certificates',
    ],
    'public_endpoints': [
        '/verify/<code>',
        '/certificates/verify/<code>',
    ],
}
