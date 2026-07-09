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
        branch_org_unit_id=int(row.branch_org_unit_id) if getattr(row, 'branch_org_unit_id', None) else None,
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
    )


def pos_terminal_to_dto(row: CorePosTerminal) -> PosTerminalDTO:
    return PosTerminalDTO(
        id=int(row.id),
        organization_id=int(row.organization_id),
        terminal_ref=str(row.terminal_ref),
        register_ref=(row.register_ref or None),
        status=str(row.status),
        device_label=(row.device_label or None),
    )
