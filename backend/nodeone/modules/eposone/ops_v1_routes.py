"""API v1 ADR-EN1-EP1 — runtime, money handoff, cierre TEST."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user

from nodeone.modules.eposone.device_provisioning import (
    DeviceProvisioningError,
    DeviceProvisioningService,
)
from nodeone.modules.eposone.money_handoff_service import (
    MoneyHandoffError,
    MoneyHandoffService,
    close_test_period,
    preview_test_purge,
    runtime_contract,
)
from nodeone.modules.eposone.ops_lifecycle import (
    MONEY_HANDOFF_CHAIN,
    OPS_OPERATIONAL,
    resolve_money_handoff_mode,
    resolve_ops_lifecycle,
    ensure_test_session_id,
)

eposone_ops_v1_bp = Blueprint('eposone_ops_v1', __name__, url_prefix='/api/v1/ops')


def _device_from_request():
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


def _require_session_tenant_admin():
    if not getattr(current_user, 'is_authenticated', False):
        raise DeviceProvisioningError('forbidden', http_status=403)
    from nodeone.core.template_context_gates import user_can_see_tenant_admin_menu

    if not user_can_see_tenant_admin_menu(current_user):
        raise DeviceProvisioningError('forbidden', http_status=403)


def _actor():
    from nodeone.modules.eposone.bo_actor import actor_label_from_user

    uid = int(getattr(current_user, 'id', 0) or 0) or None
    label = actor_label_from_user(current_user) if getattr(current_user, 'is_authenticated', False) else 'device'
    return uid, str(label or 'admin')


def _err(exc: Exception):
    if isinstance(exc, DeviceProvisioningError):
        return jsonify({'error': exc.code}), int(exc.http_status)
    if isinstance(exc, MoneyHandoffError):
        return jsonify({'error': str(exc)}), 400
    raise exc


@eposone_ops_v1_bp.route('/runtime', methods=['GET'])
def ops_runtime():
    try:
        device = _device_from_request()
        return jsonify({'runtime': runtime_contract(int(device.organization_id))})
    except DeviceProvisioningError as exc:
        return _err(exc)


@eposone_ops_v1_bp.route('/money-handoffs', methods=['GET'])
def money_handoffs_list():
    try:
        device = _device_from_request()
        oid = int(device.organization_id)
        status = (request.args.get('status') or '').strip() or None
        cashier = request.args.get('cashier_contact_id', type=int)
        shift_id = request.args.get('shift_id', type=int)
        from_date = (request.args.get('from') or request.args.get('from_date') or '').strip() or None
        to_date = (request.args.get('to') or request.args.get('to_date') or '').strip() or None
        items = MoneyHandoffService.list_handoffs(
            oid,
            status=status,
            cashier_contact_id=cashier,
            shift_id=shift_id,
            from_date=from_date,
            to_date=to_date,
        )
        return jsonify(
            {
                'handoffs': items,
                'summary': MoneyHandoffService.summary(oid),
                'money_handoff_mode': resolve_money_handoff_mode(oid),
            }
        )
    except DeviceProvisioningError as exc:
        return _err(exc)


@eposone_ops_v1_bp.route('/money-handoffs', methods=['POST'])
def money_handoffs_upsert():
    try:
        device = _device_from_request()
        oid = int(device.organization_id)
        if resolve_money_handoff_mode(oid) != MONEY_HANDOFF_CHAIN:
            return jsonify({'error': 'money_handoff_simple_mode'}), 409
        body = request.get_json(silent=True) or {}
        row = MoneyHandoffService.upsert_from_device(
            oid,
            body,
            is_test=resolve_ops_lifecycle(oid) != OPS_OPERATIONAL,
            test_session_id=ensure_test_session_id(oid),
        )
        return jsonify({'handoff': row}), 201
    except (DeviceProvisioningError, MoneyHandoffError) as exc:
        return _err(exc)


@eposone_ops_v1_bp.route('/money-handoffs/<int:handoff_id>/confirm', methods=['POST'])
def money_handoff_confirm(handoff_id: int):
    try:
        _require_session_tenant_admin()
        device = _device_from_request()
        body = request.get_json(silent=True) or {}
        received = body.get('received_amount', body.get('amount'))
        if received is None:
            return jsonify({'error': 'received_amount_required'}), 400
        uid, label = _actor()
        row = MoneyHandoffService.confirm(
            int(device.organization_id),
            int(handoff_id),
            received_amount=float(received),
            actor_user_id=uid,
            actor_label=label,
        )
        return jsonify({'handoff': row})
    except (DeviceProvisioningError, MoneyHandoffError) as exc:
        return _err(exc)


@eposone_ops_v1_bp.route('/money-handoffs/<int:handoff_id>/reverse', methods=['POST'])
def money_handoff_reverse(handoff_id: int):
    try:
        _require_session_tenant_admin()
        device = _device_from_request()
        body = request.get_json(silent=True) or {}
        uid, label = _actor()
        row = MoneyHandoffService.reverse(
            int(device.organization_id),
            int(handoff_id),
            reason=str(body.get('reason') or ''),
            actor_user_id=uid,
            actor_label=label,
        )
        return jsonify({'handoff': row})
    except (DeviceProvisioningError, MoneyHandoffError) as exc:
        return _err(exc)


@eposone_ops_v1_bp.route('/test-close', methods=['GET'])
def test_close_preview():
    try:
        _require_session_tenant_admin()
        device = _device_from_request()
        return jsonify(preview_test_purge(int(device.organization_id)))
    except DeviceProvisioningError as exc:
        return _err(exc)


@eposone_ops_v1_bp.route('/test-close', methods=['POST'])
def test_close():
    try:
        _require_session_tenant_admin()
        device = _device_from_request()
        body = request.get_json(silent=True) or {}
        uid, label = _actor()
        result = close_test_period(
            int(device.organization_id),
            confirm_phrase=str(body.get('confirm_phrase') or ''),
            actor_user_id=uid,
            actor_label=label,
        )
        return jsonify(result)
    except (DeviceProvisioningError, MoneyHandoffError) as exc:
        return _err(exc)
