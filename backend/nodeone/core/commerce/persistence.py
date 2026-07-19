"""Mapeo ORM → DTOs comerciales."""

from __future__ import annotations

from models.commercial_core import (
    CoreCashShift,
    CoreCommercialOrder,
    CoreCommercialPayment,
    CorePosTerminal,
)
from nodeone.core.commerce.constants import (
    ORDER_FISCAL_STATUS_NOT_REQUIRED,
    ORDER_LINE_STATUS_PENDING,
    ORDER_PAYMENT_STATUS_UNPAID,
    PAYMENT_STATUS_CAPTURED,
)
from nodeone.core.commerce.dtos import (
    CashShiftDTO,
    OrderDTO,
    OrderLineDTO,
    PaymentDTO,
    PosTerminalDTO,
)


def order_to_dto(row: CoreCommercialOrder) -> OrderDTO:
    lines = tuple(
        OrderLineDTO(
            description=str(line.description or ''),
            quantity=float(line.quantity or 0),
            unit_price=float(line.unit_price or 0),
            line_total=float(line.line_total or 0),
            product_ref=(line.product_ref or None),
            line_status=str(line.line_status or ORDER_LINE_STATUS_PENDING),
        )
        for line in (row.lines or [])
    )
    return OrderDTO(
        id=int(row.id),
        organization_id=int(row.organization_id),
        order_ref=str(row.order_ref),
        status=str(row.operational_status),
        payment_status=str(row.payment_status or ORDER_PAYMENT_STATUS_UNPAID),
        fiscal_status=str(row.fiscal_status or ORDER_FISCAL_STATUS_NOT_REQUIRED),
        contact_id=int(row.contact_id) if row.contact_id else None,
        currency=str(row.currency or 'USD'),
        subtotal=float(row.subtotal or 0),
        tax_total=float(row.tax_total or 0),
        grand_total=float(row.grand_total or 0),
        amount_paid=float(row.amount_paid or 0),
        lines=lines,
        source_app_id=str(row.source_app_id or 'eposone'),
        discount_total=float(getattr(row, 'discount_total', 0) or 0),
        promotion_ref=(str(row.promotion_ref).strip() if getattr(row, 'promotion_ref', None) else None),
        branch_org_unit_id=int(row.branch_org_unit_id) if getattr(row, 'branch_org_unit_id', None) else None,
        parent_order_id=int(row.parent_order_id) if getattr(row, 'parent_order_id', None) else None,
        pos_terminal_id=int(row.pos_terminal_id) if getattr(row, 'pos_terminal_id', None) else None,
        cashier_contact_id=(
            int(row.cashier_contact_id)
            if getattr(row, 'cashier_contact_id', None) is not None
            else None
        ),
        created_at=row.created_at,
    )


def payment_to_dto(row: CoreCommercialPayment, *, order_ref: str) -> PaymentDTO:
    return PaymentDTO(
        id=int(row.id),
        organization_id=int(row.organization_id),
        payment_ref=str(row.payment_ref),
        status=str(row.status or PAYMENT_STATUS_CAPTURED),
        payment_type=str(row.payment_type or 'cash'),
        amount=float(row.amount or 0),
        refunded_amount=float(getattr(row, 'refunded_amount', 0) or 0),
        currency=str(row.currency or 'USD'),
        order_ref=order_ref,
        cashier_contact_id=(
            int(row.cashier_contact_id)
            if getattr(row, 'cashier_contact_id', None) is not None
            else None
        ),
        refunded_by_cashier_contact_id=(
            int(row.refunded_by_cashier_contact_id)
            if getattr(row, 'refunded_by_cashier_contact_id', None) is not None
            else None
        ),
        captured_at=row.captured_at,
    )


def cash_shift_to_dto(row: CoreCashShift, *, include_variance: bool = True) -> CashShiftDTO:
    counted = float(row.counted_amount) if row.counted_amount is not None else None
    expected = float(row.expected_balance) if row.expected_balance is not None else None
    variance = None
    if include_variance and counted is not None and expected is not None:
        variance = round(counted - expected, 2)
    return CashShiftDTO(
        id=int(row.id),
        organization_id=int(row.organization_id),
        register_ref=str(row.register_ref),
        status=str(row.status),
        opened_at=row.opened_at,
        closed_at=row.closed_at,
        opening_balance=float(row.opening_balance or 0),
        closing_balance=float(row.closing_balance) if row.closing_balance is not None else None,
        counted_amount=counted,
        expected_balance=expected if include_variance else None,
        cash_variance=variance,
        cashier_contact_id=(
            int(row.cashier_contact_id)
            if getattr(row, 'cashier_contact_id', None) is not None
            else None
        ),
        cashier_name=(getattr(row, 'cashier_name', None) or None),
    )


def pos_terminal_to_dto(row: CorePosTerminal) -> PosTerminalDTO:
    return PosTerminalDTO(
        id=int(row.id),
        organization_id=int(row.organization_id),
        terminal_ref=str(row.terminal_ref),
        register_ref=(row.register_ref or None),
        status=str(row.status),
        device_label=(row.device_label or None),
        profile=str(getattr(row, 'profile', None) or 'fixed'),
        platform=(getattr(row, 'platform', None) or None),
        device_model=(getattr(row, 'device_model', None) or None),
        app_version=(getattr(row, 'app_version', None) or None),
        android_version=(getattr(row, 'android_version', None) or None),
        branch_ref=(getattr(row, 'branch_ref', None) or None),
        pos_ref=(getattr(row, 'pos_ref', None) or None),
        sync_enabled=bool(getattr(row, 'sync_enabled', True)),
        last_seen_at=getattr(row, 'last_seen_at', None),
        created_at=getattr(row, 'created_at', None),
        config_version=int(getattr(row, 'config_version', 1) or 1),
    )
