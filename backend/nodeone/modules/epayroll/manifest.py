"""EPayroll — nómina (manifest Etapa 9; implementación en chat dedicado)."""

MODULE = {
    'id': 'epayroll',
    'name': 'EPayroll',
    'saas_codes': ('epayroll',),
    'depends_on': ('contacts',),
    'native_platform': True,
    'lifecycle': 'planned',
    'notes': (
        'Etapa 9 — registrada en manifest_registry; sin rutas ni nav hasta GO de producto.',
        'Dependerá solo del Core (contactos, org, licenciamiento).',
    ),
}
