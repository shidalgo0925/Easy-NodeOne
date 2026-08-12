"""Bridge comercial ESB ↔ EN1 (S2S).

Reutiliza ProductRegistry, Cliente ETS, SubscriptionRegistry y DiscountCode.
No escribe org_memberships / carriers / dominio operativo ESB.
"""

from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timedelta
from typing import Any

from nodeone.core.platform.esecurebroker_commercial_plans import (
    PLAN_INDIVIDUAL,
    get_esb_list_price,
    get_esb_plan,
    normalize_esb_plan_code,
)
from nodeone.core.platform.entitlement_plans import get_plan_template

PRODUCT_ESB = 'esecurebroker'
DEFAULT_PLAN = PLAN_INDIVIDUAL
ALLOWED_PRODUCTS = frozenset({PRODUCT_ESB})


class CommercialBridgeError(Exception):
    def __init__(self, code: str, message: str = '', *, http_status: int = 400):
        super().__init__(message or code)
        self.code = code
        self.message = message or code
        self.http_status = int(http_status)


def _split_name(full_name: str) -> tuple[str, str]:
    parts = [p for p in (full_name or '').strip().split() if p]
    if not parts:
        return 'Usuario', 'ESB'
    if len(parts) == 1:
        return parts[0][:50], 'ESB'
    return parts[0][:50], ' '.join(parts[1:])[:50]


def _is_dev_database() -> bool:
    from nodeone.core.db import db

    uri = ''
    try:
        uri = str(db.engine.url)
    except Exception:
        uri = os.environ.get('DATABASE_URL') or ''
    uri_l = uri.lower()
    if 'easynodeone_prod' in uri_l or 'easynodeone_staging' in uri_l:
        return False
    return 'easynodeone_dev' in uri_l and 'postgresql' in uri_l


def _require_product(product_code: str) -> str:
    from nodeone.core.platform.product_context import SURFACE_PRODUCT
    from nodeone.core.platform.product_registry import ProductRegistry

    code = (product_code or '').strip().lower()
    if code not in ALLOWED_PRODUCTS:
        raise CommercialBridgeError('product_not_supported', f'Producto no soportado: {code}', http_status=400)
    definition = ProductRegistry.get(code)
    if definition is None or definition.surface != SURFACE_PRODUCT:
        raise CommercialBridgeError('unknown_product', f'Producto no registrado: {code}', http_status=400)
    return code


def _require_esb_plan(plan_code: str | None, *, for_checkout: bool) -> dict[str, Any]:
    raw = (plan_code or '').strip().lower() or DEFAULT_PLAN
    plan = get_esb_plan(raw)
    if plan is None:
        raise CommercialBridgeError(
            'invalid_plan',
            f'Plan ESecureBroker no válido: {raw}',
            http_status=400,
        )
    if for_checkout and plan.get('checkout_mode') != 'self_serve':
        raise CommercialBridgeError(
            'plan_requires_quote',
            f'Plan {plan["code"]} requiere cotización; no admite checkout self-serve',
            http_status=400,
        )
    return plan


def _validate_promo(*, code: str, user_id: int | None, list_amount: float) -> dict[str, Any]:
    """Valida DiscountCode; E2E DEV exige 100% → total $0 sobre list_amount del plan."""
    from models.events import DiscountCode

    raw = (code or '').strip().upper()
    if not raw:
        raise CommercialBridgeError('promo_required', 'promo_code requerido', http_status=400)
    row = DiscountCode.query.filter(DiscountCode.code.ilike(raw)).first()
    if row is None:
        row = DiscountCode.query.filter_by(code=raw).first()
    if row is None:
        raise CommercialBridgeError('promo_invalid', 'Código promocional no válido', http_status=400)
    ok, reason = row.can_use(user_id=user_id)
    if not ok:
        raise CommercialBridgeError('promo_invalid', reason, http_status=400)

    list_amt = float(list_amount)
    dtype = (row.discount_type or 'percentage').strip().lower()
    value = float(row.value or 0)
    if dtype == 'percentage' and value >= 100:
        discount_amount = list_amt
        final_amount = 0.0
    elif dtype == 'fixed' and value >= list_amt:
        discount_amount = list_amt
        final_amount = 0.0
    else:
        raise CommercialBridgeError(
            'promo_not_complimentary',
            'Este E2E solo acepta promo 100% (pago $0)',
            http_status=400,
        )
    return {
        'promo_code': row.code,
        'discount_code_id': int(row.id),
        'list_amount': list_amt,
        'discount_amount': discount_amount,
        'final_amount': final_amount,
        'currency': 'USD',
    }


