"""EPayroll — nómina nativa (activada desde manifest Etapa 9)."""

MODULE = {
    'id': 'epayroll',
    'name': 'EPayroll',
    'saas_codes': ('epayroll',),
    'nav_area_id': 'epayroll',
    'depends_on': ('contacts',),
    'native_platform': True,
    'lifecycle': 'active',
    'register': 'nodeone.modules.epayroll.register.register_epayroll_blueprints',
    'zone_blueprints': ('epayroll',),
    'zone_path_prefixes': ('/admin/epayroll',),
    'zone_endpoints': ('epayroll.epayroll_home',),
    'notes': (
        'App nativa Carril 2 — solo Core (contactos, org, licenciamiento).',
        'Scaffold inicial; módulos de planilla y reportes en iteraciones de producto.',
    ),
}
