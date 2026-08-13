"""Alta comercial mínima (ADR-031): Cliente + Contrato bajo compañía ETS.

No crea recursos operacionales (sucursal/POS/caja) ni cascarón-tenant por comprador.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime
from typing import Any

from nodeone.core.platform.commercial_plans import operating_modality_for_plan


def plan_modality(plan_code: str) -> str:
    """Alias estable → modalidad Standalone|Connected (ADR-027/031)."""
    return operating_modality_for_plan(plan_code)


def _new_contract_number() -> str:
    stamp = datetime.utcnow().strftime('%Y%m%d')
    return f'CTR-{stamp}-{secrets.token_hex(3).upper()}'


def ensure_customer_and_contract(
    *,
    organization_id: int,
    user_id: int,
    display_name: str,
    email: str,
    country: str | None,
    product_code: str,
    plan_code: str,
    source: str = 'eposone_start_assistant',
    metadata: dict[str, Any] | None = None,
    phone: str | None = None,
    contact_id: int | None = None,
) -> dict[str, Any]:
    """Crea (o reutiliza) Cliente bajo org proveedor ETS + Contrato activo del producto.

    organization_id = compañía productiva ETS (no el negocio del comprador).
    """
    from models.ets_commercial_contract import EtsCommercialContract
    from models.ets_commercial_customer import EtsCommercialCustomer
    from models.users import User
    from nodeone.core.db import db
    from nodeone.core.platform.standalone_expediente import ensure_standalone_contact

    oid = int(organization_id)
    mail = (email or '').strip().lower()[:200]
    meta = dict(metadata or {})
    meta_json = json.dumps(meta, ensure_ascii=False) if meta else None
    now = datetime.utcnow()
    modality = plan_modality(plan_code)

    contact = ensure_standalone_contact(
        provider_organization_id=oid,
        full_name=display_name or mail,
        email=mail,
        phone=phone,
        country=country,
        fallback_last='ETS',
    )
    resolved_contact_id = int(contact_id) if contact_id else int(contact.id)

    user_row = User.query.get(int(user_id))
    if user_row is not None and hasattr(user_row, 'linked_contact_id'):
        if not user_row.linked_contact_id:
            user_row.linked_contact_id = resolved_contact_id

    customer = EtsCommercialCustomer.query.filter_by(organization_id=oid, email=mail).first()
    if customer is None:
        customer = EtsCommercialCustomer(
            organization_id=oid,
            display_name=(display_name or '').strip()[:200] or 'Cliente',
            email=mail,
            phone=(phone or '').strip()[:64] or None,
            country=(country or '').strip()[:120] or None,
            status='registered',
            primary_user_id=int(user_id),
            contact_id=resolved_contact_id,
            metadata_json=meta_json,
            created_at=now,
            updated_at=now,
        )
        db.session.add(customer)
        db.session.flush()
    else:
        customer.display_name = (display_name or customer.display_name)[:200]
        customer.email = mail
        if country:
            customer.country = country.strip()[:120]
        if phone:
            customer.phone = phone.strip()[:64]
        customer.primary_user_id = int(user_id)
        if not customer.contact_id:
            customer.contact_id = resolved_contact_id
        elif contact_id:
            customer.contact_id = int(contact_id)
        customer.updated_at = now
        if meta_json:
            customer.metadata_json = meta_json

    contract = (
        EtsCommercialContract.query.filter_by(
            customer_id=int(customer.id),
            product_code=product_code,
            status='active',
        )
        .order_by(EtsCommercialContract.id.desc())
        .first()
    )
    if contract is None:
        contract = EtsCommercialContract(
            contract_number=_new_contract_number(),
            customer_id=int(customer.id),
            organization_id=oid,
            product_code=product_code,
            plan_code=plan_code,
            modality=modality,
            status='active',
            starts_at=now,
            ends_at=None,
            source=source,
            metadata_json=meta_json,
            created_by_user_id=int(user_id),
            created_at=now,
            updated_at=now,
        )
        db.session.add(contract)
        db.session.flush()

    db.session.commit()
    return {
        'customer_id': int(customer.id),
        'contract_id': int(contract.id),
        'contract_number': contract.contract_number,
        'modality': contract.modality,
        'plan_code': contract.plan_code,
        'product_code': contract.product_code,
        'organization_id': oid,
        'contact_id': int(customer.contact_id) if customer.contact_id else None,
    }


def link_subscription_to_contract(
    *,
    organization_id: int,
    product_code: str,
    contract_id: int,
    customer_id: int | None = None,
) -> None:
    """Ancla la suscripción vigente al Contrato (ADR-031)."""
    from models.ets_product_subscription import EtsProductSubscription
    from nodeone.core.db import db

    if customer_id:
        row = EtsProductSubscription.query.filter_by(
            customer_id=int(customer_id),
            product_code=product_code,
        ).first()
    else:
        row = EtsProductSubscription.query.filter_by(
            organization_id=int(organization_id),
            product_code=product_code,
            customer_id=None,
        ).first()
        if row is None:
            row = EtsProductSubscription.query.filter_by(
                organization_id=int(organization_id),
                product_code=product_code,
            ).first()
    if row is None:
        return
    row.contract_id = int(contract_id)
    if customer_id and not row.customer_id:
        row.customer_id = int(customer_id)
    row.updated_at = datetime.utcnow()
    db.session.commit()