def resolve_or_create_identity(
    *,
    email: str,
    full_name: str,
    external_subject_id: str | None = None,
) -> dict[str, Any]:
    from models.users import User
    from nodeone.core.db import db
    from nodeone.core.platform.ets_provider import ets_provider_organization_id

    mail = (email or '').strip().lower()
    if not mail or '@' not in mail:
        raise CommercialBridgeError('email_invalid', 'email inválido', http_status=400)
    provider_id = ets_provider_organization_id()
    user = User.query.filter_by(email=mail).first()
    created = False
    if user is None:
        first, last = _split_name(full_name)
        user = User(
            email=mail,
            first_name=first,
            last_name=last,
            organization_id=int(provider_id),
            is_admin=False,
            email_verified=False,
            is_active=True,
        )
        user.set_password(secrets.token_urlsafe(24))
        db.session.add(user)
        db.session.commit()
        created = True
    return {
        'user_id': int(user.id),
        'email': mail,
        'created': created,
        'external_subject_id': (external_subject_id or '').strip() or None,
        'provider_organization_id': int(provider_id),
    }


def bootstrap(body: dict[str, Any]) -> dict[str, Any]:
    """Registro comercial: Identity + Cliente ETS + Contrato (sin org operativa ESB)."""
    from nodeone.core.platform.commercial_registration import (
        ensure_customer_and_contract,
        link_subscription_to_contract,
    )
    from nodeone.core.platform.ets_provider import ets_provider_organization_id
    from nodeone.core.platform.subscription_registry import SubscriptionRegistry

    product_code = _require_product(str(body.get('product_code') or PRODUCT_ESB))
    identity_in = body.get('identity') or {}
    customer_in = body.get('customer') or {}
    plan = _require_esb_plan(body.get('plan_code'), for_checkout=False)
    plan_code = plan['code']

    email = identity_in.get('email') or customer_in.get('email')
    full_name = identity_in.get('full_name') or customer_in.get('legal_name') or email
    ext_sub = identity_in.get('external_subject_id')

    identity = resolve_or_create_identity(
        email=str(email or ''),
        full_name=str(full_name or ''),
        external_subject_id=str(ext_sub) if ext_sub else None,
    )
    provider_id = ets_provider_organization_id()
    commercial = ensure_customer_and_contract(
        organization_id=int(provider_id),
        user_id=int(identity['user_id']),
        display_name=str(customer_in.get('legal_name') or full_name or email),
        email=identity['email'],
        country=str(customer_in.get('country') or 'PA'),
        product_code=product_code,
        plan_code=plan_code,
        source='esb_commercial_bridge',
        phone=(str(customer_in.get('phone')).strip()[:64] if customer_in.get('phone') else None),
        metadata={
            'external_subject_id': identity.get('external_subject_id'),
            'source': 'esb_registro',
            'esb_organization_hint': customer_in.get('esb_organization_id'),
        },
    )

    try:
        SubscriptionRegistry.create_trial(
            int(provider_id),
            product_code,
            datetime.utcnow() + timedelta(days=14),
            user_id=int(identity['user_id']),
            customer_id=int(commercial['customer_id']),
            metadata={
                'plan_code': plan_code,
                'source': 'esb_commercial_bridge',
                'state': 'prepared',
            },
        )
    except Exception:
        pass

    link_subscription_to_contract(
        organization_id=int(provider_id),
        product_code=product_code,
        contract_id=int(commercial['contract_id']),
        customer_id=int(commercial['customer_id']),
    )

    return {
        'product_code': product_code,
        'plan_code': plan_code,
        'identity': {
            'user_id': identity['user_id'],
            'email': identity['email'],
            'created': identity['created'],
            'external_subject_id': identity.get('external_subject_id'),
        },
        'customer_id': int(commercial['customer_id']),
        'contract_id': int(commercial['contract_id']),
        'contract_number': commercial.get('contract_number'),
        'provider_organization_id': int(provider_id),
    }


