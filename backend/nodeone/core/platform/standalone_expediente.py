"""Expediente comercial Standalone bajo ETS — Contact + atribución + evidencia contrato.

No crea Org operativa del comprador. No duplica identidad en 5 tablas:
SoT identidad = en1_contact; customer/contrato/sub/licencia apuntan con FKs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from nodeone.core.platform.commercial_plans import get_commercial_plan


def _country_code(country: str | None) -> str:
    raw = (country or '').strip()
    if not raw:
        return 'PA'
    low = raw.lower()
    if low in ('panamá', 'panama', 'pa'):
        return 'PA'
    return raw[:8].upper() if len(raw) <= 8 else 'PA'


def _split_display_name(full_name: str) -> tuple[str, str]:
    parts = [p for p in (full_name or '').strip().split() if p]
    if not parts:
        return 'Usuario', 'EPosOne'
    if len(parts) == 1:
        return parts[0][:50], 'EPosOne'
    return parts[0][:50], ' '.join(parts[1:])[:50]


def ensure_standalone_contact(
    *,
    provider_organization_id: int,
    full_name: str,
    email: str,
    phone: str | None = None,
    country: str | None = None,
    intended_business_name: str | None = None,
) -> Any:
    """Crea o reutiliza en1_contact (cliente ETS) por email bajo el proveedor."""
    from models.contact import Contact
    from nodeone.core.db import db

    mail = (email or '').strip().lower()
    first, last = _split_display_name(full_name)
    display = (full_name or '').strip() or mail
    phone_n = (phone or '').strip()[:50] or None
    biz = (intended_business_name or '').strip()[:300] or None

    row = None
    if mail:
        row = (
            Contact.query.filter_by(organization_id=int(provider_organization_id), email=mail)
            .order_by(Contact.id.desc())
            .first()
        )
    if row is None:
        row = Contact(
            organization_id=int(provider_organization_id),
            contact_type='person',
            display_name=display[:300],
            first_name=first,
            last_name=last,
            commercial_name=biz,
            email=mail[:255] if mail else None,
            phone=phone_n,
            mobile=phone_n,
            country=_country_code(country),
            identification_type='consumer_final',
            is_customer=True,
            active=True,
        )
        db.session.add(row)
        db.session.flush()
    else:
        row.is_customer = True
        row.active = True
        if display:
            row.display_name = display[:300]
        row.first_name = first
        row.last_name = last
        if phone_n:
            row.phone = phone_n
            row.mobile = phone_n
        if biz:
            row.commercial_name = biz
        row.country = _country_code(country)
        row.updated_at = datetime.utcnow()
        db.session.flush()
    return row


def apply_contract_commercial_terms(
    *,
    contract,
    plan_code: str,
    user_id: int,
    contract_type: str = 'electronic',
    terms_version: str | None = None,
    billing_period: str = 'monthly',
    agreed_price: float | None = None,
    discount_percent: float | None = None,
    discount_amount: float | None = None,
    implementation_mode: str = 'self_serve',
) -> None:
    """Rellena condiciones + evidencia electrónica en el contrato (sin duplicar identidad)."""
    from nodeone.core.db import db

    plan = get_commercial_plan(plan_code)
    period = (billing_period or 'monthly').strip().lower()
    if period not in ('monthly', 'annual'):
        period = 'monthly'
    price = agreed_price
    if price is None:
        price = float(plan.get('price_annual') if period == 'annual' else plan.get('price_monthly') or 0)

    contract.agreed_price = price
    contract.discount_percent = discount_percent
    contract.discount_amount = discount_amount
    contract.currency = (plan.get('currency') or 'USD')[:8]
    contract.billing_period = period
    contract.implementation_mode = (implementation_mode or 'self_serve')[:32]
    contract.contract_type = (contract_type or 'electronic')[:16]
    contract.contract_version = 'standalone-v1'
    contract.terms_version = (terms_version or 'start-legal-v1')[:32]
    contract.accepted_at = datetime.utcnow()
    contract.accepted_by_user_id = int(user_id)
    contract.updated_at = datetime.utcnow()
    db.session.flush()


def ensure_attribution(
    *,
    provider_organization_id: int,
    customer_id: int,
    contract_id: int | None = None,
    channel: str | None = None,
    source_detail: str | None = None,
    campaign: str | None = None,
    referral_code: str | None = None,
    advisor_user_id: int | None = None,
    utm_source: str | None = None,
    utm_medium: str | None = None,
    utm_campaign: str | None = None,
    utm_content: str | None = None,
    utm_term: str | None = None,
    landing_url: str | None = None,
) -> Any:
    from models.ets_commercial_attribution import EtsCommercialAttribution
    from nodeone.core.db import db

    ch = (channel or 'web').strip().lower()[:64] or 'web'
    row = EtsCommercialAttribution.query.filter_by(customer_id=int(customer_id)).first()
    now = datetime.utcnow()
    if row is None:
        row = EtsCommercialAttribution(
            organization_id=int(provider_organization_id),
            customer_id=int(customer_id),
            contract_id=int(contract_id) if contract_id else None,
            channel=ch,
            source_detail=(source_detail or '').strip()[:200] or None,
            campaign=(campaign or '').strip()[:200] or None,
            referral_code=(referral_code or '').strip()[:64] or None,
            advisor_user_id=int(advisor_user_id) if advisor_user_id else None,
            utm_source=(utm_source or '').strip()[:120] or None,
            utm_medium=(utm_medium or '').strip()[:120] or None,
            utm_campaign=(utm_campaign or '').strip()[:120] or None,
            utm_content=(utm_content or '').strip()[:120] or None,
            utm_term=(utm_term or '').strip()[:120] or None,
            landing_url=(landing_url or '').strip()[:500] or None,
            attributed_at=now,
            created_at=now,
            updated_at=now,
        )
        db.session.add(row)
    else:
        if contract_id:
            row.contract_id = int(contract_id)
        row.channel = ch
        if source_detail:
            row.source_detail = source_detail.strip()[:200]
        if campaign:
            row.campaign = campaign.strip()[:200]
        if referral_code:
            row.referral_code = referral_code.strip()[:64]
        if advisor_user_id:
            row.advisor_user_id = int(advisor_user_id)
        for attr, val in (
            ('utm_source', utm_source),
            ('utm_medium', utm_medium),
            ('utm_campaign', utm_campaign),
            ('utm_content', utm_content),
            ('utm_term', utm_term),
            ('landing_url', landing_url),
        ):
            if val:
                setattr(row, attr, str(val).strip()[:500 if attr == 'landing_url' else 120])
        row.updated_at = now
    db.session.flush()
    return row


def mark_customer_active(customer_id: int) -> None:
    from models.ets_commercial_customer import EtsCommercialCustomer
    from nodeone.core.db import db

    row = EtsCommercialCustomer.query.get(int(customer_id))
    if row is None:
        return
    if row.status == 'registered':
        row.status = 'active'
        row.updated_at = datetime.utcnow()
        db.session.commit()
