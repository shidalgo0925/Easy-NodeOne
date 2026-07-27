"""Reportes comerciales — KPIs derivados del bus (Etapa 8, dominio 6.9)."""

from __future__ import annotations

from typing import Any

from nodeone.core.commerce.events import (
    COMMERCE_REPORT_ORDER_VOIDED,
    COMMERCE_REPORT_REFUND_RECORDED,
    COMMERCE_REPORT_SALE_RECORDED,
    COMMERCE_REPORT_SHIFT_CLOSED,
)
from nodeone.core.platform.events import DomainEventMessage
from nodeone.core.services.audit import AuditService


class CommerceReportService:
    """v1 — sin tablas BI; publica métricas derivadas para analytics."""

    @staticmethod
    def process_payment_captured(message: DomainEventMessage) -> dict[str, Any]:
        payload = dict(message.payload or {})
        order_ref = (payload.get('order_ref') or '').strip()
        amount = float(payload.get('amount') or 0)
        if not order_ref or amount <= 0:
            return {'status': 'skipped', 'reason': 'missing_sale_fields'}

        return CommerceReportService._publish_metric(
            message,
            event_type=COMMERCE_REPORT_SALE_RECORDED,
            metric='sale',
            order_ref=order_ref,
            amount=amount,
            payment_ref=str(payload.get('payment_ref') or ''),
            payment_type=str(payload.get('payment_type') or ''),
            source_event_type=str(message.event_type or ''),
        )

    @staticmethod
    def process_payment_refunded(message: DomainEventMessage) -> dict[str, Any]:
        payload = dict(message.payload or {})
        order_ref = (payload.get('order_ref') or '').strip()
        amount = float(payload.get('amount') or 0)
        if not order_ref or amount <= 0:
            return {'status': 'skipped', 'reason': 'missing_refund_fields'}

        return CommerceReportService._publish_metric(
            message,
            event_type=COMMERCE_REPORT_REFUND_RECORDED,
            metric='refund',
            order_ref=order_ref,
            amount=amount,
            payment_ref=str(payload.get('payment_ref') or ''),
            source_event_type=str(message.event_type or ''),
        )

    @staticmethod
    def process_order_cancelled(message: DomainEventMessage) -> dict[str, Any]:
        payload = dict(message.payload or {})
        order_ref = (payload.get('order_ref') or '').strip()
        if not order_ref:
            return {'status': 'skipped', 'reason': 'missing_order_ref'}

        return CommerceReportService._publish_metric(
            message,
            event_type=COMMERCE_REPORT_ORDER_VOIDED,
            metric='order_voided',
            order_ref=order_ref,
            reason=str(payload.get('reason') or ''),
            source_event_type=str(message.event_type or ''),
        )

    @staticmethod
    def process_cash_shift_closed(message: DomainEventMessage) -> dict[str, Any]:
        payload = dict(message.payload or {})
        register_ref = (payload.get('register_ref') or '').strip()
        if not register_ref:
            return {'status': 'skipped', 'reason': 'missing_register_ref'}

        extra: dict[str, Any] = {
            'register_ref': register_ref,
            'closing_balance': float(payload.get('closing_balance') or 0),
        }
        if payload.get('expected_balance') is not None:
            extra['expected_balance'] = float(payload.get('expected_balance') or 0)
        if payload.get('variance') is not None:
            extra['variance'] = float(payload.get('variance') or 0)

        return CommerceReportService._publish_metric(
            message,
            event_type=COMMERCE_REPORT_SHIFT_CLOSED,
            metric='shift_closed',
            source_event_type=str(message.event_type or ''),
            **extra,
        )

    @staticmethod
    def _publish_metric(
        message: DomainEventMessage,
        *,
        event_type: str,
        metric: str,
        **fields: Any,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {'metric': metric}
        payload.update({k: v for k, v in fields.items() if v not in (None, '')})
        CommerceReportService.publish_metric(
            int(message.organization_id),
            event_type,
            payload,
            source_app_id=str(message.source_app_id or 'eposone'),
        )
        return {'status': 'published', 'metric': metric, 'event_type': event_type}

    @staticmethod
    def publish_metric(
        organization_id: int,
        event_type: str,
        payload: dict[str, Any],
        *,
        source_app_id: str = 'eposone',
    ):
        return AuditService.publish_domain_event(
            organization_id,
            event_type,
            payload,
            source_app_id=source_app_id,
        )
