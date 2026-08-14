"""Handlers sync offline → dominio EPosOne."""

from __future__ import annotations

from nodeone.core.commerce.order import OrderService, OrderValidationError
from nodeone.core.commerce.payment import PaymentService
from nodeone.core.sync.queue import SyncOperationDTO

_CASHIER_OPERATIONS = frozenset(
    {
        'create_order',
        'transition_order_status',
        'capture_payment',
        'refund_payment',
        'open_cash_shift',
        'reconcile_cash_shift',
        'close_cash_shift',
        'manual_cash_movement',
        'split_order',
        'transfer_order',
    }
)


def apply_eposone_sync_operation(dto: SyncOperationDTO) -> None:
    op = (dto.operation_type or '').strip().lower()
    payload = dict(dto.payload or {})
    cashier = None
    if op in _CASHIER_OPERATIONS:
        from nodeone.modules.eposone.cashier_service import (
            CashierService,
            CashierValidationError,
        )

        try:
            cashier = CashierService.require_cashier(
                int(dto.organization_id),
                payload.get('cashier_contact_id'),
                active=(op == 'open_cash_shift'),
            )
        except CashierValidationError as exc:
            raise OrderValidationError(str(exc)) from exc
    if op == 'create_order':
        OrderService.create(int(dto.organization_id), payload, source_app_id='eposone')
        return
    if op == 'transition_order_status':
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
            cashier_contact_id=int(cashier.id),
        )
        return
    if op == 'capture_payment':
        PaymentService.capture(int(dto.organization_id), payload, source_app_id='eposone')
        return
    if op == 'emit_fiscal':
        from nodeone.core.commerce.fiscal import CommerceFiscalService

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

        CashRegisterService.open_shift(
            int(dto.organization_id),
            register_ref=str(payload.get('register_ref') or ''),
            opening_balance=float(payload.get('opening_balance') or 0),
            cashier_contact_id=int(cashier.id),
            cashier_name=str(cashier.display_name),
            source_app_id='eposone',
        )
        return
    if op == 'reconcile_cash_shift':
        from nodeone.core.commerce.cash import CashRegisterService

        shift_id = payload.get('shift_id')
        if not shift_id:
            raise OrderValidationError('shift_id_required')
        CashRegisterService.begin_reconcile(
            int(dto.organization_id),
            int(shift_id),
            counted_amount=float(payload.get('counted_amount') or 0),
            source_app_id='eposone',
            cashier_contact_id=int(cashier.id),
        )
        return
    if op == 'close_cash_shift':
        from nodeone.core.commerce.cash import CashRegisterService

        shift_id = payload.get('shift_id')
        if not shift_id:
            raise OrderValidationError('shift_id_required')
        CashRegisterService.close_shift(
            int(dto.organization_id),
            int(shift_id),
            source_app_id='eposone',
            cashier_contact_id=int(cashier.id),
        )
        return
    if op == 'manual_cash_movement':
        from nodeone.core.commerce.cash import CashRegisterService

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
            cashier_contact_id=int(cashier.id),
            source_app_id='eposone',
        )
        return
    if op == 'split_order':
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
            cashier_contact_id=int(cashier.id),
        )
        return
    if op == 'transfer_order':
        order_id = payload.get('order_id')
        if not order_id:
            raise OrderValidationError('order_id_required')
        OrderService.transfer_to_terminal(
            int(dto.organization_id),
            int(order_id),
            payload,
            source_app_id='eposone',
        )
        return
    if op == 'stock_adjust':
        from nodeone.core.platform.connected_inventory import record_connected_adjust

        record_connected_adjust(
            int(dto.organization_id),
            payload,
            source_app_id='eposone',
            source_system='EP1',
        )
        return
    if op == 'create_contact':
        from nodeone.core.services.contacts import ContactService

        if payload.get('legacy_contact_id') is not None:
            ContactService.create_with_legacy_link(int(dto.organization_id), payload)
        else:
            ContactService.create(int(dto.organization_id), payload)
        return
    if op == 'promote_legacy_contact':
        from nodeone.core.master.contact_bridge import ContactBridgeService

        legacy_contact_id = payload.get('legacy_contact_id')
        if legacy_contact_id is None:
            raise OrderValidationError('legacy_contact_id_required')
        ContactBridgeService.promote_legacy(
            int(dto.organization_id),
            int(legacy_contact_id),
            link_source=str(payload.get('link_source') or 'eposone_sync'),
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
        'transfer_order',
        'stock_adjust',
        'create_contact',
        'promote_legacy_contact',
    }
)


def process_eposone_sync_queue(*, organization_id: int | None = None, limit: int = 50) -> int:
    from nodeone.core.sync.queue import SyncOperationService

    return SyncOperationService.process_pending(
        limit=limit,
        organization_id=organization_id,
        handler=apply_eposone_sync_operation,
    )
