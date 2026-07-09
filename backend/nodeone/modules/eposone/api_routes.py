"""API REST EPosOne MVP — Etapa 14."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import login_required

from nodeone.core.commerce.cash import CashRegisterService
from nodeone.core.commerce.order import OrderService, OrderValidationError
from nodeone.core.commerce.payment import PaymentService
from nodeone.core.commerce.pos import PosTerminalService
from nodeone.core.master.constants import (
    MasterDataError,
    ORG_UNIT_TYPE_BRANCH,
    ORG_UNIT_TYPE_POS_TERMINAL,
    ORG_UNIT_TYPE_REGISTER,
    ORG_UNIT_TYPE_WAREHOUSE,
)
from nodeone.core.platform.runtime import resolve_organization_id
from nodeone.core.services.org_unit import OrgUnitService
from nodeone.core.template_context_gates import user_can_see_tenant_admin_menu
from nodeone.modules.eposone.org_unit_api import org_unit_collection_handler, org_unit_get_handler
from nodeone.modules.eposone.product_api import product_collection_handler, product_get_handler
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


@eposone_api_bp.route('/orders/<int:order_id>/fiscal', methods=['POST'])
@login_required
def orders_emit_fiscal(order_id: int):
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    from nodeone.core.commerce.fiscal import CommerceFiscalService

    try:
        result = CommerceFiscalService.process_pending_order(gate, int(order_id), source_app_id='eposone')
    except OrderValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'fiscal': result})


@eposone_api_bp.route('/orders/<int:order_id>/split', methods=['POST'])
@login_required
def orders_split(order_id: int):
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    body = request.get_json(silent=True) or {}
    line_indexes = body.get('line_indexes')
    if not isinstance(line_indexes, list) or not line_indexes:
        return jsonify({'error': 'line_indexes_required'}), 400
    try:
        dto = OrderService.split_order(
            gate,
            int(order_id),
            [int(i) for i in line_indexes],
            source_app_id='eposone',
        )
    except (OrderValidationError, ValueError, TypeError) as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'order': dto.to_dict()}), 201


@eposone_api_bp.route('/payments/<int:payment_id>/refund', methods=['POST'])
@login_required
def payments_refund(payment_id: int):
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    body = request.get_json(silent=True) or {}
    try:
        dto = PaymentService.refund(
            gate,
            int(payment_id),
            amount=float(body['amount']) if body.get('amount') is not None else None,
            approval=body,
            source_app_id='eposone',
        )
    except OrderValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'payment': dto.to_dict()})


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


@eposone_api_bp.route('/cash/shifts/<int:shift_id>/reconcile', methods=['POST'])
@login_required
def cash_reconcile_shift(shift_id: int):
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    body = request.get_json(silent=True) or {}
    try:
        dto = CashRegisterService.begin_reconcile(
            gate,
            int(shift_id),
            counted_amount=float(body.get('counted_amount') or 0),
        )
    except OrderValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'shift': dto.to_dict()})


@eposone_api_bp.route('/cash/shifts/<int:shift_id>/close', methods=['POST'])
@login_required
def cash_close_shift(shift_id: int):
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    try:
        dto = CashRegisterService.close_shift(gate, int(shift_id))
    except OrderValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'shift': dto.to_dict()})


@eposone_api_bp.route('/cash/shifts/<int:shift_id>/movements', methods=['POST'])
@login_required
def cash_manual_movement(shift_id: int):
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    body = request.get_json(silent=True) or {}
    try:
        dto = CashRegisterService.record_manual_movement(
            gate,
            int(shift_id),
            str(body.get('movement_type') or ''),
            float(body.get('amount') or 0),
            notes=body.get('notes'),
            approval=body,
        )
    except OrderValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'shift': dto.to_dict()})


@eposone_api_bp.route('/terminals', methods=['GET', 'POST'])
@login_required
def terminals_collection():
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    if request.method == 'GET':
        limit = int(request.args.get('limit', 100) or 100)
        items = PosTerminalService.list_terminals(gate, limit=limit)
        return jsonify({'terminals': [t.to_dict() for t in items], 'count': len(items)})
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


@eposone_api_bp.route('/pos-units', methods=['GET', 'POST'])
@login_required
def pos_units_collection():
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    return org_unit_collection_handler(
        gate,
        unit_type=ORG_UNIT_TYPE_POS_TERMINAL,
        collection_key='pos_units',
        item_key='pos_unit',
    )


@eposone_api_bp.route('/pos-units/<unit_ref>', methods=['GET'])
@login_required
def pos_units_get(unit_ref: str):
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    return org_unit_get_handler(gate, unit_ref, unit_type=ORG_UNIT_TYPE_POS_TERMINAL, item_key='pos_unit')


@eposone_api_bp.route('/registers', methods=['GET', 'POST'])
@login_required
def registers_collection():
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    return org_unit_collection_handler(
        gate,
        unit_type=ORG_UNIT_TYPE_REGISTER,
        collection_key='registers',
        item_key='register',
    )


@eposone_api_bp.route('/registers/<unit_ref>', methods=['GET'])
@login_required
def registers_get(unit_ref: str):
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    return org_unit_get_handler(gate, unit_ref, unit_type=ORG_UNIT_TYPE_REGISTER, item_key='register')


@eposone_api_bp.route('/warehouses', methods=['GET', 'POST'])
@login_required
def warehouses_collection():
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    return org_unit_collection_handler(
        gate,
        unit_type=ORG_UNIT_TYPE_WAREHOUSE,
        collection_key='warehouses',
        item_key='warehouse',
    )


@eposone_api_bp.route('/warehouses/<unit_ref>', methods=['GET'])
@login_required
def warehouses_get(unit_ref: str):
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    return org_unit_get_handler(gate, unit_ref, unit_type=ORG_UNIT_TYPE_WAREHOUSE, item_key='warehouse')


@eposone_api_bp.route('/stock-balances', methods=['GET'])
@login_required
def stock_balances_list():
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    from nodeone.core.commerce.stock import StockService

    warehouse_id = request.args.get('warehouse_org_unit_id')
    product_ref = (request.args.get('product_ref') or '').strip() or None
    limit = int(request.args.get('limit', 100) or 100)
    items = StockService.list_balances(
        gate,
        warehouse_org_unit_id=int(warehouse_id) if warehouse_id else None,
        product_ref=product_ref,
        limit=limit,
    )
    return jsonify({'stock_balances': [b.to_dict() for b in items], 'count': len(items)})


@eposone_api_bp.route('/products', methods=['GET', 'POST'])
@login_required
def products_collection():
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    return product_collection_handler(gate)


@eposone_api_bp.route('/products/<product_ref>', methods=['GET'])
@login_required
def products_get(product_ref: str):
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    return product_get_handler(gate, product_ref)


@eposone_api_bp.route('/branches', methods=['GET', 'POST'])
@login_required
def branches_collection():
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    if request.method == 'GET':
        status = (request.args.get('status') or '').strip() or None
        items = OrgUnitService.list_units(gate, unit_type=ORG_UNIT_TYPE_BRANCH, status=status)
        return jsonify({'branches': [b.to_dict() for b in items], 'count': len(items)})
    body = request.get_json(silent=True) or {}
    body['unit_type'] = ORG_UNIT_TYPE_BRANCH
    try:
        dto = OrgUnitService.create(gate, body)
    except MasterDataError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'branch': dto.to_dict()}), 201


@eposone_api_bp.route('/branches/<unit_ref>', methods=['GET'])
@login_required
def branches_get(unit_ref: str):
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    dto = OrgUnitService.get_by_ref(gate, unit_ref)
    if dto is None or dto.unit_type != ORG_UNIT_TYPE_BRANCH:
        return jsonify({'error': 'not_found'}), 404
    return jsonify({'branch': dto.to_dict()})


@eposone_api_bp.route('/kds/tickets', methods=['GET'])
@login_required
def kds_tickets_list():
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    from nodeone.modules.eposone.kds_service import KdsService

    station_type = (request.args.get('station_type') or '').strip() or None
    status = (request.args.get('status') or '').strip() or None
    limit = int(request.args.get('limit', 50) or 50)
    items = KdsService.list_tickets(gate, station_type=station_type, status=status, limit=limit)
    return jsonify({'tickets': [t.to_dict() for t in items]})


@eposone_api_bp.route('/kds/tickets/<int:ticket_id>/status', methods=['POST'])
@login_required
def kds_ticket_transition(ticket_id: int):
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    from nodeone.modules.eposone.kds_service import KdsService

    body = request.get_json(silent=True) or {}
    try:
        dto = KdsService.transition_ticket(gate, int(ticket_id), str(body.get('status') or ''))
    except OrderValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'ticket': dto.to_dict()})


@eposone_api_bp.route('/kds/orders/<int:order_id>/tickets', methods=['POST'])
@login_required
def kds_tickets_create_for_order(order_id: int):
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    from nodeone.modules.eposone.kds_service import KdsService

    try:
        items = KdsService.create_tickets_for_order(gate, int(order_id))
    except OrderValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'tickets': [t.to_dict() for t in items]}), 201


@eposone_api_bp.route('/deliveries', methods=['GET'])
@login_required
def deliveries_list():
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    from nodeone.modules.eposone.delivery_service import EposoneDeliveryService

    status = (request.args.get('status') or '').strip() or None
    limit = int(request.args.get('limit', 50) or 50)
    items = EposoneDeliveryService.list_deliveries(gate, status=status, limit=limit)
    return jsonify({'deliveries': [d.to_dict() for d in items]})


@eposone_api_bp.route('/deliveries', methods=['POST'])
@login_required
def deliveries_create():
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    from nodeone.modules.eposone.delivery_service import EposoneDeliveryService

    body = request.get_json(silent=True) or {}
    order_id = body.get('order_id')
    if not order_id:
        return jsonify({'error': 'order_id_required'}), 400
    try:
        dto = EposoneDeliveryService.create_for_order(
            gate,
            int(order_id),
            destination_address=body.get('destination_address'),
            notes=body.get('notes'),
        )
    except OrderValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'delivery': dto.to_dict()}), 201


@eposone_api_bp.route('/deliveries/<int:delivery_id>/assign', methods=['POST'])
@login_required
def deliveries_assign(delivery_id: int):
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    from nodeone.modules.eposone.delivery_service import EposoneDeliveryService

    body = request.get_json(silent=True) or {}
    try:
        dto = EposoneDeliveryService.assign_driver(
            gate,
            int(delivery_id),
            driver_name=str(body.get('driver_name') or ''),
            driver_contact_id=body.get('driver_contact_id'),
        )
    except OrderValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'delivery': dto.to_dict()})


@eposone_api_bp.route('/deliveries/<int:delivery_id>/status', methods=['POST'])
@login_required
def deliveries_transition(delivery_id: int):
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    from nodeone.modules.eposone.delivery_service import EposoneDeliveryService

    body = request.get_json(silent=True) or {}
    try:
        dto = EposoneDeliveryService.transition_status(gate, int(delivery_id), str(body.get('status') or ''))
    except OrderValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'delivery': dto.to_dict()})


@eposone_api_bp.route('/digital-menus', methods=['GET', 'POST'])
@login_required
def digital_menus_collection():
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    from nodeone.modules.eposone.digital_menu_service import DigitalMenuService

    if request.method == 'GET':
        menus = DigitalMenuService.list_menus(gate)
        return jsonify(
            {
                'menus': [
                    {
                        **m.to_dict(),
                        'public_url': DigitalMenuService.public_menu_url(m.public_token),
                    }
                    for m in menus
                ]
            }
        )
    body = request.get_json(silent=True) or {}
    try:
        dto = DigitalMenuService.create_menu(
            gate,
            name=str(body.get('name') or ''),
            items=body.get('items') if isinstance(body.get('items'), list) else None,
        )
    except OrderValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify(
        {
            'menu': dto.to_dict(),
            'public_url': DigitalMenuService.public_menu_url(dto.public_token),
        }
    ), 201
