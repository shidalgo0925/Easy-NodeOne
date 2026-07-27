"""Helpers API EPosOne — catálogo maestro (Etapa 10d)."""

from __future__ import annotations

from flask import jsonify, request

from nodeone.core.master.constants import MasterDataError
from nodeone.core.services.product import ProductService


def product_collection_handler(gate: int):
    if request.method == 'GET':
        query = (request.args.get('q') or request.args.get('query') or '').strip() or None
        product_type = (request.args.get('product_type') or '').strip() or None
        status = (request.args.get('status') or '').strip() or None
        limit = int(request.args.get('limit', 100) or 100)
        items = ProductService.search(
            gate,
            query=query,
            product_type=product_type,
            status=status,
            limit=limit,
        )
        return jsonify({'products': [p.to_dict() for p in items], 'count': len(items)})
    body = request.get_json(silent=True) or {}
    if not body.get('source_app_id'):
        body['source_app_id'] = 'eposone'
    try:
        dto = ProductService.create(gate, body)
    except MasterDataError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'product': dto.to_dict()}), 201


def product_get_handler(gate: int, product_ref: str):
    dto = ProductService.get_by_ref(gate, product_ref)
    if dto is None:
        return jsonify({'error': 'not_found'}), 404
    payload = dto.to_dict()
    payload['can_delete'] = not ProductService.has_operational_usage(gate, product_ref)
    return jsonify({'product': payload})


def product_update_handler(gate: int, product_ref: str):
    body = request.get_json(silent=True) or {}
    try:
        dto = ProductService.update(gate, product_ref, body)
    except MasterDataError as exc:
        code = str(exc)
        status = 404 if code == 'product_not_found' else 400
        return jsonify({'error': code}), status
    return jsonify({'product': dto.to_dict()})


def product_delete_handler(gate: int, product_ref: str):
    try:
        ProductService.delete(gate, product_ref)
    except MasterDataError as exc:
        code = str(exc)
        if code == 'product_not_found':
            return jsonify({'error': code}), 404
        if code == 'product_has_movements':
            return jsonify({'error': code, 'hint': 'deactivate_instead'}), 409
        return jsonify({'error': code}), 400
    return jsonify({'ok': True, 'deleted': product_ref}), 200


def product_deactivate_handler(gate: int, product_ref: str):
    try:
        dto = ProductService.deactivate(gate, product_ref)
    except MasterDataError as exc:
        code = str(exc)
        status = 404 if code == 'product_not_found' else 400
        return jsonify({'error': code}), status
    return jsonify({'product': dto.to_dict()})

