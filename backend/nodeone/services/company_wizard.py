"""Helpers compartidos — wizard único de empresa (tenant + plataforma)."""

from __future__ import annotations

IDENTITY_PRESETS: dict[str, dict[str, str]] = {
    'iius': {'primary_color': '#8B60AA', 'primary_color_dark': '#00042D', 'accent_color': '#E6BF75'},
    'en1': {'primary_color': '#FF6B35', 'primary_color_dark': '#2D3E50', 'accent_color': '#9CA3AF'},
    'hubspot': {'primary_color': '#FF6B35', 'primary_color_dark': '#2D3E50', 'accent_color': '#9CA3AF'},
    'azul': {'primary_color': '#2563EB', 'primary_color_dark': '#1E3A8A', 'accent_color': '#06B6D4'},
    'verde': {'primary_color': '#059669', 'primary_color_dark': '#047857', 'accent_color': '#10B981'},
    'rojo': {'primary_color': '#DC2626', 'primary_color_dark': '#B91C1C', 'accent_color': '#EF4444'},
    'violeta': {'primary_color': '#7C3AED', 'primary_color_dark': '#5B21B6', 'accent_color': '#A78BFA'},
    'indigo': {'primary_color': '#4F46E5', 'primary_color_dark': '#3730A3', 'accent_color': '#818CF8'},
    'teal': {'primary_color': '#0D9488', 'primary_color_dark': '#0F766E', 'accent_color': '#2DD4BF'},
    'cyan': {'primary_color': '#0891B2', 'primary_color_dark': '#0E7490', 'accent_color': '#22D3EE'},
    'naranja': {'primary_color': '#EA580C', 'primary_color_dark': '#C2410C', 'accent_color': '#FB923C'},
    'ambar': {'primary_color': '#D97706', 'primary_color_dark': '#B45309', 'accent_color': '#FBBF24'},
    'rosa': {'primary_color': '#DB2777', 'primary_color_dark': '#BE185D', 'accent_color': '#F472B6'},
    'slate': {'primary_color': '#475569', 'primary_color_dark': '#334155', 'accent_color': '#94A3B8'},
    'esmeralda': {'primary_color': '#10B981', 'primary_color_dark': '#059669', 'accent_color': '#34D399'},
    'coral': {'primary_color': '#E11D48', 'primary_color_dark': '#BE123C', 'accent_color': '#FB7185'},
}

WIZARD_STEP_SLUGS: dict[str, int] = {
    'empresa': 1,
    'fiscal': 2,
    'branding': 3,
    'acceso': 4,
}


def validate_hex_color(value: str | None) -> bool:
    if not value or not isinstance(value, str):
        return False
    v = value.strip()
    return len(v) == 7 and v[0] == '#' and all(c in '0123456789AaBbCcDdEeFf' for c in v[1:])


def identity_settings_dict(organization_id: int) -> dict:
    from models.saas import OrganizationSettings

    row = OrganizationSettings.query.filter_by(organization_id=int(organization_id)).first()
    if row is None:
        return {
            'preset': 'azul',
            'primary_color': '#2563EB',
            'primary_color_dark': '#1E3A8A',
            'accent_color': '#06B6D4',
        }
    return row.to_dict()


def save_identity_from_form(form, organization_id: int) -> str | None:
    """Persiste branding desde campos identity_* del formulario. Devuelve error o None."""
    from models.saas import OrganizationSettings

    preset = (form.get('identity_preset') or 'azul').strip().lower()
    row = OrganizationSettings.query.filter_by(organization_id=int(organization_id)).first()
    if row is None:
        row = OrganizationSettings(organization_id=int(organization_id))
        from app import db

        db.session.add(row)

    if preset in IDENTITY_PRESETS:
        p = IDENTITY_PRESETS[preset]
        row.primary_color = p['primary_color']
        row.primary_color_dark = p['primary_color_dark']
        row.accent_color = p['accent_color']
        row.preset = preset
        return None
    if preset == 'custom':
        primary = (form.get('identity_primary_color') or '').strip()
        primary_dark = (form.get('identity_primary_color_dark') or '').strip()
        accent = (form.get('identity_accent_color') or '').strip()
        if not all((validate_hex_color(primary), validate_hex_color(primary_dark), validate_hex_color(accent))):
            return 'Colores personalizados deben ser HEX válidos (#RRGGBB).'
        row.primary_color = primary
        row.primary_color_dark = primary_dark
        row.accent_color = accent
        row.preset = 'custom'
        return None
    return 'Preset de identidad no válido.'


def resolve_initial_wizard_step(*, mode: str, step_arg: str | None) -> int:
    slug = (step_arg or '').strip().lower()
    if slug in WIZARD_STEP_SLUGS:
        n = WIZARD_STEP_SLUGS[slug]
        if mode == 'tenant' and n == 4:
            return 3
        return n
    try:
        n = int(slug)
        if mode == 'tenant' and n == 4:
            return 3
        if 1 <= n <= 4:
            return n
    except (TypeError, ValueError):
        pass
    return 1


def fiscal_payload_from_form(form) -> dict:
    return {
        'legal_name': (form.get('legal_name') or '').strip() or None,
        'tax_id': (form.get('tax_id') or '').strip() or None,
        'tax_regime': (form.get('tax_regime') or '').strip() or None,
        'fiscal_address': (form.get('fiscal_address') or '').strip() or None,
        'fiscal_city': (form.get('fiscal_city') or '').strip() or None,
        'fiscal_state': (form.get('fiscal_state') or '').strip() or None,
        'fiscal_country': (form.get('fiscal_country') or '').strip() or None,
        'fiscal_phone': (form.get('fiscal_phone') or '').strip() or None,
        'fiscal_email': (form.get('fiscal_email') or '').strip() or None,
    }
