"""Comprador ETS → ficha canónica en1_contact (Clientes). Relación interna, no menú."""

from __future__ import annotations

import json
from typing import Any

from nodeone.core.platform.ets_provider import ets_provider_organization_id
from nodeone.core.platform.product_registry import ProductRegistry


def _product_name(code: str) -> str:
    row = ProductRegistry.get((code or '').strip().lower())
    if row is None:
        return code
    return (row.name or code).strip() or code


def _plan_from_meta(metadata_json: str | None) -> str | None:
    if not metadata_json:
        return None
    try:
        data = json.loads(metadata_json)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    raw = data.get('plan_code')
    return str(raw).strip().lower() if raw else None


def backfill_missing_buyer_contacts(*, limit: int = 500) -> int:
    """DEV/ops: clientes comerciales sin en1_contact → ensure idempotente."""
    from models.ets_commercial_customer import EtsCommercialCustomer
    from models.users import User
    from nodeone.core.db import db
    from nodeone.core.platform.standalone_expediente import ensure_standalone_contact

    rows = (
        EtsCommercialCustomer.query.filter(EtsCommercialCustomer.contact_id.is_(None))
        .order_by(EtsCommercialCustomer.id.asc())
        .limit(int(limit))
        .all()
    )
    n = 0
    for customer in rows:
        contact = ensure_standalone_contact(
            provider_organization_id=int(customer.organization_id),
            full_name=customer.display_name or customer.email,
            email=customer.email,
            phone=customer.phone,
            country=customer.country,
            fallback_last='ETS',
        )
        customer.contact_id = int(contact.id)
        if customer.primary_user_id:
            user = User.query.get(int(customer.primary_user_id))
            if user is not None and hasattr(user, 'linked_contact_id') and not user.linked_contact_id:
                user.linked_contact_id = int(contact.id)
        n += 1
    if n:
        db.session.commit()
    return n


def ets_buyer_contact_ids() -> list[int]:
    """Contactos canónicos de compradores ETS (org proveedor)."""
    from models.ets_commercial_customer import EtsCommercialCustomer

    oid = ets_provider_organization_id()
    rows = (
        EtsCommercialCustomer.query.filter(
            EtsCommercialCustomer.organization_id == int(oid),
            EtsCommercialCustomer.contact_id.isnot(None),
        )
        .with_entities(EtsCommercialCustomer.contact_id)
        .all()
    )
    seen: set[int] = set()
    out: list[int] = []
    for (cid,) in rows:
        n = int(cid)
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def product_labels_by_contact_id(contact_ids: list[int]) -> dict[int, list[str]]:
    from models.ets_commercial_customer import EtsCommercialCustomer

    ids = [int(i) for i in (contact_ids or []) if i]
    if not ids:
        return {}
    oid = ets_provider_organization_id()
    customers = (
        EtsCommercialCustomer.query.filter(
            EtsCommercialCustomer.organization_id == int(oid),
            EtsCommercialCustomer.contact_id.in_(ids),
        )
        .all()
    )
    out: dict[int, list[str]] = {}
    for customer in customers:
        cid = int(customer.contact_id) if customer.contact_id else 0
        if not cid:
            continue
        dossier = commercial_dossier(customer)
        labels = [str(p.get('product_name') or p.get('product_code') or '') for p in dossier.get('products') or []]
        out[cid] = [x for x in labels if x]
    return out


def list_commercial_customers(*, search: str = '', limit: int = 50, offset: int = 0) -> tuple[list[Any], int]:
    from models.ets_commercial_customer import EtsCommercialCustomer
    from sqlalchemy import func, or_

    oid = ets_provider_organization_id()
    q = EtsCommercialCustomer.query.filter_by(organization_id=int(oid))
    term = (search or '').strip()
    if term:
        like = f'%{term}%'
        q = q.filter(
            or_(
                EtsCommercialCustomer.email.ilike(like),
                EtsCommercialCustomer.display_name.ilike(like),
            )
        )
    total = q.with_entities(func.count(EtsCommercialCustomer.id)).scalar() or 0
    rows = (
        q.order_by(EtsCommercialCustomer.created_at.desc())
        .offset(int(offset))
        .limit(int(limit))
        .all()
    )
    return rows, int(total)


def commercial_dossier(customer) -> dict[str, Any]:
    """Relaciones comerciales para la ficha (sin duplicar columnas)."""
    from models.ets_commercial_contract import EtsCommercialContract
    from models.ets_product_entitlement import EtsProductEntitlement
    from models.ets_product_subscription import EtsProductSubscription
    from models.users import User
    from nodeone.core.platform.entitlement_service import EntitlementService

    contracts = (
        EtsCommercialContract.query.filter_by(customer_id=int(customer.id))
        .order_by(EtsCommercialContract.id.desc())
        .all()
    )
    subs = (
        EtsProductSubscription.query.filter_by(customer_id=int(customer.id))
        .order_by(EtsProductSubscription.id.desc())
        .all()
    )
    user = User.query.get(int(customer.primary_user_id)) if customer.primary_user_id else None

    products: list[dict[str, Any]] = []
    seen: set[str] = set()
    for contract in contracts:
        code = (contract.product_code or '').strip().lower()
        if not code or code in seen:
            continue
        seen.add(code)
        sub = next((s for s in subs if (s.product_code or '').strip().lower() == code), None)
        plan = (contract.plan_code or '').strip().lower()
        if sub:
            plan = _plan_from_meta(sub.metadata_json) or plan
        ent_state = None
        if sub is not None:
            rec = EntitlementService.get_by_subscription(int(sub.id))
            if rec is not None:
                ent_state = rec.effective_state
            else:
                ent_row = EtsProductEntitlement.query.filter_by(
                    organization_id=int(sub.organization_id),
                    product_code=code,
                ).first()
                if ent_row is not None:
                    ent_state = ent_row.effective_state
        products.append(
            {
                'product_code': code,
                'product_name': _product_name(code),
                'plan_code': plan,
                'commercial_status': customer.status,
                'contract_id': int(contract.id),
                'contract_number': contract.contract_number,
                'contract_status': contract.status,
                'subscription_id': int(sub.id) if sub is not None else None,
                'subscription_status': sub.status if sub is not None else None,
                'entitlement_state': ent_state,
                'created_at': customer.created_at,
            }
        )
    return {
        'customer': customer,
        'user': user,
        'products': products,
        'contact_id': int(customer.contact_id) if customer.contact_id else None,
    }


def dossier_for_contact(contact_id: int) -> dict[str, Any] | None:
    from models.ets_commercial_customer import EtsCommercialCustomer

    oid = ets_provider_organization_id()
    customer = EtsCommercialCustomer.query.filter_by(
        organization_id=int(oid), contact_id=int(contact_id)
    ).first()
    if customer is None:
        return None
    return commercial_dossier(customer)
