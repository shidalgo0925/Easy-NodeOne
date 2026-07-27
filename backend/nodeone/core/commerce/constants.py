"""Constantes del dominio comercial — Etapa 12 (contrato v1)."""

from __future__ import annotations

# --- Pedido ---
ORDER_STATUS_DRAFT = 'draft'
ORDER_STATUS_CONFIRMED = 'confirmed'
ORDER_STATUS_IN_PROGRESS = 'in_progress'
ORDER_STATUS_READY = 'ready'
ORDER_STATUS_DELIVERED = 'delivered'
ORDER_STATUS_CANCELLED = 'cancelled'
ORDER_STATUS_REFUNDED = 'refunded'

# Alias semántico (dominio Etapa 6 — eje operativo)
OPERATIONAL_STATUS_DRAFT = ORDER_STATUS_DRAFT
OPERATIONAL_STATUS_CONFIRMED = ORDER_STATUS_CONFIRMED
OPERATIONAL_STATUS_IN_PROGRESS = ORDER_STATUS_IN_PROGRESS
OPERATIONAL_STATUS_READY = ORDER_STATUS_READY
OPERATIONAL_STATUS_DELIVERED = ORDER_STATUS_DELIVERED
OPERATIONAL_STATUS_CANCELLED = ORDER_STATUS_CANCELLED
OPERATIONAL_STATUS_REFUNDED = ORDER_STATUS_REFUNDED

# --- Eje pago del pedido (Etapa 7) ---
ORDER_PAYMENT_STATUS_UNPAID = 'unpaid'
ORDER_PAYMENT_STATUS_PARTIAL = 'partial'
ORDER_PAYMENT_STATUS_PAID = 'paid'
ORDER_PAYMENT_STATUS_OVERPAID = 'overpaid'

ORDER_PAYMENT_STATUSES = frozenset(
    {
        ORDER_PAYMENT_STATUS_UNPAID,
        ORDER_PAYMENT_STATUS_PARTIAL,
        ORDER_PAYMENT_STATUS_PAID,
        ORDER_PAYMENT_STATUS_OVERPAID,
    }
)

# --- Eje fiscal del pedido (Etapa 7) ---
ORDER_FISCAL_STATUS_NOT_REQUIRED = 'not_required'
ORDER_FISCAL_STATUS_PENDING = 'pending'
ORDER_FISCAL_STATUS_INVOICED = 'invoiced'
ORDER_FISCAL_STATUS_CANCELLED = 'cancelled'

ORDER_FISCAL_STATUSES = frozenset(
    {
        ORDER_FISCAL_STATUS_NOT_REQUIRED,
        ORDER_FISCAL_STATUS_PENDING,
        ORDER_FISCAL_STATUS_INVOICED,
        ORDER_FISCAL_STATUS_CANCELLED,
    }
)

# --- Líneas de pedido (Etapa 7) ---
ORDER_LINE_STATUS_PENDING = 'pending'
ORDER_LINE_STATUS_IN_PROGRESS = 'in_progress'
ORDER_LINE_STATUS_READY = 'ready'
ORDER_LINE_STATUS_SERVED = 'served'
ORDER_LINE_STATUS_CANCELLED = 'cancelled'

ORDER_LINE_STATUSES = frozenset(
    {
        ORDER_LINE_STATUS_PENDING,
        ORDER_LINE_STATUS_IN_PROGRESS,
        ORDER_LINE_STATUS_READY,
        ORDER_LINE_STATUS_SERVED,
        ORDER_LINE_STATUS_CANCELLED,
    }
)

ORDER_STATUSES = frozenset(
    {
        ORDER_STATUS_DRAFT,
        ORDER_STATUS_CONFIRMED,
        ORDER_STATUS_IN_PROGRESS,
        ORDER_STATUS_READY,
        ORDER_STATUS_DELIVERED,
        ORDER_STATUS_CANCELLED,
        ORDER_STATUS_REFUNDED,
    }
)

