"""Helpers API EPosOne — contactos maestro + puente legacy (Etapa 10c)."""

from __future__ import annotations

from flask import jsonify, request

from nodeone.core.master.constants import MasterDataError
from nodeone.core.services.contacts import ContactService


def contact_create_handler(gate: int):
    body = request.get_json(silent=True) or {}
    try:
        if body.get('legacy_contact_id') is not None:
            dto = ContactService.create_with_legacy_link(gate, body)
        else:
            dto = ContactService.create(gate, body)
    except (ContactService.ValidationError, MasterDataError) as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'contact': dto.to_dict()}), 201


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
