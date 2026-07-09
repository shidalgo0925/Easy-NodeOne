"""EPosOne — aplicación nativa de plataforma (Etapa 6)."""

MODULE = {
    'id': 'eposone',
    'name': 'EPosOne',
    'saas_codes': ('eposone',),
    'nav_area_id': 'eposone',
    'depends_on': ('contacts',),
    'native_platform': True,
    'register': 'nodeone.modules.eposone.register.register_eposone_blueprints',
    'zone_blueprints': ('eposone',),
    'zone_path_prefixes': ('/admin/eposone',),
        'zone_endpoints': (
            'eposone.eposone_home',
            'eposone.eposone_section',
        ),
        'nav_provider': 'nodeone.modules.eposone.nav.build_nav_tree',
    'notes': (
        'App nativa Carril 2 — no importa Membership, Events ni Certificates.',
        'Back office POS (Etapa 7): menú en nav_menu área eposone; compone Core (sales, contacts, contador).',
        'Eventos (Etapa 8): publicar vía nodeone.modules.eposone.events — sin sync de tablas.',
    ),
}
