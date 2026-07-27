"""Helpers API EPosOne — contactos maestro + puente legacy (Etapa 10c)."""

from __future__ import annotations

from flask import jsonify, request

from nodeone.core.master.constants import MasterDataError
from nodeone.core.services.contacts import ContactService


def contact_collection_handler(gate: int):
    if request.method == 'GET':
        q = (request.args.get('q') or request.args.get('query') or '').strip()
        role = (request.args.get('role') or '').strip()
        contact_type = (request.args.get('contact_type') or '').strip()
        limit = int(request.args.get('limit', 50) or 50)
        offset = int(request.args.get('offset', 0) or 0)
        active_raw = (request.args.get('active_only') or 'true').strip().lower()
        active_only = active_raw not in ('0', 'false', 'no')
        items, total = ContactService.search(
            gate,
            q=q,
            role=role,
            contact_type=contact_type,
            active_only=active_only,
            limit=limit,
            offset=offset,
        )
        return jsonify({'contacts': [c.to_dict() for c in items], 'count': len(items), 'total': total})
    return _contact_create(gate)


def _contact_create(gate: int):
    body = request.get_json(silent=True) or {}
    try:
        if body.get('legacy_contact_id') is not None:
            dto = ContactService.create_with_legacy_link(gate, body)
        else:
            dto = ContactService.create(gate, body)
    except (ContactService.ValidationError, MasterDataError) as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'contact': dto.to_dict()}), 201


def contact_get_handler(gate: int, contact_id: int):
    dto = ContactService.get(gate, int(contact_id))
    if dto is None:
        return jsonify({'error': 'not_found'}), 404
    return jsonify({'contact': dto.to_dict()})


def contact_resolve_handler(gate: int, contact_id: int):
    from nodeone.core.master.contact_bridge import ContactBridgeService

    dto = ContactBridgeService.resolve(gate, int(contact_id))
    if dto is None:
        return jsonify({'error': 'not_found'}), 404
    return jsonify({'resolved': dto.to_dict()})


def contact_promote_legacy_handler(gate: int):
    from nodeone.core.master.contact_bridge import ContactBridgeService

    body = request.get_json(silent=True) or {}
    legacy_contact_id = body.get('legacy_contact_id')
    if legacy_contact_id is None:
        return jsonify({'error': 'legacy_contact_id_required'}), 400
    try:
        resolved = ContactBridgeService.promote_legacy(
            gate,
            int(legacy_contact_id),
            link_source=str(body.get('link_source') or 'eposone_promote'),
        )
    except MasterDataError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'resolved': resolved.to_dict()}), 201
