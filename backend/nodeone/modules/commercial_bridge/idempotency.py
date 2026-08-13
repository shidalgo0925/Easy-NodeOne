"""Idempotencia formal del bridge comercial (Idempotency-Key)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.exc import IntegrityError

# TTL documentado: 7 días. Tras expirar, la key puede reutilizarse.
IDEMPOTENCY_TTL = timedelta(days=7)


def normalize_idempotency_key(raw: str | None) -> str | None:
    if not raw:
        return None
    s = str(raw).strip()
    if not s:
        return None
    return s[:128]


def request_body_hash(payload: dict[str, Any]) -> str:
    """Hash canónico del body lógico (orden de claves estable)."""
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'), default=str)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def ensure_idempotency_table() -> None:
    from nodeone.core.db import db
    from nodeone.modules.commercial_bridge.models import CommercialBridgeIdempotency

    CommercialBridgeIdempotency.__table__.create(db.engine, checkfirst=True)


def lookup_idempotent(
    *,
    organization_id: int,
    operation: str,
    key: str,
    request_hash: str,
) -> tuple[str, tuple[int, dict] | None]:
    """Retorna (status, cached).

    status:
      - ``miss``: no hay registro (o expiró)
      - ``hit``: misma key + mismo hash → cached response
      - ``conflict``: misma key + hash distinto
    """
    ensure_idempotency_table()
    from nodeone.core.db import db
    from nodeone.modules.commercial_bridge.models import CommercialBridgeIdempotency

    row = CommercialBridgeIdempotency.query.filter_by(
        organization_id=int(organization_id),
        operation=str(operation),
        idempotency_key=key,
    ).first()
    if row is None:
        return 'miss', None

    now = datetime.utcnow()
    if row.expires_at and row.expires_at < now:
        db.session.delete(row)
        db.session.commit()
        return 'miss', None

    if row.request_hash != request_hash:
        return 'conflict', None

    try:
        body = json.loads(row.response_body)
        if not isinstance(body, dict):
            return 'miss', None
        return 'hit', (int(row.response_status), body)
    except (json.JSONDecodeError, TypeError, ValueError):
        return 'miss', None


def store_idempotent(
    *,
    organization_id: int,
    operation: str,
    key: str,
    request_hash: str,
    status: int,
    body: dict[str, Any],
) -> None:
    ensure_idempotency_table()
    from nodeone.core.db import db
    from nodeone.modules.commercial_bridge.models import CommercialBridgeIdempotency

    now = datetime.utcnow()
    row = CommercialBridgeIdempotency(
        organization_id=int(organization_id),
        operation=str(operation),
        idempotency_key=key,
        request_hash=request_hash,
        response_status=int(status),
        response_body=json.dumps(body, ensure_ascii=False, default=str),
        created_at=now,
        expires_at=now + IDEMPOTENCY_TTL,
    )
    db.session.add(row)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        # Carrera: otro worker guardó primero — revalidar hash.
        status_code, cached = lookup_idempotent(
            organization_id=organization_id,
            operation=operation,
            key=key,
            request_hash=request_hash,
        )
        if status_code == 'conflict':
            from nodeone.modules.commercial_bridge.service import CommercialBridgeError

            raise CommercialBridgeError(
                'idempotency_conflict',
                'Idempotency-Key reutilizado con body distinto',
                http_status=409,
            )
        # hit u otro miss: ok (respuesta ya persistida)


def bootstrap_idempotency_payload(body: dict[str, Any]) -> dict[str, Any]:
    identity = body.get('identity') or {}
    customer = body.get('customer') or {}
    return {
        'product_code': str(body.get('product_code') or '').strip().lower(),
        'plan_code': str(body.get('plan_code') or '').strip().lower(),
        'email': str(identity.get('email') or customer.get('email') or '').strip().lower(),
        'external_subject_id': str(identity.get('external_subject_id') or '').strip(),
        'legal_name': str(customer.get('legal_name') or '').strip(),
        'country': str(customer.get('country') or '').strip().upper(),
        'phone': str(customer.get('phone') or '').strip(),
        'esb_organization_id': customer.get('esb_organization_id'),
    }


def checkout_idempotency_payload(body: dict[str, Any]) -> dict[str, Any]:
    payment = body.get('payment') or {}
    return {
        'product_code': str(body.get('product_code') or '').strip().lower(),
        'plan_code': str(body.get('plan_code') or '').strip().lower(),
        'customer_id': body.get('customer_id'),
        'promo_code': str(body.get('promo_code') or '').strip().upper(),
        'payment_method': str(payment.get('method') or '').strip(),
    }
