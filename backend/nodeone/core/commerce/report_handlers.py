"""Handlers bus — reportes comerciales derivados (Etapa 8)."""

from __future__ import annotations

from nodeone.core.commerce.events import (
    COMMERCE_CASH_SHIFT_CLOSED,
    COMMERCE_ORDER_CANCELLED,
    COMMERCE_PAYMENT_CAPTURED,
    COMMERCE_PAYMENT_REFUNDED,
)
from nodeone.core.commerce.reports import CommerceReportService
from nodeone.core.platform.events import DomainEventMessage, subscribe

_REGISTERED = False


def _on_payment_captured(message: DomainEventMessage) -> None:
    try:
        CommerceReportService.process_payment_captured(message)
    except Exception:
        pass


def _on_payment_refunded(message: DomainEventMessage) -> None:
    try:
        CommerceReportService.process_payment_refunded(message)
    except Exception:
        pass


def _on_order_cancelled(message: DomainEventMessage) -> None:
    try:
        CommerceReportService.process_order_cancelled(message)
    except Exception:
        pass


def _on_cash_shift_closed(message: DomainEventMessage) -> None:
    try:
        CommerceReportService.process_cash_shift_closed(message)
    except Exception:
        pass


def register_commerce_report_handlers() -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    subscribe(COMMERCE_PAYMENT_CAPTURED, _on_payment_captured)
    subscribe(COMMERCE_PAYMENT_REFUNDED, _on_payment_refunded)
    subscribe(COMMERCE_ORDER_CANCELLED, _on_order_cancelled)
    subscribe(COMMERCE_CASH_SHIFT_CLOSED, _on_cash_shift_closed)
    _REGISTERED = True
