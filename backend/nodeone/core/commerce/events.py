"""Eventos de dominio comercial — Etapa 12."""

from __future__ import annotations

COMMERCE_ORDER_CREATED = 'commerce.order.created'
COMMERCE_ORDER_CONFIRMED = 'commerce.order.confirmed'
COMMERCE_ORDER_STATUS_CHANGED = 'commerce.order.status_changed'
COMMERCE_ORDER_PAYMENT_STATUS_CHANGED = 'commerce.order.payment_status_changed'
COMMERCE_ORDER_FISCAL_STATUS_CHANGED = 'commerce.order.fiscal_status_changed'
COMMERCE_ORDER_LINE_STATUS_CHANGED = 'commerce.order.line_status_changed'
COMMERCE_ORDER_CANCELLED = 'commerce.order.cancelled'

COMMERCE_PAYMENT_INITIATED = 'commerce.payment.initiated'
COMMERCE_PAYMENT_CAPTURED = 'commerce.payment.captured'
COMMERCE_PAYMENT_FAILED = 'commerce.payment.failed'
COMMERCE_PAYMENT_REFUNDED = 'commerce.payment.refunded'

COMMERCE_INVOICE_ISSUED = 'commerce.invoice.issued'
COMMERCE_INVOICE_REQUESTED = 'commerce.invoice.requested'
COMMERCE_INVOICE_CANCELLED = 'commerce.invoice.cancelled'

COMMERCE_DELIVERY_STARTED = 'commerce.delivery.started'
COMMERCE_DELIVERY_COMPLETED = 'commerce.delivery.completed'

COMMERCE_CASH_SHIFT_OPENED = 'commerce.cash.shift.opened'
COMMERCE_CASH_SHIFT_RECONCILING = 'commerce.cash.shift.reconciling'
COMMERCE_CASH_SHIFT_CLOSED = 'commerce.cash.shift.closed'
COMMERCE_CASH_COUNT_RECORDED = 'commerce.cash.count.recorded'
COMMERCE_CASH_MOVEMENT_RECORDED = 'commerce.cash.movement.recorded'

COMMERCE_POS_TERMINAL_REGISTERED = 'commerce.pos.terminal.registered'

COMMERCE_AUTHORIZATION_APPLIED = 'commerce.authorization.applied'

COMMERCE_INVENTORY_RESERVED = 'commerce.inventory.reserved'
COMMERCE_INVENTORY_RELEASED = 'commerce.inventory.released'
COMMERCE_INVENTORY_DEDUCTED = 'commerce.inventory.deducted'
COMMERCE_INVENTORY_RETURNED = 'commerce.inventory.returned'
COMMERCE_INVENTORY_ADJUSTED = 'commerce.inventory.adjusted'

COMMERCE_REPORT_SALE_RECORDED = 'commerce.report.sale_recorded'
COMMERCE_REPORT_REFUND_RECORDED = 'commerce.report.refund_recorded'
COMMERCE_REPORT_ORDER_VOIDED = 'commerce.report.order_voided'
COMMERCE_REPORT_SHIFT_CLOSED = 'commerce.report.shift_closed'

COMMERCE_EVENT_TYPES = frozenset(
    {
        COMMERCE_ORDER_CREATED,
        COMMERCE_ORDER_CONFIRMED,
        COMMERCE_ORDER_STATUS_CHANGED,
        COMMERCE_ORDER_PAYMENT_STATUS_CHANGED,
        COMMERCE_ORDER_FISCAL_STATUS_CHANGED,
        COMMERCE_ORDER_LINE_STATUS_CHANGED,
        COMMERCE_ORDER_LINE_STATUS_CHANGED,
        COMMERCE_ORDER_CANCELLED,
        COMMERCE_PAYMENT_INITIATED,
        COMMERCE_PAYMENT_CAPTURED,
        COMMERCE_PAYMENT_FAILED,
        COMMERCE_PAYMENT_REFUNDED,
        COMMERCE_INVOICE_ISSUED,
        COMMERCE_INVOICE_REQUESTED,
        COMMERCE_INVOICE_CANCELLED,
        COMMERCE_DELIVERY_STARTED,
        COMMERCE_DELIVERY_COMPLETED,
        COMMERCE_CASH_SHIFT_OPENED,
        COMMERCE_CASH_SHIFT_RECONCILING,
        COMMERCE_CASH_SHIFT_CLOSED,
        COMMERCE_CASH_COUNT_RECORDED,
        COMMERCE_CASH_MOVEMENT_RECORDED,
        COMMERCE_POS_TERMINAL_REGISTERED,
        COMMERCE_AUTHORIZATION_APPLIED,
        COMMERCE_INVENTORY_RESERVED,
        COMMERCE_INVENTORY_RELEASED,
        COMMERCE_INVENTORY_DEDUCTED,
        COMMERCE_INVENTORY_RETURNED,
        COMMERCE_INVENTORY_ADJUSTED,
        COMMERCE_REPORT_SALE_RECORDED,
        COMMERCE_REPORT_REFUND_RECORDED,
        COMMERCE_REPORT_ORDER_VOIDED,
        COMMERCE_REPORT_SHIFT_CLOSED,
    }
)
