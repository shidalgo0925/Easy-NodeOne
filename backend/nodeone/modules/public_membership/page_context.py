"""Contexto de la página portal /membership (planes × servicios)."""

from __future__ import annotations

from datetime import datetime
from typing import Any


_DEFAULT_HIERARCHY = {'basic': 0, 'personal': 1, 'emprendedor': 2, 'ejecutivo': 3}


def _membership_hierarchy(MembershipPlan) -> dict[str, int]:
    try:
        hierarchy = MembershipPlan.get_hierarchy()
        if hierarchy:
            return hierarchy
    except Exception:
        pass
    return dict(_DEFAULT_HIERARCHY)


def _available_plans_for_service(service, pricing_rules, hierarchy: dict[str, int]) -> list[str]:
    available_plans: list[str] = []
    smt = (service.membership_type or '').strip().lower()
    if smt:
        if smt == 'basic':
            if 'basic' not in available_plans:
                available_plans.append('basic')
            for slug, tier in hierarchy.items():
                if slug in ('admin', 'basic'):
                    continue
                if tier > 0 and slug not in available_plans:
                    available_plans.append(slug)
        elif smt not in available_plans:
            available_plans.append(smt)

    if pricing_rules:
        for rule in pricing_rules:
            mt = (rule.membership_type or '').strip().lower()
            if mt and mt not in available_plans:
                available_plans.append(mt)
    else:
        service_tier = hierarchy.get((service.membership_type or '').strip().lower(), -1)
        if service_tier >= 0:
            for plan_type, tier in hierarchy.items():
                if tier > service_tier and plan_type not in available_plans:
                    available_plans.append(plan_type)
    return available_plans


def _plan_label_and_badge(active_membership, plans) -> tuple[str, str, str]:
    """slug, label, badge bootstrap class."""
    if not active_membership:
        return '', '', 'bg-secondary'
    slug = (active_membership.membership_type or '').strip().lower()
    if slug == 'admin':
        return slug, 'Administrador', 'bg-primary'
    for plan in plans or []:
        if plan.slug == slug:
            return slug, plan.name, (plan.color or 'bg-secondary')
    return slug, (slug.title() if slug else ''), 'bg-secondary'


def _plan_cta(plan, *, current_slug: str, is_admin: bool, hierarchy: dict[str, int]) -> dict[str, str]:
    """CTA de compra/upgrade por columna de plan."""
    if is_admin:
        return {'kind': 'none'}
    slug = (plan.slug or '').strip().lower()
    if current_slug and slug == current_slug:
        return {'kind': 'current', 'label': 'Tu plan'}
    cur_level = hierarchy.get(current_slug, -1) if current_slug else -1
    plan_level = int(getattr(plan, 'level', None) or 0)
    if not current_slug or cur_level < 0:
        return {'kind': 'buy', 'label': 'Comprar', 'icon': 'fa-cart-plus', 'btn_class': 'btn-primary'}
    if plan_level > cur_level:
        return {'kind': 'upgrade', 'label': 'Upgrade', 'icon': 'fa-arrow-up', 'btn_class': 'btn-primary'}
    if plan_level < cur_level:
        return {'kind': 'downgrade', 'label': 'Cambiar', 'icon': 'fa-exchange-alt', 'btn_class': 'btn-outline-primary'}
    return {'kind': 'buy', 'label': 'Comprar', 'icon': 'fa-cart-plus', 'btn_class': 'btn-primary'}


def build_membership_portal_context(active_membership, *, organization_id: int) -> dict[str, Any]:
    from app import MembershipPlan, Service, ServicePricingRule

    plans = MembershipPlan.get_active_ordered(organization_id=organization_id)
    plans_display = [p for p in plans if (p.slug or '').lower() != 'admin']
    hierarchy = _membership_hierarchy(MembershipPlan)

    all_services = (
        Service.query.filter_by(is_active=True, organization_id=organization_id)
        .order_by(Service.display_order, Service.name)
        .all()
    )

    services_with_plans = []
    for service in all_services:
        pricing_rules = ServicePricingRule.query.filter_by(service_id=service.id, is_active=True).all()
        services_with_plans.append(
            {
                'service': service,
                'available_plans': _available_plans_for_service(service, pricing_rules, hierarchy),
            }
        )

    days_remaining = None
    if active_membership and getattr(active_membership, 'end_date', None):
        if (active_membership.membership_type or '').strip().lower() != 'admin':
            days_remaining = (active_membership.end_date - datetime.utcnow()).days

    current_plan_slug, current_plan_label, current_plan_badge = _plan_label_and_badge(active_membership, plans)
    is_admin_plan = bool(active_membership and current_plan_slug == 'admin')

    plan_columns = []
    for plan in plans_display:
        plan_columns.append(
            {
                'plan': plan,
                'is_current': bool(current_plan_slug and plan.slug == current_plan_slug),
                'cta': _plan_cta(
                    plan,
                    current_slug=current_plan_slug,
                    is_admin=is_admin_plan,
                    hierarchy=hierarchy,
                ),
            }
        )

    return {
        'membership': active_membership,
        'plans_display': plans_display,
        'plan_columns': plan_columns,
        'services_with_plans': services_with_plans,
        'days_remaining': days_remaining,
        'current_plan_slug': current_plan_slug,
        'current_plan_label': current_plan_label,
        'current_plan_badge': current_plan_badge,
        'is_admin_plan': is_admin_plan,
        'can_purchase_plans': not is_admin_plan,
    }
