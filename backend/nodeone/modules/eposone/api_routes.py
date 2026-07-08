"""API REST EPosOne MVP — Etapa 14."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import login_required

from nodeone.core.commerce.cash import CashRegisterService
from nodeone.core.commerce.order import OrderService, OrderValidationError
from nodeone.core.commerce.payment import PaymentService
from nodeone.core.commerce.pos import PosTerminalService
from nodeone.core.platform.runtime import resolve_organization_id
from nodeone.core.template_context_gates import user_can_see_tenant_admin_menu
from flask_login import current_user

eposone_api_bp = Blueprint('eposone_api', __name__, url_prefix='/api/eposone')


def _org_gate():
    if not current_user.is_authenticated:
        return jsonify({'error': 'unauthorized'}), 401
    if not user_can_see_tenant_admin_menu(current_user):
        return jsonify({'error': 'forbidden'}), 403
    oid = resolve_organization_id()
    if oid is None:
        return jsonify({'error': 'organization_required'}), 400
    return int(oid)


@eposone_api_bp.route('/orders', methods=['GET', 'POST'])
@login_required
def orders_collection():
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    if request.method == 'GET':
        status = (request.args.get('status') or '').strip() or None
        limit = int(request.args.get('limit', 50) or 50)
        offset = int(request.args.get('offset', 0) or 0)
        items, total = OrderService.search(gate, status=status, limit=limit, offset=offset)
        return jsonify(
            {
                'orders': [o.to_dict() for o in items],
                'total': total,
                'limit': limit,
                'offset': offset,
            }
        )
    body = request.get_json(silent=True) or {}
    try:
        dto = OrderService.create(gate, body, source_app_id='eposone')
    except OrderValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'order': dto.to_dict()}), 201


@eposone_api_bp.route('/orders/<int:order_id>', methods=['GET'])
@login_required
def orders_get(order_id: int):
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    dto = OrderService.get(gate, int(order_id))
    if dto is None:
        return jsonify({'error': 'not_found'}), 404
    return jsonify({'order': dto.to_dict()})


@eposone_api_bp.route('/orders/<int:order_id>/status', methods=['POST'])
@login_required
def orders_transition(order_id: int):
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    body = request.get_json(silent=True) or {}
    try:
        dto = OrderService.transition_status(
            gate,
            int(order_id),
            str(body.get('status') or ''),
            source_app_id='eposone',
            reason=body.get('reason'),
        )
    except OrderValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'order': dto.to_dict()})


@eposone_api_bp.route('/orders/<int:order_id>/payments', methods=['POST'])
@login_required
def orders_capture_payment(order_id: int):
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    body = request.get_json(silent=True) or {}
    body['order_id'] = int(order_id)
    try:
        dto = PaymentService.capture(gate, body, source_app_id='eposone')
    except OrderValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'payment': dto.to_dict()}), 201


@eposone_api_bp.route('/cash/shifts', methods=['POST'])
@login_required
def cash_open_shift():
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    body = request.get_json(silent=True) or {}
    try:
        dto = CashRegisterService.open_shift(
            gate,
            register_ref=str(body.get('register_ref') or ''),
            opening_balance=float(body.get('opening_balance') or 0),
        )
    except OrderValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'shift': dto.to_dict()}), 201


@eposone_api_bp.route('/cash/shifts/<int:shift_id>/close', methods=['POST'])
@login_required
def cash_close_shift(shift_id: int):
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    body = request.get_json(silent=True) or {}
    try:
        dto = CashRegisterService.close_shift(
            gate,
            int(shift_id),
            closing_balance=float(body.get('closing_balance') or 0),
        )
    except OrderValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'shift': dto.to_dict()})


@eposone_api_bp.route('/terminals', methods=['POST'])
@login_required
def terminals_register():
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    body = request.get_json(silent=True) or {}
    try:
        dto = PosTerminalService.register(
            gate,
            terminal_ref=str(body.get('terminal_ref') or ''),
            device_label=body.get('device_label'),
            register_ref=body.get('register_ref'),
        )
    except OrderValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'terminal': dto.to_dict()}), 201
