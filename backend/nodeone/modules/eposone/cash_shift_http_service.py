"""API v1 Turnos de caja — Device Bearer (Hito cash-shift HTTP)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from models.commercial_core import CoreCashShift
from models.core_master import CoreOrgUnit
from nodeone.core.commerce.cash import CashRegisterService
from nodeone.core.commerce.constants import (
    CASH_SHIFT_CLOSED,
    CASH_SHIFT_OPEN,
    CASH_SHIFT_RECONCILING,
)
from nodeone.core.commerce.order import OrderValidationError
from nodeone.core.master.constants import ORG_UNIT_TYPE_REGISTER
from nodeone.modules.eposone.cashier_service import CashierService, CashierValidationError


class CashShiftHttpError(Exception):
    def __init__(self, code: str, *, http_status: int = 400):
        super().__init__(code)
        self.code = code
        self.http_status = int(http_status)


def _parse_iso_dt_utc_naive(raw: Any, *, field: str) -> datetime | None:
    if raw is None or raw == '':
        return None
    text = str(raw).strip()
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise CashShiftHttpError(f'{field}_invalid', http_status=400) from exc
    if dt.tzinfo is not None:
        from datetime import timezone

        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _register_meta(organization_id: int, register_ref: str) -> tuple[str, str]:
    ref = (register_ref or '').strip()
    if not ref:
        return '', ''
    unit = CoreOrgUnit.query.filter_by(
        organization_id=int(organization_id),
        unit_ref=ref,
        unit_type=ORG_UNIT_TYPE_REGISTER,
    ).first()
    name = str(getattr(unit, 'name', None) or ref)
    return ref, name


def shift_to_http_dict(row: CoreCashShift, *, include_expected: bool = False) -> dict[str, Any]:
    caja_id, caja_name = _register_meta(int(row.organization_id), str(row.register_ref))
    status = str(row.status or '')
    data: dict[str, Any] = {
        'shift_id': int(row.id),
        'shift_number': int(row.id),
        'client_shift_id': (getattr(row, 'client_shift_id', None) or None),
        'caja_id': caja_id,
        'caja_name': caja_name,
        'register_ref': str(row.register_ref),
        'cashier_contact_id': (
            int(row.cashier_contact_id) if row.cashier_contact_id is not None else None
        ),
        'cashier_name': row.cashier_name,
        'status': status,
        'opening_float': float(row.opening_balance or 0),
        'opening_balance': float(row.opening_balance or 0),
        'opened_at': row.opened_at.isoformat() + 'Z' if row.opened_at else None,
        'closed_at': row.closed_at.isoformat() + 'Z' if row.closed_at else None,
        'counted_amount': (
            float(row.counted_amount) if row.counted_amount is not None else None
        ),
        'expected_balance': (
            float(row.expected_balance) if row.expected_balance is not None else None
        ),
        'closing_balance': (
            float(row.closing_balance) if row.closing_balance is not None else None
        ),
        'cash_variance': None,
        'closed_by_cashier_contact_id': (
            int(row.closed_by_cashier_contact_id)
            if getattr(row, 'closed_by_cashier_contact_id', None) is not None
            else None
        ),
    }
    if (
        row.counted_amount is not None
        and row.expected_balance is not None
        and status in (CASH_SHIFT_RECONCILING, CASH_SHIFT_CLOSED)
    ):
        data['cash_variance'] = round(
            float(row.counted_amount) - float(row.expected_balance), 2
        )
    if include_expected and status == CASH_SHIFT_OPEN:
        data['expected_balance'] = CashRegisterService.compute_expected_balance(int(row.id))
    return data


def _device_register(device) -> str:
    ref = str(getattr(device, 'register_ref', None) or '').strip()
    if not ref:
        raise CashShiftHttpError('device_without_register', http_status=403)
    return ref


def _map_cashier_error(exc: CashierValidationError) -> CashShiftHttpError:
    code = str(exc)
    status = 404 if code == 'cashier_not_found' else 400
    if code == 'cashier_inactive':
        status = 409
    return CashShiftHttpError(code, http_status=status)


def _map_order_error(exc: OrderValidationError) -> CashShiftHttpError:
    code = str(exc)
    conflict = {
        'shift_already_open',
        'shift_not_open',
        'cash_shift_not_open',
        'shift_must_reconcile_before_close',
        'cash_shift_not_accepting_movements',
    }
    not_found = {'shift_not_found', 'cash_shift_not_found'}
    if code in not_found:
        return CashShiftHttpError(code, http_status=404)
    if code in conflict:
        return CashShiftHttpError(code, http_status=409)
    return CashShiftHttpError(code, http_status=400)


class CashShiftHttpService:
    @staticmethod
    def get_current(device) -> dict[str, Any] | None:
        oid = int(device.organization_id)
        ref = _device_register(device)
        row = (
            CoreCashShift.query.filter_by(organization_id=oid, register_ref=ref)
            .filter(CoreCashShift.status.in_((CASH_SHIFT_OPEN, CASH_SHIFT_RECONCILING)))
            .order_by(CoreCashShift.id.desc())
            .first()
        )
        if row is None:
            return None
        return shift_to_http_dict(row, include_expected=True)

    @staticmethod
    def get_shift(device, shift_id: int) -> dict[str, Any]:
        oid = int(device.organization_id)
        ref = _device_register(device)
        row = CoreCashShift.query.filter_by(
            organization_id=oid, id=int(shift_id)
        ).first()
        if row is None or str(row.register_ref) != ref:
            raise CashShiftHttpError('shift_not_found', http_status=404)
        return shift_to_http_dict(row, include_expected=(str(row.status) == CASH_SHIFT_OPEN))

    @staticmethod
    def open_shift(device, body: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """Returns (shift_dict, created). created=False ⇒ idempotent replay."""
        oid = int(device.organization_id)
        ref = _device_register(device)
        client_shift_id = str(body.get('client_shift_id') or body.get('idempotency_key') or '').strip() or None
        if client_shift_id:
            existing = CoreCashShift.query.filter_by(
                organization_id=oid, client_shift_id=client_shift_id
            ).first()
            if existing is not None:
                if str(existing.register_ref) != ref:
                    raise CashShiftHttpError('client_shift_id_conflict', http_status=409)
                return shift_to_http_dict(existing, include_expected=True), False

        try:
            cashier = CashierService.require_cashier(
                oid, body.get('cashier_contact_id'), active=True
            )
        except CashierValidationError as exc:
            raise _map_cashier_error(exc) from exc

        opening = body.get('opening_float')
        if opening is None:
            opening = body.get('opening_balance', 0)
        try:
            opening_float = round(float(opening or 0), 2)
        except (TypeError, ValueError) as exc:
            raise CashShiftHttpError('opening_float_invalid', http_status=400) from exc
        if opening_float < 0:
            raise CashShiftHttpError('opening_float_invalid', http_status=400)

        cashier_name = (
            str(body.get('cashier_name') or '').strip() or str(cashier.display_name or '')
        )
        opened_at = _parse_iso_dt_utc_naive(body.get('opened_at'), field='opened_at')

        try:
            dto = CashRegisterService.open_shift(
                oid,
                register_ref=ref,
                opening_balance=opening_float,
                cashier_contact_id=int(cashier.id),
                cashier_name=cashier_name,
                source_app_id='eposone',
                opened_at=opened_at,
                client_shift_id=client_shift_id,
            )
        except OrderValidationError as exc:
            raise _map_order_error(exc) from exc

        row = CoreCashShift.query.filter_by(organization_id=oid, id=int(dto.id)).first()
        assert row is not None
        return shift_to_http_dict(row, include_expected=True), True

    @staticmethod
    def close_shift(device, shift_id: int, body: dict[str, Any]) -> dict[str, Any]:
        oid = int(device.organization_id)
        ref = _device_register(device)
        row = CoreCashShift.query.filter_by(organization_id=oid, id=int(shift_id)).first()
        if row is None or str(row.register_ref) != ref:
            raise CashShiftHttpError('shift_not_found', http_status=404)

        if str(row.status) == CASH_SHIFT_CLOSED:
            return shift_to_http_dict(row)

        try:
            cashier = CashierService.require_cashier(
                oid, body.get('cashier_contact_id'), active=False
            )
        except CashierValidationError as exc:
            raise _map_cashier_error(exc) from exc

        if 'counted_amount' in body:
            counted_raw = body.get('counted_amount')
        elif 'closing_float' in body:
            counted_raw = body.get('closing_float')
        else:
            raise CashShiftHttpError('counted_amount_required', http_status=400)
        try:
            counted = round(float(counted_raw), 2)
        except (TypeError, ValueError) as exc:
            raise CashShiftHttpError('counted_amount_invalid', http_status=400) from exc
        if counted < 0:
            raise CashShiftHttpError('counted_amount_invalid', http_status=400)

        notes = str(body.get('notes') or '').strip() or None
        closed_at = _parse_iso_dt_utc_naive(body.get('closed_at'), field='closed_at')

        try:
            CashRegisterService.close_shift_counted(
                oid,
                int(shift_id),
                counted_amount=counted,
                cashier_contact_id=int(cashier.id),
                notes=notes,
                closed_at=closed_at,
                source_app_id='eposone',
            )
        except OrderValidationError as exc:
            raise _map_order_error(exc) from exc

        row = CoreCashShift.query.filter_by(organization_id=oid, id=int(shift_id)).first()
        assert row is not None
        return shift_to_http_dict(row)
