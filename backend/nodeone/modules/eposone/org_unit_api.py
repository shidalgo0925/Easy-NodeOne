"""Helpers API EPosOne — org units maestro (Etapa 10b + ADR-005)."""

from __future__ import annotations

from flask import jsonify, request

from nodeone.core.master.constants import ORG_UNIT_POS_TYPES, MasterDataError
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
        parent_raw = (request.args.get('parent_id') or '').strip()
        parent_id = int(parent_raw) if parent_raw.isdigit() else None
        items = OrgUnitService.list_units(
            gate, unit_type=unit_type, status=status, parent_id=parent_id
        )
        return jsonify({collection_key: [u.to_dict() for u in items], 'count': len(items)})
    body = request.get_json(silent=True) or {}
    body['unit_type'] = unit_type
    try:
        dto = OrgUnitService.create(gate, body)
    except MasterDataError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({item_key: dto.to_dict()}), 201


def _unit_type_matches(actual: str, expected: str) -> bool:
    a = (actual or '').strip().lower()
    e = (expected or '').strip().lower()
    if a == e:
        return True
    # POS: aceptar pos y legado pos_terminal
    if e in ORG_UNIT_POS_TYPES and a in ORG_UNIT_POS_TYPES:
        return True
    return False


def org_unit_get_handler(gate: int, unit_ref: str, *, unit_type: str, item_key: str):
    dto = OrgUnitService.get_by_ref(gate, unit_ref)
    if dto is None or not _unit_type_matches(dto.unit_type, unit_type):
        return jsonify({'error': 'not_found'}), 404
    return jsonify({item_key: dto.to_dict()})


def org_unit_patch_handler(gate: int, unit_id: int, *, item_key: str):
    body = request.get_json(silent=True) or {}
    try:
        dto = OrgUnitService.update(gate, int(unit_id), body)
    except MasterDataError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({item_key: dto.to_dict()})


def org_unit_deactivate_handler(gate: int, unit_id: int, *, item_key: str):
    try:
        dto = OrgUnitService.deactivate(gate, int(unit_id))
    except MasterDataError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({item_key: dto.to_dict()})
