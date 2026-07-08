"""Helpers de eventos EPosOne (Etapa 8 — sin sync de tablas)."""

from __future__ import annotations

from typing import Any

from nodeone.core.commerce.order import OrderService
from nodeone.core.commerce.payment import PaymentService
from nodeone.core.platform.events import EPOSONE_ORDER_CREATED, EPOSONE_ORDER_PAID
from nodeone.core.services.audit import AuditService


def publish_order_created(
    organization_id: int,
    *,
    order_ref: str,
    total: float | None = None,
    extra: dict[str, Any] | None = None,
):
    payload: dict[str, Any] = {'order_ref': order_ref, 'status': 'created'}
    if total is not None:
        payload['total'] = total
    if extra:
        payload.update(extra)
    OrderService.publish_created(
        organization_id,
        order_ref=order_ref,
        status='created',
        grand_total=total,
        source_app_id='eposone',
        extra=extra,
    )
    return AuditService.publish_domain_event(
        organization_id,
        EPOSONE_ORDER_CREATED,
        payload,
        source_app_id='eposone',
    )


def publish_order_paid(organization_id: int, *, order_ref: str, payment_ref: str | None = None):
    payload: dict[str, Any] = {'order_ref': order_ref, 'status': 'paid'}
    if payment_ref:
        payload['payment_ref'] = payment_ref
    if payment_ref:
        PaymentService.publish_captured(
            organization_id,
            payment_ref=payment_ref,
            order_ref=order_ref,
            amount=float(payload.get('total') or 0),
            source_app_id='eposone',
        )
    return AuditService.publish_domain_event(
        organization_id,
        EPOSONE_ORDER_PAID,
        payload,
        source_app_id='eposone',
    )
