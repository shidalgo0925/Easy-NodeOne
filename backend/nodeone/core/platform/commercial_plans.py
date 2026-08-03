"""Motor comercial EPosOne — fuente única de planes, precios, features y límites.

Consumido por:
- EntitlementService / entitlement_plans (límites + features de licencia)
- Navegación (disponible / bloqueado / próximamente)
- Pantalla Mi Plan + mensajes de upgrade
- Landing (puede mapear precios/nombres desde aquí)

Regla UX: no ocultar capacidades del producto — mostrar, explicar, invitar al upgrade.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

FeatureNavState = Literal['available', 'locked', 'coming_soon']

# Catálogo de capacidades (qué existe en el producto)
FEATURE_CATALOG: dict[str, dict[str, Any]] = {
    'inventory': {
        'label': 'Inventario',
        'description': 'Stock y movimientos vinculados al POS.',
        'default_state': 'available',
    },
    'customers': {
        'label': 'Clientes',
        'description': 'Clientes POS, fiscal y consumidor final.',
        'default_state': 'available',
    },
    'open_tickets': {
        'label': 'Tickets abiertos',
        'description': 'Pedidos abiertos y flujo de caja.',
        'default_state': 'available',
    },
    'multi_payment': {
        'label': 'Pago mixto',
        'description': 'Varias formas de pago en un mismo cobro.',
        'default_state': 'available',
    },
    'offline': {
        'label': 'Modo offline',
        'description': 'Operación sin Internet con sincronización a EN1.',
        'default_state': 'available',
    },
    'fiscal': {
        'label': 'Fiscal / impuestos',
        'description': 'Configuración avanzada de impuestos y fiscal.',
        'default_state': 'available',
    },
    'kds': {
        'label': 'Kitchen Display (KDS)',
        'description': 'Pantalla de cocina y tickets de preparación.',
        'default_state': 'available',
    },
    'delivery': {
        'label': 'Delivery',
        'description': 'Repartidores, rutas y estado de entrega.',
        'default_state': 'available',
    },
    'promotions': {
        'label': 'Promociones',
        'description': 'Descuentos, combos y reglas comerciales.',
        'default_state': 'available',
    },
    'multi_branch': {
        'label': 'Multi sucursal',
        'description': 'Varias sucursales bajo la misma organización.',
        'default_state': 'available',
    },
    'advanced_reports': {
        'label': 'Reportes avanzados',
        'description': 'Analítica operativa más allá del reporte básico.',
        'default_state': 'available',
    },
    'api': {
        'label': 'API e integraciones',
        'description': 'Acceso API para integraciones externas.',
        'default_state': 'available',
    },
    'analytics': {
        'label': 'Analytics',
        'description': 'Tableros analíticos avanzados.',
        'default_state': 'coming_soon',
    },
    'loyalty': {
        'label': 'Loyalty',
        'description': 'Programas de fidelización.',
        'default_state': 'coming_soon',
    },
    'gift_cards': {
        'label': 'Gift cards',
        'description': 'Tarjetas de regalo y crédito de cliente.',
        'default_state': 'coming_soon',
    },
}

# Planes comerciales oficiales (landing + licencia)
# standalone = modalidad local (sin trial automático); starter/business/enterprise = conectados
_PLAN_ORDER = ('standalone', 'starter', 'business', 'enterprise')

_COMMERCIAL_PLANS: dict[str, dict[str, Any]] = {
    'standalone': {
        'code': 'standalone',
        'name': 'Standalone',
        'description': (
            'Modalidad local para pequeños comercios con un solo punto de venta. '
            'Activación al contratar · Sin prueba automática.'
        ),
        'eyebrow': 'Modalidad local',
        'price_monthly': 15.00,
        'price_annual': 150.00,
        'currency': 'USD',
        'status': 'active',
        'modality': 'local',
        'trial_days': 0,
        'resource_limits': {
            'branches': 1,
            'pos': 1,
            'registers': 1,
            'tablets': 1,
            'cashiers': 2,
            'products': 500,
            'customers': 500,
        },
        'features': {
            'inventory': True,
            'customers': True,
            'open_tickets': True,
            'multi_payment': True,
            'offline': True,
            'fiscal': False,
            'kds': False,
            'delivery': False,
            'promotions': False,
            'multi_branch': False,
            'advanced_reports': False,
            'api': False,
            'cloud_backup': False,
            'web_admin': False,
            'dashboard': 'basic',
        },
    },
    'starter': {
        'code': 'starter',
        'name': 'Starter',
        'description': (
            'Para emprendedores y pequeños comercios que desean empezar con control y respaldo.'
        ),
        'eyebrow': 'Modalidad conectada',
        'price_monthly': 29.95,
        'price_annual': 299.50,
        'currency': 'USD',
        'status': 'active',
        'modality': 'connected',
        'trial_days': 15,
        'resource_limits': {
            'branches': 1,
            'pos': 1,
            'registers': 1,
            'tablets': 1,
            'cashiers': 2,
            'products': 500,
            'customers': 500,
        },
        'features': {
            'inventory': True,
            'customers': True,
            'open_tickets': True,
            'multi_payment': True,
            'offline': True,
            'fiscal': True,
            'kds': False,
            'delivery': False,
            'promotions': False,
            'multi_branch': False,
            'advanced_reports': False,
            'api': False,
            'cloud_backup': True,
            'web_admin': True,
            'dashboard': 'basic',
        },
    },
    'business': {
        'code': 'business',
        'name': 'Business',
        'description': 'Para restaurantes, cafeterías y comercios en crecimiento.',
        'eyebrow': 'Más elegido · Conectada',
        'price_monthly': 39.95,
        'price_annual': 399.50,
        'currency': 'USD',
        'status': 'active',
        'featured': True,
        'modality': 'connected',
        'trial_days': 15,
        'resource_limits': {
            'branches': 1,
            'pos': 3,
            'registers': 3,
            'tablets': 3,
            'cashiers': 20,
            'products': 5000,
            'customers': 5000,
        },
        'features': {
            'inventory': True,
            'customers': True,
            'open_tickets': True,
            'multi_payment': True,
            'offline': True,
            'fiscal': True,
            'kds': True,
            'delivery': True,
            'promotions': True,
            'multi_branch': False,
            'advanced_reports': True,
            'api': False,
            'cloud_backup': True,
            'web_admin': True,
            'dashboard': 'full',
        },
    },
    'enterprise': {
        'code': 'enterprise',
        'name': 'Enterprise',
        'description': 'Para empresas con múltiples sucursales o necesidades avanzadas.',
        'eyebrow': 'Multi-sucursal · Conectada',
        'price_monthly': 79.95,
        'price_annual': 799.50,
        'currency': 'USD',
        'status': 'active',
        'modality': 'connected',
        'trial_days': 15,
        'resource_limits': {
            'branches': -1,
            'pos': -1,
            'registers': -1,
            'tablets': -1,
            'cashiers': -1,
            'products': -1,
            'customers': -1,
        },
        'features': {
            'inventory': True,
            'customers': True,
            'open_tickets': True,
            'multi_payment': True,
            'offline': True,
            'fiscal': True,
            'kds': True,
            'delivery': True,
            'promotions': True,
            'multi_branch': True,
            'advanced_reports': True,
            'api': True,
            'cloud_backup': True,
            'web_admin': True,
            'dashboard': 'full',
        },
    },
}

# Alias históricos → plan comercial
_PLAN_ALIASES = {
    'professional': 'business',
    'pro': 'business',
    'trial': 'starter',
}


def normalize_commercial_plan_code(plan_code: str | None) -> str:
    code = (plan_code or 'starter').strip().lower() or 'starter'
    return _PLAN_ALIASES.get(code, code)


def list_commercial_plan_codes() -> list[str]:
    return list(_PLAN_ORDER)


def get_commercial_plan(plan_code: str | None) -> dict[str, Any]:
    code = normalize_commercial_plan_code(plan_code)
    plan = _COMMERCIAL_PLANS.get(code) or _COMMERCIAL_PLANS['starter']
    return deepcopy(plan)


def list_commercial_plans() -> list[dict[str, Any]]:
    return [get_commercial_plan(c) for c in _PLAN_ORDER]


def format_price(amount: float, currency: str = 'USD') -> str:
    return f'{currency} {amount:.2f}'


def entitlement_template_from_commercial(plan_code: str | None) -> dict[str, Any]:
    """Shape esperado por EntitlementService / get_plan_template."""
    plan = get_commercial_plan(plan_code)
    return {
        'resource_limits': deepcopy(plan.get('resource_limits') or {}),
        'features': deepcopy(plan.get('features') or {}),
    }


def plans_that_include_feature(feature: str) -> list[str]:
    feat = (feature or '').strip().lower()
    result: list[str] = []
    for code in _PLAN_ORDER:
        if (_COMMERCIAL_PLANS[code].get('features') or {}).get(feat) is True:
            result.append(code)
    return result


def feature_nav_state_for_plan(plan_code: str | None, feature: str) -> FeatureNavState:
    """Estado de una feature respecto a un plan (sin mirar BD)."""
    feat = (feature or '').strip().lower()
    meta = FEATURE_CATALOG.get(feat) or {}
    if meta.get('default_state') == 'coming_soon':
        return 'coming_soon'
    plan = get_commercial_plan(plan_code)
    val = (plan.get('features') or {}).get(feat)
    if val is True:
        return 'available'
    if isinstance(val, str) and val and val not in ('basic', 'none', 'no'):
        return 'available'
    return 'locked'



def cheapest_plan_with_feature(feature: str) -> dict[str, Any] | None:
    for code in plans_that_include_feature(feature):
        return get_commercial_plan(code)
    return None


def upgrade_message(
    *,
    current_plan_code: str | None,
    feature: str,
) -> dict[str, Any]:
    """Copy comercial para ítem bloqueado / pantalla de upgrade."""
    feat = (feature or '').strip().lower()
    meta = FEATURE_CATALOG.get(feat) or {'label': feat, 'description': ''}
    current = get_commercial_plan(current_plan_code)
    target = cheapest_plan_with_feature(feat)
    state = feature_nav_state_for_plan(current_plan_code, feat)
    if state == 'coming_soon':
        return {
            'state': 'coming_soon',
            'feature': feat,
            'feature_label': meta.get('label') or feat,
            'title': f'{meta.get("label") or feat} — Próximamente',
            'body': meta.get('description') or 'Esta capacidad estará disponible en una próxima versión.',
            'current_plan': current,
            'target_plan': None,
            'cta_primary': None,
            'cta_secondary_label': 'Ver mi plan',
        }
    if target is None:
        return {
            'state': 'locked',
            'feature': feat,
            'feature_label': meta.get('label') or feat,
            'title': f'{meta.get("label") or feat} no disponible',
            'body': 'Esta funcionalidad no está incluida en su plan actual. Contacte a ventas.',
            'current_plan': current,
            'target_plan': None,
            'cta_primary': None,
            'cta_secondary_label': 'Ver planes',
        }
    price = format_price(float(target['price_monthly']), target.get('currency') or 'USD')
    return {
        'state': 'locked',
        'feature': feat,
        'feature_label': meta.get('label') or feat,
        'title': f'{meta.get("label") or feat} no está en su plan',
        'body': (
            f'Esta funcionalidad no está incluida en su plan {current["name"]}. '
            f'Actualice a {target["name"]} por {price}/mes.'
        ),
        'current_plan': current,
        'target_plan': target,
        'cta_primary': {
            'label': f'Actualizar a {target["name"]}',
            'plan_code': target['code'],
            'price_label': f'{price}/mes',
        },
        'cta_secondary_label': 'Ver planes',
    }


def resolve_org_plan_code(organization_id: int, product_code: str = 'eposone') -> str:
    try:
        from nodeone.core.platform.entitlement_service import EntitlementService

        rec = EntitlementService.get_for_tenant_product(
            int(organization_id),
            product_code,
            scope_organization_id=int(organization_id),
        )
        if rec is not None and rec.plan_code:
            return normalize_commercial_plan_code(rec.plan_code)
    except Exception:
        pass
    return 'starter'


def feature_nav_state_for_org(
    organization_id: int | None,
    feature: str,
    *,
    product_code: str = 'eposone',
) -> FeatureNavState:
    meta = FEATURE_CATALOG.get((feature or '').strip().lower()) or {}
    if meta.get('default_state') == 'coming_soon':
        return 'coming_soon'
    if organization_id is None:
        return feature_nav_state_for_plan('starter', feature)
    plan_code = resolve_org_plan_code(int(organization_id), product_code)
    try:
        from nodeone.core.platform.entitlement_service import EntitlementService

        rec = EntitlementService.get_for_tenant_product(
            int(organization_id),
            product_code,
            scope_organization_id=int(organization_id),
        )
        if rec is not None:
            if not rec.is_operable:
                return 'locked'
            if EntitlementService.has_feature(
                int(organization_id),
                product_code,
                feature,
                scope_organization_id=int(organization_id),
            ):
                return 'available'
            return 'locked'
    except Exception:
        pass
    return feature_nav_state_for_plan(plan_code, feature)


def _count_usage(organization_id: int) -> dict[str, int]:
    """Consumo actual del tenant (best-effort).

    Cualquier fallo SQL debe hacer ``rollback``: si no, la transacción queda
    abortada y ``render_template`` (context processors) revienta — p. ej. Mi plan.
    """
    usage = {
        'branches': 0,
        'pos': 0,
        'registers': 0,
        'tablets': 0,
        'cashiers': 0,
        'products': 0,
        'customers': 0,
    }

    def _rollback_quiet() -> None:
        try:
            from nodeone.core.db import db

            db.session.rollback()
        except Exception:
            pass

    try:
        from nodeone.core.master.constants import (
            ORG_UNIT_TYPE_BRANCH,
            ORG_UNIT_TYPE_POS,
            ORG_UNIT_TYPE_REGISTER,
        )
        from nodeone.core.services.org_unit import OrgUnitService

        usage['branches'] = len(
            OrgUnitService.list_units(int(organization_id), unit_type=ORG_UNIT_TYPE_BRANCH)
        )
        usage['pos'] = len(OrgUnitService.list_units(int(organization_id), unit_type=ORG_UNIT_TYPE_POS))
        usage['registers'] = len(
            OrgUnitService.list_units(int(organization_id), unit_type=ORG_UNIT_TYPE_REGISTER)
        )
    except Exception:
        _rollback_quiet()
    try:
        from models.core_master import CoreProduct

        usage['products'] = int(
            CoreProduct.query.filter_by(organization_id=int(organization_id)).count()
        )
    except Exception:
        _rollback_quiet()
    try:
        from models.eposone_cashier import EposoneCashierCredential

        usage['cashiers'] = int(
            EposoneCashierCredential.query.filter_by(organization_id=int(organization_id)).count()
        )
    except Exception:
        _rollback_quiet()
    try:
        from models.contact import Contact

        usage['customers'] = int(
            Contact.query.filter_by(organization_id=int(organization_id)).count()
        )
    except Exception:
        _rollback_quiet()
    try:
        from models.commercial_core import CorePosTerminal

        usage['tablets'] = int(
            CorePosTerminal.query.filter_by(organization_id=int(organization_id)).count()
        )
    except Exception:
        _rollback_quiet()
    return usage


_LIMIT_LABELS = {
    'branches': 'Sucursales',
    'pos': 'Puntos de venta',
    'registers': 'Cajas',
    'tablets': 'Tablets',
    'cashiers': 'Cajeros',
    'products': 'Productos',
    'customers': 'Clientes',
}


def build_mi_plan_payload(organization_id: int, *, product_code: str = 'eposone') -> dict[str, Any]:
    plan_code = resolve_org_plan_code(organization_id, product_code)
    plan = get_commercial_plan(plan_code)
    usage = _count_usage(organization_id)
    limits = plan.get('resource_limits') or {}
    consumption: list[dict[str, Any]] = []
    for key, label in _LIMIT_LABELS.items():
        lim = limits.get(key)
        if lim is None:
            continue
        used = int(usage.get(key) or 0)
        unlimited = lim is None or int(lim) < 0
        consumption.append(
            {
                'key': key,
                'label': label,
                'used': used,
                'limit': None if unlimited else int(lim),
                'unlimited': unlimited,
                'display': f'{used} / ∞' if unlimited else f'{used} / {int(lim)}',
                'at_limit': (not unlimited) and used >= int(lim),
            }
        )

    features_out: list[dict[str, Any]] = []
    for feat_code, meta in FEATURE_CATALOG.items():
        state = feature_nav_state_for_org(organization_id, feat_code, product_code=product_code)
        features_out.append(
            {
                'code': feat_code,
                'label': meta.get('label') or feat_code,
                'description': meta.get('description') or '',
                'state': state,
            }
        )

    next_plan = None
    for code in _PLAN_ORDER:
        if _PLAN_ORDER.index(code) > _PLAN_ORDER.index(plan_code if plan_code in _PLAN_ORDER else 'starter'):
            next_plan = get_commercial_plan(code)
            break

    entitlement_state = None
    try:
        from nodeone.core.platform.entitlement_service import EntitlementService

        rec = EntitlementService.get_for_tenant_product(
            int(organization_id),
            product_code,
            scope_organization_id=int(organization_id),
        )
        if rec is not None:
            entitlement_state = rec.effective_state
    except Exception:
        pass

    return {
        'product_code': product_code,
        'plan': plan,
        'plan_code': plan_code,
        'price_label': format_price(float(plan['price_monthly']), plan.get('currency') or 'USD'),
        'entitlement_state': entitlement_state,
        'consumption': consumption,
        'features': features_out,
        'all_plans': list_commercial_plans(),
        'next_plan': next_plan,
        'next_plan_price_label': (
            format_price(float(next_plan['price_monthly']), next_plan.get('currency') or 'USD')
            if next_plan
            else None
        ),
    }
