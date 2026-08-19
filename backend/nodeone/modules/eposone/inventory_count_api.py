"""API de dominio — toma física Connected (sesión, no pantallas Flutter)."""

from __future__ import annotations

from flask import jsonify, request

from nodeone.core.platform.inventory_service import InventoryError
from nodeone.core.platform.physical_count_service import (
    PhysicalCountError,
    approve_count,
    cancel_count,
    complete_count,
    get_count,
    list_location_products,
    start_count,
    upsert_lines,
)


def _err(exc: Exception):
    code = str(exc)
    http = 400
    if code in ('count_not_found',):
        http = 404
    if code in ('cannot_self_approve', 'cannot_delete_approved', 'cannot_cancel_approved'):
        http = 403
    return jsonify({'error': code}), http


def start_handler(
    organization_id: int,
    body: dict,
    *,
    created_by_user_id: int | None = None,
    source_device_id: int | None = None,
):
    try:
        payload = start_count(
            int(organization_id),
            warehouse_org_unit_id=int(body.get('warehouse_org_unit_id')),
            client_count_id=body.get('client_count_id'),
            created_by_user_id=created_by_user_id,
            source_device_id=source_device_id,
            count_mode=str(body.get('count_mode') or 'BLIND'),
            notes=body.get('notes'),
            source_system=str(body.get('source_system') or 'EP1'),
        )
    except (PhysicalCountError, InventoryError, TypeError, ValueError) as exc:
        return _err(exc)
    return jsonify(payload), 201


def get_handler(organization_id: int, count_id: int, *, include_theoretical=None):
    try:
        payload = get_count(
            int(organization_id),
            int(count_id),
            include_theoretical=include_theoretical,
        )
    except (PhysicalCountError, InventoryError) as exc:
        return _err(exc)
    return jsonify(payload)


def lines_handler(organization_id: int, count_id: int, body: dict):
    raw_lines = body.get('lines')
    if not isinstance(raw_lines, list):
        return jsonify({'error': 'lines_required'}), 400
    try:
        payload = upsert_lines(int(organization_id), int(count_id), raw_lines)
    except (PhysicalCountError, InventoryError, ValueError) as exc:
        return _err(exc)
    return jsonify(payload)


def complete_handler(organization_id: int, count_id: int):
    try:
        payload = complete_count(int(organization_id), int(count_id))
    except (PhysicalCountError, InventoryError) as exc:
        return _err(exc)
    return jsonify(payload)


def approve_handler(
    organization_id: int,
    count_id: int,
    *,
    approved_by_user_id: int | None,
    is_admin: bool = False,
    allow_self_approve: bool = False,
):
    try:
        payload = approve_count(
            int(organization_id),
            int(count_id),
            approved_by_user_id=approved_by_user_id,
            allow_self_approve=allow_self_approve,
            is_admin=is_admin,
        )
    except (PhysicalCountError, InventoryError) as exc:
        return _err(exc)
    return jsonify(payload)


def cancel_handler(organization_id: int, count_id: int):
    try:
        payload = cancel_count(int(organization_id), int(count_id))
    except (PhysicalCountError, InventoryError) as exc:
        return _err(exc)
    return jsonify(payload)


def products_handler(organization_id: int, warehouse_org_unit_id: int, *, blind: bool = True):
    try:
        items = list_location_products(
            int(organization_id),
            int(warehouse_org_unit_id),
            blind=blind,
        )
    except (PhysicalCountError, InventoryError) as exc:
        return _err(exc)
    return jsonify({'products': items, 'count': len(items), 'blind': blind})


def request_include_theoretical() -> bool | None:
    raw = (request.args.get('include_theoretical') or '').strip().lower()
    if raw in ('1', 'true', 'yes'):
        return True
    if raw in ('0', 'false', 'no'):
        return False
    return None
