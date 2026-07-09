"""Handlers sync offline → dominio EPosOne."""

from __future__ import annotations

from nodeone.core.commerce.order import OrderService, OrderValidationError
from nodeone.core.commerce.payment import PaymentService
from nodeone.core.sync.queue import SyncOperationDTO


def apply_eposone_sync_operation(dto: SyncOperationDTO) -> None:
    op = (dto.operation_type or '').strip().lower()
    if op == 'create_order':
        OrderService.create(int(dto.organization_id), dict(dto.payload or {}), source_app_id='eposone')
        return
    if op == 'transition_order_status':
        payload = dict(dto.payload or {})
        order_id = payload.get('order_id')
        status = (payload.get('status') or '').strip()
        if not order_id or not status:
            raise OrderValidationError('order_id_and_status_required')
        OrderService.transition_status(
            int(dto.organization_id),
            int(order_id),
            status,
            source_app_id='eposone',
            reason=payload.get('reason'),
        )
        return
    if op == 'capture_payment':
        PaymentService.capture(int(dto.organization_id), dict(dto.payload or {}), source_app_id='eposone')
        return
    if op == 'emit_fiscal':
        from nodeone.core.commerce.fiscal import CommerceFiscalService

        payload = dict(dto.payload or {})
        order_id = payload.get('order_id')
        if not order_id:
            raise OrderValidationError('order_id_required')
        CommerceFiscalService.process_pending_order(
            int(dto.organization_id),
            int(order_id),
            source_app_id='eposone',
        )
        return
    if op == 'refund_payment':
        payload = dict(dto.payload or {})
        payment_id = payload.get('payment_id')
        if not payment_id:
            raise OrderValidationError('payment_id_required')
        amount = payload.get('amount')
        PaymentService.refund(
            int(dto.organization_id),
            int(payment_id),
            amount=float(amount) if amount is not None else None,
            approval=payload,
            source_app_id='eposone',
        )
        return
    if op == 'open_cash_shift':
        from nodeone.core.commerce.cash import CashRegisterService

        payload = dict(dto.payload or {})
        CashRegisterService.open_shift(
            int(dto.organization_id),
            register_ref=str(payload.get('register_ref') or ''),
            opening_balance=float(payload.get('opening_balance') or 0),
            source_app_id='eposone',
        )
        return
    if op == 'reconcile_cash_shift':
        from nodeone.core.commerce.cash import CashRegisterService

        payload = dict(dto.payload or {})
        shift_id = payload.get('shift_id')
        if not shift_id:
            raise OrderValidationError('shift_id_required')
        CashRegisterService.begin_reconcile(
            int(dto.organization_id),
            int(shift_id),
            counted_amount=float(payload.get('counted_amount') or 0),
            source_app_id='eposone',
        )
        return
    if op == 'close_cash_shift':
        from nodeone.core.commerce.cash import CashRegisterService

        payload = dict(dto.payload or {})
        shift_id = payload.get('shift_id')
        if not shift_id:
            raise OrderValidationError('shift_id_required')
        CashRegisterService.close_shift(
            int(dto.organization_id),
            int(shift_id),
            source_app_id='eposone',
        )
        return
    if op == 'manual_cash_movement':
        from nodeone.core.commerce.cash import CashRegisterService

        payload = dict(dto.payload or {})
        shift_id = payload.get('shift_id')
        movement_type = (payload.get('movement_type') or '').strip()
        if not shift_id or not movement_type:
            raise OrderValidationError('shift_id_and_movement_type_required')
        CashRegisterService.record_manual_movement(
            int(dto.organization_id),
            int(shift_id),
            movement_type,
            float(payload.get('amount') or 0),
            notes=payload.get('notes'),
            approval=payload,
            source_app_id='eposone',
        )
        return
    if op == 'split_order':
        payload = dict(dto.payload or {})
        order_id = payload.get('order_id')
        line_indexes = payload.get('line_indexes')
        if not order_id:
            raise OrderValidationError('order_id_required')
        if not isinstance(line_indexes, list) or not line_indexes:
            raise OrderValidationError('line_indexes_required')
        OrderService.split_order(
            int(dto.organization_id),
            int(order_id),
            [int(i) for i in line_indexes],
            source_app_id='eposone',
        )
        return
    if op == 'stock_adjust':
        from nodeone.core.commerce.stock import StockService

        StockService.record_manual_adjust(
            int(dto.organization_id),
            dict(dto.payload or {}),
            source_app_id='eposone',
        )
        return
    raise OrderValidationError(f'unsupported_operation:{op}')


EPOSONE_SYNC_OPERATIONS = frozenset(
    {
        'create_order',
        'transition_order_status',
        'capture_payment',
        'refund_payment',
        'emit_fiscal',
        'open_cash_shift',
        'reconcile_cash_shift',
        'close_cash_shift',
        'manual_cash_movement',
        'split_order',
        'stock_adjust',
    }
)


def process_eposone_sync_queue(*, organization_id: int | None = None, limit: int = 50) -> int:
    from nodeone.core.sync.queue import SyncOperationService

    return SyncOperationService.process_pending(
        limit=limit,
        organization_id=organization_id,
        handler=apply_eposone_sync_operation,
    )