ORDER_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    ORDER_STATUS_DRAFT: frozenset({ORDER_STATUS_CONFIRMED, ORDER_STATUS_CANCELLED}),
    ORDER_STATUS_CONFIRMED: frozenset(
        {ORDER_STATUS_IN_PROGRESS, ORDER_STATUS_CANCELLED, ORDER_STATUS_REFUNDED}
    ),
    ORDER_STATUS_IN_PROGRESS: frozenset(
        {ORDER_STATUS_READY, ORDER_STATUS_CANCELLED, ORDER_STATUS_REFUNDED}
    ),
    ORDER_STATUS_READY: frozenset(
        {ORDER_STATUS_DELIVERED, ORDER_STATUS_CANCELLED, ORDER_STATUS_REFUNDED}
    ),
    ORDER_STATUS_DELIVERED: frozenset({ORDER_STATUS_REFUNDED}),
    ORDER_STATUS_CANCELLED: frozenset(),
    ORDER_STATUS_REFUNDED: frozenset(),
}

# --- Pago ---
PAYMENT_STATUS_PENDING = 'pending'
PAYMENT_STATUS_AUTHORIZED = 'authorized'
PAYMENT_STATUS_CAPTURED = 'captured'
PAYMENT_STATUS_FAILED = 'failed'
PAYMENT_STATUS_REFUNDED = 'refunded'
PAYMENT_STATUS_PARTIAL_REFUND = 'partial_refund'

PAYMENT_STATUSES = frozenset(
    {
        PAYMENT_STATUS_PENDING,
        PAYMENT_STATUS_AUTHORIZED,
        PAYMENT_STATUS_CAPTURED,
        PAYMENT_STATUS_FAILED,
        PAYMENT_STATUS_REFUNDED,
        PAYMENT_STATUS_PARTIAL_REFUND,
    }
)

PAYMENT_TYPE_CASH = 'cash'
PAYMENT_TYPE_CARD = 'card'
PAYMENT_TYPE_TRANSFER = 'transfer'
PAYMENT_TYPE_WALLET = 'wallet'
PAYMENT_TYPE_CREDIT = 'credit'
PAYMENT_TYPE_OTHER = 'other'

PAYMENT_TYPES = frozenset(
    {
        PAYMENT_TYPE_CASH,
        PAYMENT_TYPE_CARD,
        PAYMENT_TYPE_TRANSFER,
        PAYMENT_TYPE_WALLET,
        PAYMENT_TYPE_CREDIT,
        PAYMENT_TYPE_OTHER,
    }
)

# --- Factura ---
INVOICE_KIND_FISCAL = 'fiscal'
INVOICE_KIND_NON_FISCAL = 'non_fiscal'
INVOICE_KIND_PROFORMA = 'proforma'

INVOICE_KINDS = frozenset({INVOICE_KIND_FISCAL, INVOICE_KIND_NON_FISCAL, INVOICE_KIND_PROFORMA})

INVOICE_STATUS_DRAFT = 'draft'
INVOICE_STATUS_POSTED = 'posted'
INVOICE_STATUS_PARTIAL = 'partial'
INVOICE_STATUS_PAID = 'paid'
INVOICE_STATUS_CANCELLED = 'cancelled'

INVOICE_STATUSES = frozenset(
    {
        INVOICE_STATUS_DRAFT,
        INVOICE_STATUS_POSTED,
        INVOICE_STATUS_PARTIAL,
        INVOICE_STATUS_PAID,
        INVOICE_STATUS_CANCELLED,
    }
)

# --- Entrega ---
DELIVERY_STATUS_PENDING = 'pending'
DELIVERY_STATUS_PARTIAL = 'partial'
DELIVERY_STATUS_COMPLETED = 'completed'
DELIVERY_STATUS_CANCELLED = 'cancelled'

DELIVERY_STATUSES = frozenset(
    {
        DELIVERY_STATUS_PENDING,
        DELIVERY_STATUS_PARTIAL,
        DELIVERY_STATUS_COMPLETED,
        DELIVERY_STATUS_CANCELLED,
    }
)

# --- Caja ---
CASH_SHIFT_OPEN = 'open'
CASH_SHIFT_CLOSED = 'closed'
CASH_SHIFT_RECONCILING = 'reconciling'

CASH_SHIFT_STATUSES = frozenset({CASH_SHIFT_OPEN, CASH_SHIFT_CLOSED, CASH_SHIFT_RECONCILING})

