"""API maestro Core — org units, catálogo (Etapa 10)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from nodeone.core.master.constants import MasterDataError
from nodeone.core.platform.runtime import resolve_organization_id
from nodeone.core.services.org_unit import OrgUnitService
from nodeone.core.services.user_contact import UserContactLinkService
from nodeone.core.template_context_gates import user_can_see_tenant_admin_menu

platform_master_bp = Blueprint('platform_master', __name__, url_prefix='/api/platform/master')


def _org_gate():
    if not current_user.is_authenticated:
        return jsonify({'error': 'unauthorized'}), 401
    if not user_can_see_tenant_admin_menu(current_user):
        return jsonify({'error': 'forbidden'}), 403
    oid = resolve_organization_id()
    if oid is None:
        return jsonify({'error': 'organization_required'}), 400
    return int(oid)


@platform_master_bp.route('/org-units', methods=['GET', 'POST'])
@login_required
def org_units_collection():
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    if request.method == 'GET':
        unit_type = (request.args.get('unit_type') or '').strip() or None
        status = (request.args.get('status') or '').strip() or None
        items = OrgUnitService.list_units(gate, unit_type=unit_type, status=status)
        return jsonify({'org_units': [u.to_dict() for u in items], 'count': len(items)})
    body = request.get_json(silent=True) or {}
    try:
        dto = OrgUnitService.create(gate, body)
    except MasterDataError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'org_unit': dto.to_dict()}), 201


@platform_master_bp.route('/org-units/<unit_ref>', methods=['GET'])
@login_required
def org_units_get(unit_ref: str):
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    dto = OrgUnitService.get_by_ref(gate, unit_ref)
    if dto is None:
        return jsonify({'error': 'not_found'}), 404
    return jsonify({'org_unit': dto.to_dict()})


@platform_master_bp.route('/me/linked-contact', methods=['GET', 'PUT', 'DELETE'])
@login_required
def me_linked_contact():
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    user_id = int(current_user.id)
    if request.method == 'GET':
        try:
            dto = UserContactLinkService.get(user_id, gate)
        except MasterDataError as exc:
            return jsonify({'error': str(exc)}), 400
        return jsonify({'link': dto.to_dict()})
    if request.method == 'DELETE':
        try:
            dto = UserContactLinkService.unlink(user_id, gate)
        except MasterDataError as exc:
            return jsonify({'error': str(exc)}), 400
        return jsonify({'link': dto.to_dict()})
    body = request.get_json(silent=True) or {}
    contact_id = body.get('contact_id')
    if contact_id is None:
        return jsonify({'error': 'contact_id_required'}), 400
    try:
        dto = UserContactLinkService.link(user_id, gate, int(contact_id))
    except MasterDataError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'link': dto.to_dict()})


@platform_master_bp.route('/contacts/resolve/<int:contact_id>', methods=['GET'])
@login_required
def contacts_resolve(contact_id: int):
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    from nodeone.core.master.contact_bridge import ContactBridgeService

    dto = ContactBridgeService.resolve(gate, int(contact_id))
    if dto is None:
        return jsonify({'error': 'not_found'}), 404
    return jsonify({'resolved': dto.to_dict()})


@platform_master_bp.route('/contacts/legacy-links', methods=['POST'])
@login_required
def contacts_legacy_link():
    gate = _org_gate()
    if not isinstance(gate, int):
        return gate
    from nodeone.core.master.contact_bridge import ContactBridgeService

    body = request.get_json(silent=True) or {}
    contact_id = body.get('contact_id')
    legacy_contact_id = body.get('legacy_contact_id')
    if contact_id is None or legacy_contact_id is None:
        return jsonify({'error': 'contact_id_and_legacy_contact_id_required'}), 400
    try:
        ContactBridgeService.link(
            gate,
            contact_id=int(contact_id),
            legacy_contact_id=int(legacy_contact_id),
            link_source=str(body.get('link_source') or 'manual'),
        )
    except MasterDataError as exc:
        return jsonify({'error': str(exc)}), 400
    dto = ContactBridgeService.resolve(gate, int(contact_id))
    return jsonify({'resolved': dto.to_dict() if dto else None}), 201


def register_platform_master_api(app) -> None:
    if 'platform_master' not in app.blueprints:
        app.register_blueprint(platform_master_bp)
