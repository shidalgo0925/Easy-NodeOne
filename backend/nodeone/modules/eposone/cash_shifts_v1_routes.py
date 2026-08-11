"""API v1 Cash Shifts — Device Bearer (apertura / cierre POS)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user

from nodeone.modules.eposone.device_provisioning import (
    DeviceProvisioningError,
    DeviceProvisioningService,
)

eposone_cash_v1_bp = Blueprint(
    'eposone_cash_v1',
    __name__,
    url_prefix='/api/v1/cash',
)


def _cash_http():
    """Lazy — evita ciclo register → cash_shifts → cash_shift_http → app → register."""
    from nodeone.modules.eposone.cash_shift_http_service import (
        CashShiftHttpError,
        CashShiftHttpService,
    )

    return CashShiftHttpError, CashShiftHttpService


def _device_from_request():
    """Auth: Device Bearer (preferido) o sesión BO con terminal activo de la org."""
    auth = request.headers.get('Authorization')
    if auth and auth.strip().lower().startswith('bearer '):
        device = DeviceProvisioningService.authenticate_bearer(auth)
        DeviceProvisioningService.require_installation_ready(device)
        return device

    if getattr(current_user, 'is_authenticated', False):
        from nodeone.core.platform.runtime import resolve_organization_id
        from nodeone.core.template_context_gates import user_can_see_tenant_admin_menu
        from nodeone.modules.eposone.bo_actor import ensure_backoffice_terminal

        if not user_can_see_tenant_admin_menu(current_user):
            raise DeviceProvisioningError('forbidden', http_status=403)
        oid = resolve_organization_id()
        if oid is None:
            raise DeviceProvisioningError('organization_required', http_status=400)
        return ensure_backoffice_terminal(int(oid))

    raise DeviceProvisioningError('unauthorized', http_status=401)


def _err(exc: Exception):
    CashShiftHttpError, _ = _cash_http()
    if isinstance(exc, (DeviceProvisioningError, CashShiftHttpError)):
        return jsonify({'error': exc.code}), int(exc.http_status)
    raise exc


@eposone_cash_v1_bp.route('/shifts/current', methods=['GET'])
def cash_shift_current():
    """Turno abierto o en arqueo de la caja del device."""
    CashShiftHttpError, CashShiftHttpService = _cash_http()
    try:
        device = _device_from_request()
        shift = CashShiftHttpService.get_current(device)
        if shift is None:
            return jsonify({'shift': None})
        return jsonify({'shift': shift})
    except (DeviceProvisioningError, CashShiftHttpError) as exc:
        return _err(exc)


@eposone_cash_v1_bp.route('/shifts', methods=['POST'])
def cash_shift_open():
    """Abrir turno en la caja provisionada al device."""
    CashShiftHttpError, CashShiftHttpService = _cash_http()
    try:
        device = _device_from_request()
        body = request.get_json(silent=True) or {}
        # Header Idempotency-Key → client_shift_id si no viene en body
        hdr = (request.headers.get('Idempotency-Key') or '').strip()
        if hdr and not body.get('client_shift_id') and not body.get('idempotency_key'):
            body = dict(body)
            body['client_shift_id'] = hdr
        shift, created = CashShiftHttpService.open_shift(device, body)
        return jsonify({'shift': shift}), (201 if created else 200)
    except (DeviceProvisioningError, CashShiftHttpError) as exc:
        return _err(exc)


@eposone_cash_v1_bp.route('/shifts/<int:shift_id>', methods=['GET'])
def cash_shift_get(shift_id: int):
    CashShiftHttpError, CashShiftHttpService = _cash_http()
    try:
        device = _device_from_request()
        shift = CashShiftHttpService.get_shift(device, shift_id)
        return jsonify({'shift': shift})
    except (DeviceProvisioningError, CashShiftHttpError) as exc:
        return _err(exc)


@eposone_cash_v1_bp.route('/shifts/<int:shift_id>/close', methods=['POST'])
def cash_shift_close(shift_id: int):
    """Cierre POS en un paso (arqueo + close). Idempotente si ya closed."""
    CashShiftHttpError, CashShiftHttpService = _cash_http()
    try:
        device = _device_from_request()
        body = request.get_json(silent=True) or {}
        shift = CashShiftHttpService.close_shift(device, shift_id, body)
        return jsonify({'shift': shift})
    except (DeviceProvisioningError, CashShiftHttpError) as exc:
        return _err(exc)


@eposone_cash_v1_bp.route('/shifts/<int:shift_id>/custody/handover', methods=['POST'])
def cash_shift_custody_offer(shift_id: int):
    """ADR-036 modo B: custodio ofrece handover."""
    CashShiftHttpError, CashShiftHttpService = _cash_http()
    try:
        device = _device_from_request()
        body = request.get_json(silent=True) or {}
        shift = CashShiftHttpService.offer_handover(device, shift_id, body)
        return jsonify({'shift': shift})
    except (DeviceProvisioningError, CashShiftHttpError) as exc:
        return _err(exc)


@eposone_cash_v1_bp.route(
    '/shifts/<int:shift_id>/custody/handover/<handover_id>/accept', methods=['POST']
)
def cash_shift_custody_accept(shift_id: int, handover_id: str):
    CashShiftHttpError, CashShiftHttpService = _cash_http()
    try:
        device = _device_from_request()
        body = request.get_json(silent=True) or {}
        shift = CashShiftHttpService.accept_handover(device, shift_id, handover_id, body)
        return jsonify({'shift': shift})
    except (DeviceProvisioningError, CashShiftHttpError) as exc:
        return _err(exc)


@eposone_cash_v1_bp.route(
    '/shifts/<int:shift_id>/custody/handover/<handover_id>/reject', methods=['POST']
)
def cash_shift_custody_reject(shift_id: int, handover_id: str):
    CashShiftHttpError, CashShiftHttpService = _cash_http()
    try:
        device = _device_from_request()
        body = request.get_json(silent=True) or {}
        shift = CashShiftHttpService.reject_handover(device, shift_id, handover_id, body)
        return jsonify({'shift': shift})
    except (DeviceProvisioningError, CashShiftHttpError) as exc:
        return _err(exc)
