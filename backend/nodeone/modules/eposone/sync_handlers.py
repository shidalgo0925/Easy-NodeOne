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
    if op == 'capture_payment':
        PaymentService.capture(int(dto.organization_id), dict(dto.payload or {}), source_app_id='eposone')
        return
    raise OrderValidationError(f'unsupported_operation:{op}')


def process_eposone_sync_queue(*, organization_id: int | None = None, limit: int = 50) -> int:
    from nodeone.core.sync.queue import SyncOperationService

    return SyncOperationService.process_pending(
        limit=limit,
        organization_id=organization_id,
        handler=apply_eposone_sync_operation,
    )
