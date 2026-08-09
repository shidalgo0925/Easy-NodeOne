"""Corrección de cierre de turno (BO supervisor) — ADR-009.

Permite ajustar cajero, fondo de apertura, efectivo contado, ajustes de
tesorería y «recibido declarado» por método sin reescribir pagos OD.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from models.commercial_core import CoreCashMovement, CoreCashShift
from nodeone.core.commerce.constants import (
    CASH_MOVEMENT_CASH_IN,
    CASH_MOVEMENT_CASH_OUT,
    CASH_SHIFT_CLOSED,
    CASH_SHIFT_OPEN,
    CASH_SHIFT_RECONCILING,
)
from nodeone.core.commerce.order import OrderValidationError
from nodeone.modules.eposone.shift_close_service import (
    _money,
    cash_expected_for_shift,
)


def _parse_corrections(raw: str | None) -> list[dict[str, Any]]:
    if not (raw or '').strip():
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def list_shift_corrections(shift: CoreCashShift) -> list[dict[str, Any]]:
    return _parse_corrections(getattr(shift, 'correction_json', None))


def apply_shift_close_correction(
    organization_id: int,
    shift_id: int,
    *,
    actor_user_id: int | None,
    reason: str,
    cashier_contact_id: int | None = None,
    opening_balance: float | None = None,
    counted_amount: float | None = None,
    adjustment_type: str | None = None,
    adjustment_amount: float | None = None,
    declared_methods: dict[str, float] | None = None,
    source_app_id: str = 'eposone',
) -> CoreCashShift:
    """Aplica corrección a un turno cerrado (o en arqueo).

    - No borra pagos Order Domain.
    - Recalcula expected_balance desde efectivo (apertura + ventas cash + movimientos).
    - Guarda bitácora en correction_json.
    """
    from app import db
    from nodeone.modules.eposone.cashier_service import CashierService

    reason_clean = (reason or '').strip()
    if len(reason_clean) < 5:
        raise OrderValidationError('correction_reason_required')

    shift = CoreCashShift.query.filter_by(
        organization_id=int(organization_id), id=int(shift_id)
    ).first()
    if shift is None:
        raise OrderValidationError('shift_not_found')
    status = str(shift.status or '')
    if status not in (CASH_SHIFT_CLOSED, CASH_SHIFT_RECONCILING, CASH_SHIFT_OPEN):
        raise OrderValidationError('shift_not_correctable')

    previous = {
        'cashier_contact_id': shift.cashier_contact_id,
        'cashier_name': shift.cashier_name,
        'opening_balance': _money(shift.opening_balance),
        'counted_amount': (
            _money(shift.counted_amount) if shift.counted_amount is not None else None
        ),
        'expected_balance': (
            _money(shift.expected_balance) if shift.expected_balance is not None else None
        ),
        'closing_balance': (
            _money(shift.closing_balance) if shift.closing_balance is not None else None
        ),
        'status': status,
    }

    cashier_name = shift.cashier_name
    if cashier_contact_id is not None:
        cid = int(cashier_contact_id)
        if cid <= 0:
            shift.cashier_contact_id = None
            cashier_name = None
            shift.cashier_name = None
        else:
            cashier = CashierService.get(int(organization_id), cid)
            if cashier is None:
                raise OrderValidationError('cashier_contact_id_invalid')
            shift.cashier_contact_id = int(cashier.id)
            cashier_name = str(cashier.display_name or '')
            shift.cashier_name = cashier_name
            shift.cashier_changed_at = datetime.utcnow()
            if actor_user_id:
                shift.cashier_changed_by_user_id = int(actor_user_id)
            if status == CASH_SHIFT_CLOSED:
                shift.closed_by_cashier_contact_id = int(cashier.id)

    if opening_balance is not None:
        ob = _money(opening_balance)
        if ob < 0:
            raise OrderValidationError('opening_balance_invalid')
        shift.opening_balance = ob

    adj_type = (adjustment_type or '').strip().lower() or None
    adj_amt = _money(adjustment_amount) if adjustment_amount is not None else 0.0
    if adj_amt > 0.009:
        if adj_type not in (CASH_MOVEMENT_CASH_IN, CASH_MOVEMENT_CASH_OUT):
            raise OrderValidationError('invalid_manual_cash_movement')
        # Permitido también en cerrado: corrección supervisor (no usa record_movement).
        db.session.add(
            CoreCashMovement(
                organization_id=int(organization_id),
                shift_id=int(shift.id),
                movement_type=adj_type,
                amount=adj_amt,
                cashier_contact_id=shift.cashier_contact_id,
                notes=f'Corrección de cierre: {reason_clean[:180]}',
            )
        )

    cash = cash_expected_for_shift(shift, include_opening=True)
    expected = _money(cash['expected'])
    shift.expected_balance = expected

    if counted_amount is not None:
        counted = _money(counted_amount)
        if counted < 0:
            raise OrderValidationError('counted_amount_invalid')
        shift.counted_amount = counted
    elif shift.counted_amount is None and status in (
        CASH_SHIFT_CLOSED,
        CASH_SHIFT_RECONCILING,
    ):
        shift.counted_amount = expected

    if shift.counted_amount is not None:
        shift.closing_balance = _money(shift.counted_amount)

    declared_clean: dict[str, float] = {}
    if declared_methods:
        for key, raw_amt in declared_methods.items():
            k = str(key or '').strip().lower()
            if not k:
                continue
            try:
                declared_clean[k] = _money(raw_amt)
            except (TypeError, ValueError):
                continue

    event = {
        'at': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'by_user_id': int(actor_user_id) if actor_user_id else None,
        'reason': reason_clean[:500],
        'source_app_id': source_app_id,
        'previous': previous,
        'after': {
            'cashier_contact_id': shift.cashier_contact_id,
            'cashier_name': shift.cashier_name,
            'opening_balance': _money(shift.opening_balance),
            'counted_amount': (
                _money(shift.counted_amount) if shift.counted_amount is not None else None
            ),
            'expected_balance': _money(shift.expected_balance),
            'closing_balance': (
                _money(shift.closing_balance) if shift.closing_balance is not None else None
            ),
        },
        'adjustment': (
            {'type': adj_type, 'amount': adj_amt} if adj_amt > 0.009 else None
        ),
        'declared_methods': declared_clean or None,
    }
    history = _parse_corrections(getattr(shift, 'correction_json', None))
    history.append(event)
    shift.correction_json = json.dumps(history, ensure_ascii=False)

    db.session.add(shift)
    db.session.commit()
    return shift
