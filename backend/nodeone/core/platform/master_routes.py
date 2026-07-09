"""API maestro Core — org units, catálogo (Etapa 10)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from nodeone.core.master.constants import MasterDataError
from nodeone.core.platform.runtime import resolve_organization_id
from nodeone.core.services.org_unit import OrgUnitService
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


def register_platform_master_api(app) -> None:
    if 'platform_master' not in app.blueprints:
        app.register_blueprint(platform_master_bp)
