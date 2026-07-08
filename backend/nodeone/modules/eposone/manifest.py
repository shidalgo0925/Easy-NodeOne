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
    'zone_endpoints': ('eposone.eposone_home',),
    'notes': (
        'App nativa Carril 2 — no importa Membership, Events ni Certificates.',
        'Back office completo (pedidos, cajas, inventario) en Etapa 7.',
    ),
}