def checkout(body: dict[str, Any]) -> dict[str, Any]:
    """Checkout ESB: promo 100% → payment $0 → subscription ACTIVE → entitlement."""
    from models.ets_commercial_customer import EtsCommercialCustomer
    from models.ets_product_subscription import EtsProductSubscription
    from models.events import DiscountApplication, DiscountCode
    from nodeone.core.db import db
    from nodeone.core.platform.commercial_registration import link_subscription_to_contract
    from nodeone.core.platform.entitlement_service import EntitlementService
    from nodeone.core.platform.ets_provider import ets_provider_organization_id

    product_code = _require_product(str(body.get('product_code') or PRODUCT_ESB))
    plan = _require_esb_plan(body.get('plan_code'), for_checkout=True)
    plan_code = plan['code']
    list_amount = get_esb_list_price(plan_code)
    if list_amount is None:
        raise CommercialBridgeError(
            'plan_requires_quote',
            f'Plan {plan_code} sin list price self-serve',
            http_status=400,
        )

    try:
        customer_id = int(body.get('customer_id'))
    except (TypeError, ValueError) as exc:
        raise CommercialBridgeError('customer_id_invalid', 'customer_id inválido', http_status=400) from exc

    provider_id = ets_provider_organization_id()
    customer = EtsCommercialCustomer.query.filter_by(
        id=customer_id, organization_id=int(provider_id)
    ).first()
    if customer is None:
        raise CommercialBridgeError('customer_not_found', 'Cliente ETS no encontrado', http_status=404)

    promo = _validate_promo(
        code=str(body.get('promo_code') or ''),
        user_id=customer.primary_user_id,
        list_amount=float(list_amount),
    )
    payment_in = body.get('payment') or {}
    method = str(payment_in.get('method') or 'promo_comp').strip()[:40]

    now = datetime.utcnow()
    row = EtsProductSubscription.query.filter_by(
        customer_id=int(customer_id), product_code=product_code
    ).first()
    if row is None:
        row = EtsProductSubscription(
            organization_id=int(provider_id),
            product_code=product_code,
            customer_id=int(customer_id),
            status='active',
            starts_at=now,
            ends_at=None,
            trial_ends_at=None,
            created_at=now,
            updated_at=now,
            created_by_user_id=customer.primary_user_id,
            updated_by_user_id=customer.primary_user_id,
        )
        db.session.add(row)
    else:
        row.status = 'active'
        row.ends_at = None
        row.trial_ends_at = None
        row.updated_at = now
        row.organization_id = int(provider_id)

    meta = {
        'source': 'esb_commercial_bridge',
        'plan_code': plan_code,
        'promo_code': promo['promo_code'],
        'payment': {
            'method': method,
            'amount': promo['final_amount'],
            'currency': promo['currency'],
            'list_amount': promo['list_amount'],
            'discount_amount': promo['discount_amount'],
            'recorded_at': now.isoformat() + 'Z',
        },
    }
    row.metadata_json = json.dumps(meta, ensure_ascii=False)
    db.session.flush()

    from models.ets_commercial_contract import EtsCommercialContract

    contract = (
        EtsCommercialContract.query.filter_by(
            customer_id=int(customer_id), product_code=product_code, status='active'
        )
        .order_by(EtsCommercialContract.id.desc())
        .first()
    )
    if contract is not None:
        row.contract_id = int(contract.id)
        contract.plan_code = plan_code
        contract.updated_at = now

    dc = DiscountCode.query.get(int(promo['discount_code_id']))
    if dc is not None and customer.primary_user_id:
        dc.current_uses = int(dc.current_uses or 0) + 1
        dc.updated_at = now
        db.session.add(
            DiscountApplication(
                discount_code_id=int(dc.id),
                user_id=int(customer.primary_user_id),
                original_amount=float(promo['list_amount']),
                discount_amount=float(promo['discount_amount']),
                final_amount=float(promo['final_amount']),
                applied_at=now,
            )
        )

    db.session.commit()

    try:
        EntitlementService.ensure_for_subscription(
            int(provider_id), product_code, plan_code=plan_code
        )
    except Exception:
        pass

    if contract is not None:
        link_subscription_to_contract(
            organization_id=int(provider_id),
            product_code=product_code,
            contract_id=int(contract.id),
            customer_id=int(customer_id),
        )

    return {
        'product_code': product_code,
        'customer_id': int(customer_id),
        'subscription_id': int(row.id),
        'subscription_status': 'active',
        'entitlement_state': 'active',
        'plan_code': plan_code,
        'payment': meta['payment'],
        'promo_code': promo['promo_code'],
    }


def _plan_code_from_subscription(row) -> str:
    plan = DEFAULT_PLAN
    if row and row.metadata_json:
        try:
            plan = json.loads(row.metadata_json).get('plan_code') or plan
        except Exception:
            pass
    normalized = normalize_esb_plan_code(plan)
    return normalized or plan


