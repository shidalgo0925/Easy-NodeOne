"""API v1 Pedidos — Hito 3 Order Domain (Device Bearer)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user

from nodeone.modules.eposone.device_provisioning import (
    DeviceProvisioningError,
    DeviceProvisioningService,
)
from nodeone.modules.eposone.order_domain import (
    OrderDomainError,
    OrderDomainService,
    order_to_dict,
)

eposone_orders_v1_bp = Blueprint(
    'eposone_orders_v1',
    __name__,
    url_prefix='/api/v1/orders',
)


def _device_from_request():
    """Auth: Device Bearer (preferido) o sesión BO con terminal activo de la org."""
    auth = request.headers.get('Authorization')
    if auth and auth.strip().lower().startswith('bearer '):
        return DeviceProvisioningService.authenticate_bearer(auth)

    # BackOffice: sesión + org; actor sintético "Caja principal (BO)".
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


def _bo_actor_user_ref() -> str | None:
    if not getattr(current_user, 'is_authenticated', False):
        return None
    from nodeone.modules.eposone.bo_actor import actor_label_from_user

    return actor_label_from_user(current_user)


def _err(exc: Exception):
    if isinstance(exc, (DeviceProvisioningError, OrderDomainError)):
        return jsonify({'error': exc.code}), int(exc.http_status)
    raise exc


@eposone_orders_v1_bp.route('/payment-methods', methods=['GET'])
def orders_payment_methods():
    """Métodos de pago POS configurables (mismo catálogo para tablet y BO)."""
    try:
        device = _device_from_request()
        from nodeone.modules.eposone.order_payment_service import OrderPaymentService

        methods = OrderPaymentService.list_methods(int(device.organization_id), enabled_only=True)
        return jsonify({'methods': methods, 'count': len(methods)})
    except (DeviceProvisioningError, OrderDomainError) as exc:
        return _err(exc)


@eposone_orders_v1_bp.route('', methods=['GET'])
def orders_list():
    try:
        device = _device_from_request()
        status = request.args.get('status')
        table_ref = request.args.get('table_ref')
        limit = int(request.args.get('limit') or 50)
        items = OrderDomainService.list_orders(
            device, status=status, table_ref=table_ref, limit=limit
        )
        return jsonify({'orders': [order_to_dict(o) for o in items], 'count': len(items)})
    except (DeviceProvisioningError, OrderDomainError) as exc:
        return _err(exc)


@eposone_orders_v1_bp.route('', methods=['POST'])
def orders_create():
    try:
        device = _device_from_request()
        body = request.get_json(silent=True) or {}
        order = OrderDomainService.create_order(device, body)
        return jsonify({'order': order_to_dict(order, include_events=True)}), 201
    except (DeviceProvisioningError, OrderDomainError) as exc:
        return _err(exc)


@eposone_orders_v1_bp.route('/<int:order_id>', methods=['GET'])
def orders_get(order_id: int):
    try:
        device = _device_from_request()
        order = OrderDomainService.get_order(device, order_id)
        include = (request.args.get('include') or '').lower()
        return jsonify(
            {'order': order_to_dict(order, include_events=('events' in include or include == 'all'))}
        )
    except (DeviceProvisioningError, OrderDomainError) as exc:
        return _err(exc)


@eposone_orders_v1_bp.route('/<int:order_id>', methods=['PATCH'])
def orders_patch(order_id: int):
    try:
        device = _device_from_request()
        body = request.get_json(silent=True) or {}
        order = OrderDomainService.patch_order(device, order_id, body)
        return jsonify({'order': order_to_dict(order)})
    except (DeviceProvisioningError, OrderDomainError) as exc:
        return _err(exc)


@eposone_orders_v1_bp.route('/<int:order_id>/events', methods=['POST'])
def orders_events(order_id: int):
    try:
        device = _device_from_request()
        body = request.get_json(silent=True) or {}
        order = OrderDomainService.apply_event(device, order_id, body)
        return jsonify({'order': order_to_dict(order, include_events=True)})
    except (DeviceProvisioningError, OrderDomainError) as exc:
        return _err(exc)


@eposone_orders_v1_bp.route('/<int:order_id>/payments', methods=['POST'])
def orders_payments(order_id: int):
    try:
        device = _device_from_request()
        body = request.get_json(silent=True) or {}
        auth = request.headers.get('Authorization') or ''
        if not auth.strip().lower().startswith('bearer '):
            actor = _bo_actor_user_ref()
            if actor and not body.get('actor_user_ref'):
                body = dict(body)
                body['actor_user_ref'] = actor
        from nodeone.modules.eposone.order_payment_service import OrderPaymentService

        order = OrderPaymentService.add_payment(device, order_id, body)
        return jsonify({'order': order_to_dict(order)}), 201
    except (DeviceProvisioningError, OrderDomainError) as exc:
        return _err(exc)


@eposone_orders_v1_bp.route('/<int:order_id>/split', methods=['POST'])
def orders_split(order_id: int):
    try:
        device = _device_from_request()
        body = request.get_json(silent=True) or {}
        result = OrderDomainService.split_order(device, order_id, body)
        return jsonify(result), 201
    except (DeviceProvisioningError, OrderDomainError) as exc:
        return _err(exc)
