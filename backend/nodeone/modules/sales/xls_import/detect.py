from nodeone.modules.sales.xls_import.profiles import panama_factura_layout_v1 as panama_v1

PROFILES = (panama_v1,)


def list_profiles() -> list[dict]:
    return [
        {
            'code': p.PROFILE_CODE,
            'version': p.PROFILE_VERSION,
            'label': p.PROFILE_LABEL,
        }
        for p in PROFILES
    ]


def parse_grid(filename: str, grid: list, profile_code: str | None = None):
    wanted = (profile_code or '').strip().lower()
    if wanted and wanted not in ('auto', ''):
        for p in PROFILES:
            if p.PROFILE_CODE == wanted:
                data = p.parse(filename, grid)
                return data, p.PROFILE_CODE, p.PROFILE_VERSION
        raise ValueError(f'Perfil de importación desconocido: {profile_code}')
    ranked = sorted(
        ((p.detect_score(filename, grid), p) for p in PROFILES),
        key=lambda x: x[0],
        reverse=True,
    )
    score, chosen = ranked[0]
    if score < 40:
        raise ValueError('No se reconoció el formato del Excel. Use un archivo de factura compatible.')
    return chosen.parse(filename, grid), chosen.PROFILE_CODE, chosen.PROFILE_VERSION
