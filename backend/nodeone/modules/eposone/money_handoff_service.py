"""ADR-EN1-EP1 — reportar / confirmar / revertir entrega de dinero a Caja Central."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from models.eposone_ops_closure import EposoneMoneyHandoff, EposoneOpsAuditEvent
from nodeone.core.commerce.order import OrderValidationError
from nodeone.modules.eposone.ops_lifecycle import (
    CLOSE_TEST_PHRASE,
    EVENT_TEST_PERIOD_CLOSED,
    HANDOFF_CONFIRMED,
    HANDOFF_PENDING,
    HANDOFF_REVERSED,
    MONEY_HANDOFF_CHAIN,
    OPS_OPERATIONAL,
    OPS_TEST,
    catalog_sync_status,
    normalize_money_handoff_mode,
    normalize_ops_lifecycle,
    resolve_money_handoff_mode,
    resolve_ops_lifecycle,
    resolve_test_session_id,
)


class MoneyHandoffError(OrderValidationError):
    pass


def runtime_contract(organization_id: int) -> dict[str, Any]:
    from nodeone.modules.eposone.cash_operation_mode import resolve_cash_operation_mode
    from nodeone.modules.eposone.ops_lifecycle import ensure_test_session_id
    from nodeone.modules.eposone.settings_service import EposoneSettingsService

    oid = int(organization_id)
    dto = EposoneSettingsService.get_settings(oid)
    life = normalize_ops_lifecycle(getattr(dto, 'operational_lifecycle', None))
    session = (getattr(dto, 'test_session_id', None) or '').strip() or None
    if life != OPS_OPERATIONAL and not session:
        session = ensure_test_session_id(oid)
    return {
        'money_handoff_mode': normalize_money_handoff_mode(getattr(dto, 'money_handoff_mode', None)),
        'cash_operation_mode': resolve_cash_operation_mode(oid),
        'operational_lifecycle': life,
        'test_session_id': session,
        'is_test': life != OPS_OPERATIONAL,
        'allow_test_purge': life == OPS_TEST,
    }


def _append_ops_audit(
    organization_id: int,
    event_type: str,
    *,
    actor_user_id: int | None,
    actor_label: str,
    payload: dict[str, Any],
) -> None:
    from app import db

    db.session.add(
        EposoneOpsAuditEvent(
            organization_id=int(organization_id),
            event_type=str(event_type)[:64],
            authorized_by_user_id=actor_user_id,
            authorized_by_label=(actor_label or '')[:160],
            payload_json=json.dumps(payload, default=str),
        )
    )


def _parse_date_range(from_date: str | None, to_date: str | None) -> tuple[datetime | None, datetime | None]:
    from datetime import timedelta

    start = None
    end = None
    raw_from = (from_date or '').strip()
    raw_to = (to_date or '').strip()
    if raw_from:
        try:
            start = datetime.strptime(raw_from[:10], '%Y-%m-%d')
        except ValueError:
            start = None
    if raw_to:
        try:
            end = datetime.strptime(raw_to[:10], '%Y-%m-%d') + timedelta(days=1)
        except ValueError:
            end = None
    return start, end


def _post_central_till_movement(row: EposoneMoneyHandoff, *, inbound: bool) -> None:
    """Caja Central suma/resta solo lo RECIBIDO, nunca un PENDING_HANDOFF."""
    ref = (row.register_ref or '').strip()
    amt = round(float(row.received_amount or 0), 2)
    if not ref or amt <= 0:
        return
    try:
        from nodeone.core.commerce.cash import CashRegisterService
        from nodeone.core.commerce.constants import CASH_MOVEMENT_CASH_IN, CASH_MOVEMENT_CASH_OUT

        shift = CashRegisterService.get_open_shift(int(row.organization_id), ref)
        if shift is None:
            return
        CashRegisterService.record_movement(
            int(row.organization_id),
            int(shift.id),
            CASH_MOVEMENT_CASH_IN if inbound else CASH_MOVEMENT_CASH_OUT,
            amt,
            notes=f'handoff:{int(row.id)}:{row.status}',
            cashier_contact_id=row.cashier_contact_id,
        )
    except Exception:
        return


def _row_to_dict(row: EposoneMoneyHandoff) -> dict[str, Any]:
    refs = []
    if row.order_refs_json:
        try:
            parsed = json.loads(row.order_refs_json)
            if isinstance(parsed, list):
                refs = [str(x) for x in parsed]
        except (TypeError, ValueError, json.JSONDecodeError):
            refs = []
    expected = float(row.expected_amount or 0)
    received = None if row.received_amount is None else float(row.received_amount)
    diff = None if row.difference_amount is None else float(row.difference_amount)
    return {
        'id': int(row.id),
        'organization_id': int(row.organization_id),
        'client_handoff_id': str(row.client_handoff_id),
        'cashier_contact_id': row.cashier_contact_id,
        'cashier_name': row.cashier_name,
        'shift_id': row.shift_id,
        'register_ref': row.register_ref,
        'expected_amount': expected,
        'received_amount': received,
        'difference_amount': diff,
        'other_tender_amount': float(row.other_tender_amount or 0),
        'order_refs': refs,
        'status': str(row.status),
        'received_by_label': row.received_by_label,
        'received_at': row.received_at.isoformat() if row.received_at else None,
        'reversed_by_label': row.reversed_by_label,
        'reversed_at': row.reversed_at.isoformat() if row.reversed_at else None,
        'reverse_reason': row.reverse_reason,
        'is_test': bool(row.is_test),
        'test_session_id': row.test_session_id,
        'created_at': row.created_at.isoformat() if row.created_at else None,
    }


class MoneyHandoffService:
    @staticmethod
    def upsert_from_device(organization_id: int, body: dict[str, Any], *, is_test: bool, test_session_id: str | None) -> dict[str, Any]:
        from app import db

        oid = int(organization_id)
        client_id = str(body.get('client_handoff_id') or body.get('id') or '').strip()
        if not client_id:
            raise MoneyHandoffError('client_handoff_id_required')
        expected = float(body.get('expected_amount') or body.get('cash_amount') or 0)
        if expected < 0:
            raise MoneyHandoffError('expected_amount_invalid')
        refs = body.get('order_refs') or body.get('orders') or []
        if not isinstance(refs, list):
            refs = []
        row = EposoneMoneyHandoff.query.filter_by(organization_id=oid, client_handoff_id=client_id[:80]).first()
        if row is None:
            row = EposoneMoneyHandoff(
                organization_id=oid,
                client_handoff_id=client_id[:80],
                status=HANDOFF_PENDING,
            )
            db.session.add(row)
        elif str(row.status) == HANDOFF_CONFIRMED:
            return _row_to_dict(row)
        row.cashier_contact_id = body.get('cashier_contact_id') or None
        row.cashier_name = (str(body.get('cashier_name') or '').strip() or None)
        row.shift_id = body.get('shift_id') or None
        row.register_ref = (str(body.get('register_ref') or '').strip() or None)
        row.expected_amount = expected
        row.other_tender_amount = float(body.get('other_tender_amount') or 0)
        row.order_refs_json = json.dumps([str(x) for x in refs][:200])
        row.is_test = bool(is_test or body.get('is_test'))
        row.test_session_id = (str(body.get('test_session_id') or test_session_id or '').strip() or None)
        if str(row.status) not in (HANDOFF_CONFIRMED, HANDOFF_REVERSED):
            row.status = HANDOFF_PENDING
        db.session.commit()
        return _row_to_dict(row)

    @staticmethod
    def list_handoffs(
        organization_id: int,
        *,
        status: str | None = None,
        cashier_contact_id: int | None = None,
        shift_id: int | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        q = EposoneMoneyHandoff.query.filter_by(organization_id=int(organization_id))
        if status:
            q = q.filter_by(status=str(status).strip().upper())
        if cashier_contact_id:
            q = q.filter_by(cashier_contact_id=int(cashier_contact_id))
        if shift_id:
            q = q.filter_by(shift_id=int(shift_id))
        start, end = _parse_date_range(from_date, to_date)
        if start is not None:
            q = q.filter(EposoneMoneyHandoff.created_at >= start)
        if end is not None:
            q = q.filter(EposoneMoneyHandoff.created_at < end)
        rows = q.order_by(EposoneMoneyHandoff.id.desc()).limit(max(1, min(int(limit), 300))).all()
        return [_row_to_dict(r) for r in rows]

    @staticmethod
    def summary(organization_id: int) -> dict[str, Any]:
        from sqlalchemy import func

        oid = int(organization_id)
        pending = (
            EposoneMoneyHandoff.query.filter_by(organization_id=oid, status=HANDOFF_PENDING)
            .with_entities(func.coalesce(func.sum(EposoneMoneyHandoff.expected_amount), 0))
            .scalar()
        )
        confirmed = (
            EposoneMoneyHandoff.query.filter_by(organization_id=oid, status=HANDOFF_CONFIRMED)
            .with_entities(func.coalesce(func.sum(EposoneMoneyHandoff.received_amount), 0))
            .scalar()
        )
        return {
            'pending_handoff_expected': float(pending or 0),
            'confirmed_received': float(confirmed or 0),
            'mode': resolve_money_handoff_mode(oid),
        }

    @staticmethod
    def confirm(
        organization_id: int,
        handoff_id: int,
        *,
        received_amount: float,
        actor_user_id: int | None,
        actor_label: str,
    ) -> dict[str, Any]:
        from app import db

        row = EposoneMoneyHandoff.query.filter_by(
            organization_id=int(organization_id), id=int(handoff_id)
        ).first()
        if row is None:
            raise MoneyHandoffError('handoff_not_found')
        if str(row.status) == HANDOFF_CONFIRMED:
            return _row_to_dict(row)
        if str(row.status) == HANDOFF_REVERSED:
            raise MoneyHandoffError('handoff_reversed')
        recv = round(float(received_amount), 2)
        if recv < 0:
            raise MoneyHandoffError('received_amount_invalid')
        expected = float(row.expected_amount or 0)
        row.received_amount = recv
        row.difference_amount = round(recv - expected, 2)
        row.status = HANDOFF_CONFIRMED
        row.received_by_user_id = actor_user_id
        row.received_by_label = (actor_label or '')[:160]
        row.received_at = datetime.utcnow()
        _append_ops_audit(
            int(organization_id),
            'MONEY_HANDOFF_CONFIRMED',
            actor_user_id=actor_user_id,
            actor_label=actor_label,
            payload={
                'handoff_id': int(row.id),
                'client_handoff_id': row.client_handoff_id,
                'cashier_name': row.cashier_name,
                'shift_id': row.shift_id,
                'expected_amount': expected,
                'received_amount': recv,
                'difference_amount': float(row.difference_amount or 0),
                'previous_status': HANDOFF_PENDING,
                'status': HANDOFF_CONFIRMED,
            },
        )
        db.session.commit()
        _post_central_till_movement(row, inbound=True)
        return _row_to_dict(row)

    @staticmethod
    def reverse(
        organization_id: int,
        handoff_id: int,
        *,
        reason: str,
        actor_user_id: int | None,
        actor_label: str,
    ) -> dict[str, Any]:
        from app import db

        why = (reason or '').strip()
        if not why:
            raise MoneyHandoffError('reverse_reason_required')
        row = EposoneMoneyHandoff.query.filter_by(
            organization_id=int(organization_id), id=int(handoff_id)
        ).first()
        if row is None:
            raise MoneyHandoffError('handoff_not_found')
        if str(row.status) != HANDOFF_CONFIRMED:
            raise MoneyHandoffError('handoff_not_confirmed')
        row.status = HANDOFF_REVERSED
        row.reversed_by_user_id = actor_user_id
        row.reversed_by_label = (actor_label or '')[:160]
        row.reversed_at = datetime.utcnow()
        row.reverse_reason = why[:400]
        _append_ops_audit(
            int(organization_id),
            'MONEY_HANDOFF_REVERSED',
            actor_user_id=actor_user_id,
            actor_label=actor_label,
            payload={
                'handoff_id': int(row.id),
                'client_handoff_id': row.client_handoff_id,
                'reason': why[:400],
                'expected_amount': float(row.expected_amount or 0),
                'received_amount': None if row.received_amount is None else float(row.received_amount),
                'previous_status': HANDOFF_CONFIRMED,
                'status': HANDOFF_REVERSED,
            },
        )
        db.session.commit()
        _post_central_till_movement(row, inbound=False)
        return _row_to_dict(row)


def _count_test_pos_payments(organization_id: int) -> int:
    from models.eposone_order import EposoneOrder, EposoneOrderPayment

    oid = int(organization_id)
    if not hasattr(EposoneOrder, 'is_test'):
        return 0
    return (
        EposoneOrderPayment.query.join(EposoneOrder, EposoneOrderPayment.order_id == EposoneOrder.id)
        .filter(EposoneOrder.organization_id == oid, EposoneOrder.is_test.is_(True))
        .count()
    )


def preview_test_purge(organization_id: int) -> dict[str, Any]:
    from models.commercial_core import CoreCashShift, CoreCommercialOrder, CoreStockMovement
    from models.eposone_order import EposoneOrder

    oid = int(organization_id)
    life = resolve_ops_lifecycle(oid)
    return {
        'operational_lifecycle': life,
        'test_session_id': resolve_test_session_id(oid),
        'allow': life == OPS_TEST,
        'confirm_phrase': CLOSE_TEST_PHRASE,
        'counts': {
            'orders': EposoneOrder.query.filter_by(organization_id=oid, is_test=True).count()
            if hasattr(EposoneOrder, 'is_test')
            else 0,
            'payments': _count_test_pos_payments(oid),
            'commercial_orders': CoreCommercialOrder.query.filter_by(organization_id=oid, is_test=True).count()
            if hasattr(CoreCommercialOrder, 'is_test')
            else 0,
            'shifts': CoreCashShift.query.filter_by(organization_id=oid, is_test=True).count()
            if hasattr(CoreCashShift, 'is_test')
            else 0,
            'stock_movements': CoreStockMovement.query.filter_by(organization_id=oid, is_test=True).count()
            if hasattr(CoreStockMovement, 'is_test')
            else 0,
            'money_handoffs': EposoneMoneyHandoff.query.filter_by(organization_id=oid, is_test=True).count(),
        },
        'kept': [
            'organization',
            'tenant',
            'users',
            'roles',
            'products',
            'categories',
            'terminals',
            'printers',
            'settings',
            'money_handoff_mode',
            'licenses',
        ],
    }


def _reverse_test_stock_and_delete(organization_id: int) -> int:
    """Deshace el efecto TEST sobre balances y borra movimientos TEST (no cascada ciega)."""
    from app import db
    from models.commercial_core import CoreStockBalance, CoreStockMovement
    from nodeone.core.commerce.constants import (
        STOCK_MOVEMENT_ADJUST,
        STOCK_MOVEMENT_DEDUCT,
        STOCK_MOVEMENT_RELEASE,
        STOCK_MOVEMENT_RESERVE,
        STOCK_MOVEMENT_RETURN,
    )

    oid = int(organization_id)
    if not hasattr(CoreStockMovement, 'is_test'):
        return 0
    rows = (
        CoreStockMovement.query.filter_by(organization_id=oid, is_test=True)
        .order_by(CoreStockMovement.id.desc())
        .all()
    )
    for mov in rows:
        bal = CoreStockBalance.query.filter_by(
            organization_id=oid,
            warehouse_org_unit_id=int(mov.warehouse_org_unit_id),
            product_ref=str(mov.product_ref),
        ).first()
        if bal is not None:
            qty = float(mov.quantity or 0)
            mt = str(mov.movement_type or '')
            on_hand = float(bal.quantity_on_hand or 0)
            reserved = float(bal.quantity_reserved or 0)
            if mt == STOCK_MOVEMENT_DEDUCT:
                bal.quantity_on_hand = round(on_hand + qty, 4)
            elif mt == STOCK_MOVEMENT_RETURN:
                bal.quantity_on_hand = round(on_hand - qty, 4)
            elif mt == STOCK_MOVEMENT_ADJUST:
                bal.quantity_on_hand = round(on_hand - qty, 4)
            elif mt == STOCK_MOVEMENT_RESERVE:
                bal.quantity_reserved = round(max(0.0, reserved - qty), 4)
            elif mt == STOCK_MOVEMENT_RELEASE:
                bal.quantity_reserved = round(reserved + qty, 4)
        db.session.delete(mov)
    return len(rows)


def _del_test_rows(model, organization_id: int) -> int:
    if not hasattr(model, 'is_test'):
        return 0
    q = model.query.filter_by(organization_id=int(organization_id), is_test=True)
    n = q.count()
    q.delete(synchronize_session=False)
    return n


def close_test_period(
    organization_id: int,
    *,
    confirm_phrase: str,
    actor_user_id: int | None,
    actor_label: str,
) -> dict[str, Any]:
    from models.commercial_core import CoreCashShift, CoreCommercialOrder
    from models.eposone_order import EposoneOrder
    from nodeone.modules.eposone.settings_service import EposoneSettingsService

    oid = int(organization_id)
    if (confirm_phrase or '').strip() != CLOSE_TEST_PHRASE:
        raise MoneyHandoffError('confirm_phrase_invalid')
    life = resolve_ops_lifecycle(oid)
    if life == OPS_OPERATIONAL:
        raise MoneyHandoffError('already_operational')
    if life != OPS_TEST:
        raise MoneyHandoffError('lifecycle_not_test')

    preview = preview_test_purge(oid)
    payments_n = int((preview.get('counts') or {}).get('payments') or 0)
    # Orden: stock revertido → pedidos POS (FK CASCADE hijos) → commercial → turnos → handoffs.
    deleted = {
        'stock_movements': _reverse_test_stock_and_delete(oid),
        'orders': _del_test_rows(EposoneOrder, oid),
        'payments': payments_n,
        'commercial_orders': _del_test_rows(CoreCommercialOrder, oid),
        'shifts': _del_test_rows(CoreCashShift, oid),
        'money_handoffs': _del_test_rows(EposoneMoneyHandoff, oid),
    }
    _append_ops_audit(
        oid,
        EVENT_TEST_PERIOD_CLOSED,
        actor_user_id=actor_user_id,
        actor_label=actor_label,
        payload={
            'previous_lifecycle': OPS_TEST,
            'new_lifecycle': OPS_OPERATIONAL,
            'test_session_id': preview.get('test_session_id'),
            'deleted': deleted,
            'preview': preview.get('counts'),
            'result': 'SUCCESS',
        },
    )
    EposoneSettingsService.update_settings(
        oid,
        operational_lifecycle=OPS_OPERATIONAL,
        test_session_id='',
    )
    return {
        'ok': True,
        'event_type': EVENT_TEST_PERIOD_CLOSED,
        'deleted': deleted,
        'operational_lifecycle': OPS_OPERATIONAL,
        'result': 'SUCCESS',
        'inventory_note': 'TEST movements reversed; set inventario inicial definitivo before selling.',
    }


__all__ = [
    'MoneyHandoffError',
    'MoneyHandoffService',
    'catalog_sync_status',
    'close_test_period',
    'preview_test_purge',
    'runtime_contract',
]
