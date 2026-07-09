"""Helpers API EPosOne — org units maestro (Etapa 10b)."""

from __future__ import annotations

from flask import jsonify, request

from nodeone.core.master.constants import MasterDataError
from nodeone.core.services.org_unit import OrgUnitService


def org_unit_collection_handler(
    gate: int,
    *,
    unit_type: str,
    collection_key: str,
    item_key: str,
):
    if request.method == 'GET':
        status = (request.args.get('status') or '').strip() or None
        items = OrgUnitService.list_units(gate, unit_type=unit_type, status=status)
        return jsonify({collection_key: [u.to_dict() for u in items], 'count': len(items)})
    body = request.get_json(silent=True) or {}
    body['unit_type'] = unit_type
    try:
        dto = OrgUnitService.create(gate, body)
    except MasterDataError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({item_key: dto.to_dict()}), 201


def org_unit_get_handler(gate: int, unit_ref: str, *, unit_type: str, item_key: str):
    dto = OrgUnitService.get_by_ref(gate, unit_ref)
    if dto is None or dto.unit_type != unit_type:
        return jsonify({'error': 'not_found'}), 404
    return jsonify({item_key: dto.to_dict()})
