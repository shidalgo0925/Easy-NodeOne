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
    return jsonify({'product': dto.to_dict()})