CASH_MOVEMENT_SALE_CASH = 'sale_cash'
CASH_MOVEMENT_REFUND_CASH = 'refund_cash'
CASH_MOVEMENT_CASH_IN = 'cash_in'
CASH_MOVEMENT_CASH_OUT = 'cash_out'

CASH_MOVEMENT_TYPES = frozenset(
    {
        CASH_MOVEMENT_SALE_CASH,
        CASH_MOVEMENT_REFUND_CASH,
        CASH_MOVEMENT_CASH_IN,
        CASH_MOVEMENT_CASH_OUT,
    }
)

# --- POS ---
POS_TERMINAL_ACTIVE = 'active'
POS_TERMINAL_INACTIVE = 'inactive'
POS_TERMINAL_MAINTENANCE = 'maintenance'

POS_TERMINAL_STATUSES = frozenset(
    {POS_TERMINAL_ACTIVE, POS_TERMINAL_INACTIVE, POS_TERMINAL_MAINTENANCE}
)

# --- Inventario (Etapa 8 — dominio 6.5) ---
INVENTORY_POLICY_NONE = 'none'
INVENTORY_POLICY_RETAIL_STANDARD = 'retail_standard'
INVENTORY_POLICY_DISPATCH_REQUIRED = 'dispatch_required'
INVENTORY_POLICY_CONSIGNMENT = 'consignment'

INVENTORY_POLICIES = frozenset(
    {
        INVENTORY_POLICY_NONE,
        INVENTORY_POLICY_RETAIL_STANDARD,
        INVENTORY_POLICY_DISPATCH_REQUIRED,
        INVENTORY_POLICY_CONSIGNMENT,
    }
)

DEFAULT_INVENTORY_POLICY = INVENTORY_POLICY_RETAIL_STANDARD


def normalize_inventory_policy(value: str | None) -> str:
    raw = (value or '').strip().lower()
    if raw in INVENTORY_POLICIES:
        return raw
    return DEFAULT_INVENTORY_POLICY


def inventory_policy_reserves_on_confirmed(policy: str) -> bool:
    p = normalize_inventory_policy(policy)
    return p in {INVENTORY_POLICY_RETAIL_STANDARD, INVENTORY_POLICY_DISPATCH_REQUIRED}


def inventory_policy_deducts_on_paid(policy: str) -> bool:
    return normalize_inventory_policy(policy) == INVENTORY_POLICY_RETAIL_STANDARD


def inventory_policy_deducts_on_delivered(policy: str) -> bool:
    p = normalize_inventory_policy(policy)
    return p in {INVENTORY_POLICY_DISPATCH_REQUIRED, INVENTORY_POLICY_CONSIGNMENT}


# --- Stock ledger (Etapa 7 slice 14) ---
STOCK_MOVEMENT_RESERVE = 'reserve'
STOCK_MOVEMENT_RELEASE = 'release'
STOCK_MOVEMENT_DEDUCT = 'deduct'
STOCK_MOVEMENT_RETURN = 'return'
STOCK_MOVEMENT_ADJUST = 'adjust'

STOCK_MOVEMENT_TYPES = frozenset(
    {
        STOCK_MOVEMENT_RESERVE,
        STOCK_MOVEMENT_RELEASE,
        STOCK_MOVEMENT_DEDUCT,
        STOCK_MOVEMENT_RETURN,
        STOCK_MOVEMENT_ADJUST,
    }
)


def can_transition_order_status(current: str, target: str) -> bool:
    cur = (current or '').strip().lower()
    tgt = (target or '').strip().lower()
    if cur not in ORDER_STATUSES or tgt not in ORDER_STATUSES:
        return False
    return tgt in ORDER_STATUS_TRANSITIONS.get(cur, frozenset())


def compute_order_payment_status(amount_paid: float, grand_total: float) -> str:
    paid = round(float(amount_paid or 0), 2)
    total = round(float(grand_total or 0), 2)
    if paid <= 0:
        return ORDER_PAYMENT_STATUS_UNPAID
    if paid < total:
        return ORDER_PAYMENT_STATUS_PARTIAL
    if paid == total:
        return ORDER_PAYMENT_STATUS_PAID
    return ORDER_PAYMENT_STATUS_OVERPAID
