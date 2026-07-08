"""Helpers de eventos EPosOne (Etapa 8 — sin sync de tablas)."""

from __future__ import annotations

from typing import Any

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
    return AuditService.publish_domain_event(
        organization_id,
        EPOSONE_ORDER_PAID,
        payload,
        source_app_id='eposone',
    )
