"""Motor de recomendación del Asistente de Inicio (ADR-024 §13 / DESIGN §5)."""

from __future__ import annotations

from typing import Any

from nodeone.core.platform.commercial_plans import (
    get_commercial_plan,
    list_commercial_plans,
)

BUSINESS_TYPES: tuple[str, ...] = (
    'Restaurante',
    'Cafetería',
    'Bar',
    'Tienda',
    'Mini súper',
    'Farmacia',
    'Servicios',
    'Otro',
)

# Orientativo — evoluciona sin cambiar la estructura del asistente.
_RECOMMEND_BY_TYPE: dict[str, str] = {
    'Restaurante': 'business',
    'Cafetería': 'business',
    'Bar': 'business',
    'Tienda': 'starter',
    'Mini súper': 'starter',
    'Farmacia': 'starter',
    'Servicios': 'starter',
    'Otro': 'starter',
}

_BLURB: dict[str, str] = {
    'standalone': 'Ideal para un solo punto de venta que opera localmente.',
    'starter': 'Ideal para empezar con control, respaldo y un punto de venta conectado.',
    'business': 'Ideal para cafeterías y restaurantes: hasta 3 puntos de venta y administración desde cualquier lugar.',
    'enterprise': 'Ideal para cadenas y multi-sucursal con operación conectada.',
}


def normalize_business_type(raw: str | None) -> str:
    value = (raw or '').strip()
    if value in BUSINESS_TYPES:
        return value
    return 'Otro'


def _modality_benefit(plan: dict[str, Any]) -> str:
    if (plan.get('modality') or '') == 'local':
        return 'Opera localmente desde un solo punto de venta'
    return 'Administra tu negocio desde cualquier lugar'


def _trial_badge(plan: dict[str, Any]) -> str:
    days = int(plan.get('trial_days') or 0)
    if days > 0:
        return f'{days} días gratis · Sin tarjeta'
    return 'Activación al contratar'


def _activation_label(plan: dict[str, Any]) -> str:
    days = int(plan.get('trial_days') or 0)
    if days > 0:
        return f'Trial de {days} días'
    return 'Activación inmediata'


def _capacity_lines(plan: dict[str, Any]) -> list[str]:
    """Cupos legibles para /start (ADR-028 — sin precio)."""
    limits = plan.get('resource_limits') or {}
    lines: list[str] = []
    pos = limits.get('pos')
    branches = limits.get('branches')
    if pos == -1:
        lines.append('POS ilimitados')
    elif isinstance(pos, int) and pos > 0:
        lines.append('1 POS incluido' if pos == 1 else f'Hasta {pos} POS incluidos')
    if branches == -1:
        lines.append('Sucursales ilimitadas')
    elif isinstance(branches, int) and branches > 0:
        lines.append(
            '1 sucursal incluida' if branches == 1 else f'Hasta {branches} sucursales'
        )
    if (plan.get('modality') or '') != 'local':
        lines.append('Administración central y sincronización')
    else:
        lines.append('Operación local desde un solo punto de venta')
    return lines


def plan_public_view(plan_code: str | None) -> dict[str, Any]:
    plan = get_commercial_plan(plan_code)
    code = plan['code']
    capacity = _capacity_lines(plan)
    return {
        'plan_code': code,
        'plan_name': plan['name'],
        'display_name': f"EPosOne {plan['name']}",
        'modality': plan.get('modality') or 'connected',
        'modality_label': 'EPosOne Standalone' if code == 'standalone' else 'EPosOne conectado',
        'modality_benefit': _modality_benefit(plan),
        # ADR-028: catálogo interno conserva precio; /start no lo expone.
        'capacity_lines': capacity,
        'includes_summary': ' · '.join(capacity),
        'trial_days': int(plan.get('trial_days') or 0),
        'trial_badge': _trial_badge(plan),
        'activation_label': _activation_label(plan),
        'blurb': _BLURB.get(code, plan.get('description') or ''),
        'eyebrow': plan.get('eyebrow') or '',
        'select_cta': 'Seleccionar este plan',
    }


def recommend_for_business_type(business_type: str | None) -> dict[str, Any]:
    btype = normalize_business_type(business_type)
    plan_code = _RECOMMEND_BY_TYPE.get(btype, 'starter')
    view = plan_public_view(plan_code)
    if btype in ('Restaurante', 'Bar', 'Mini súper', 'Servicios', 'Otro'):
        article = 'un'
    else:
        article = 'una'
    return {
        'business_type': btype,
        'recommended': True,
        'headline': f'Para {article} {btype.lower()} como la tuya recomendamos {view["display_name"]}.',
        **view,
    }


def other_plan_options(*, exclude_plan: str | None = None) -> list[dict[str, Any]]:
    skip = (exclude_plan or '').strip().lower()
    out: list[dict[str, Any]] = []
    for plan in list_commercial_plans():
        view = plan_public_view(plan['code'])
        view['recommended'] = view['plan_code'] == skip
        out.append(view)
    return out


def catalog_payload(business_type: str | None = None) -> dict[str, Any]:
    btype = normalize_business_type(business_type) if business_type else None
    reco = recommend_for_business_type(btype) if btype else None
    return {
        'business_types': list(BUSINESS_TYPES),
        'recommendation': reco,
        'plans': other_plan_options(exclude_plan=(reco or {}).get('plan_code')),
    }