def get_entitlement(*, product_code: str, customer_id: int) -> dict[str, Any]:
    from models.ets_commercial_customer import EtsCommercialCustomer
    from models.ets_product_subscription import EtsProductSubscription
    from nodeone.core.platform.ets_provider import ets_provider_organization_id

    code = _require_product(product_code)
    try:
        cid = int(customer_id)
    except (TypeError, ValueError) as exc:
        raise CommercialBridgeError('customer_id_invalid', 'customer_id inválido', http_status=400) from exc

    provider_id = ets_provider_organization_id()
    customer = EtsCommercialCustomer.query.filter_by(
        id=cid, organization_id=int(provider_id)
    ).first()
    if customer is None:
        raise CommercialBridgeError('customer_not_found', 'Cliente ETS no encontrado', http_status=404)

    row = EtsProductSubscription.query.filter_by(customer_id=cid, product_code=code).first()
    status = str(row.status) if row is not None else None
    entitled = status in ('active', 'trial', 'past_due')
    plan = _plan_code_from_subscription(row)
    template = get_plan_template(code, plan)
    limits = dict(template.get('resource_limits') or {})
    features = dict(template.get('features') or {})

    return {
        'product_code': code,
        'customer_id': cid,
        'entitled': entitled,
        'state': status if entitled else (status or 'none'),
        'plan_code': plan,
        'subscription_id': int(row.id) if row is not None else None,
        'limits': limits,
        'features': features,
    }


def ensure_dev_promo_code() -> str | None:
    """Idempotente: crea ESB-DEV-100 solo en BD Dev (nunca prod/staging)."""
    if not _is_dev_database():
        return None

    from models.events import DiscountCode
    from nodeone.core.db import db

    code = 'ESB-DEV-100'
    row = DiscountCode.query.filter(DiscountCode.code.ilike(code)).first()
    if row is None:
        row = DiscountCode(
            code=code,
            name='ESecureBroker DEV 100%',
            description='Promo E2E ESB↔EN1 DEV — complimentary (solo easynodeone_dev)',
            discount_type='percentage',
            value=100.0,
            applies_to='all',
            is_active=True,
            max_uses_total=10000,
            max_uses_per_user=50,
            current_uses=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.session.add(row)
        db.session.commit()
    else:
        row.is_active = True
        row.discount_type = 'percentage'
        row.value = 100.0
        row.updated_at = datetime.utcnow()
        db.session.commit()
    return code


def migrate_dev_esb_starter_to_individual() -> dict[str, Any]:
    """Migración DEV documentada: plan_code starter → individual (esecurebroker).

    Preferencia C1: migración explícita (no alias permanente).
    Solo corre contra ``easynodeone_dev``.
    """
    if not _is_dev_database():
        return {'migrated': False, 'reason': 'not_dev'}

    from models.ets_commercial_contract import EtsCommercialContract
    from models.ets_product_subscription import EtsProductSubscription
    from nodeone.core.db import db

    updated_subs = 0
    updated_contracts = 0
    details: list[dict[str, Any]] = []

    for row in EtsProductSubscription.query.filter_by(product_code=PRODUCT_ESB).all():
        meta: dict[str, Any] = {}
        if row.metadata_json:
            try:
                meta = json.loads(row.metadata_json) or {}
            except Exception:
                meta = {}
        if str(meta.get('plan_code') or '').strip().lower() != 'starter':
            continue
        meta['plan_code'] = PLAN_INDIVIDUAL
        meta['migrated_from_plan'] = 'starter'
        meta['migrated_at'] = datetime.utcnow().isoformat() + 'Z'
        row.metadata_json = json.dumps(meta, ensure_ascii=False)
        row.updated_at = datetime.utcnow()
        updated_subs += 1
        details.append({'subscription_id': int(row.id), 'customer_id': row.customer_id})

    for contract in EtsCommercialContract.query.filter_by(product_code=PRODUCT_ESB).all():
        if str(contract.plan_code or '').strip().lower() != 'starter':
            continue
        contract.plan_code = PLAN_INDIVIDUAL
        contract.updated_at = datetime.utcnow()
        updated_contracts += 1
        details.append({'contract_id': int(contract.id), 'customer_id': contract.customer_id})

    if updated_subs or updated_contracts:
        db.session.commit()

    return {
        'migrated': True,
        'decision': 'B',
        'from': 'starter',
        'to': PLAN_INDIVIDUAL,
        'subscriptions_updated': updated_subs,
        'contracts_updated': updated_contracts,
        'details': details,
    }
