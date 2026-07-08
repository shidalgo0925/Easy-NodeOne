"""API sync offline — Etapa 13 (admin / POS)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from nodeone.core.platform.runtime import resolve_organization_id
from nodeone.core.sync.constants import SYNC_DOMAIN_EVENTS
from nodeone.core.sync.cursor import SyncCursorService
from nodeone.core.sync.incremental import IncrementalSyncService
from nodeone.core.sync.queue import SyncOperationService
from nodeone.core.template_context_gates import user_can_see_tenant_admin_menu

platform_sync_bp = Blueprint('platform_sync', __name__, url_prefix='/api/platform/sync')


def _org_id() -> int | None:
    oid = resolve_organization_id()
    return int(oid) if oid is not None else None


def _require_sync_access():
    if not current_user.is_authenticated:
        return jsonify({'error': 'unauthorized'}), 401
    if not user_can_see_tenant_admin_menu(current_user):
        return jsonify({'error': 'forbidden'}), 403
    oid = _org_id()
    if oid is None:
        return jsonify({'error': 'organization_required'}), 400
    return oid


@platform_sync_bp.route('/events', methods=['GET'])
@login_required
def sync_events_pull():
    gate = _require_sync_access()
    if not isinstance(gate, int):
        return gate
    since_id = int(request.args.get('since_id', 0) or 0)
    limit = int(request.args.get('limit', 100) or 100)
    prefix = (request.args.get('event_type_prefix') or '').strip() or None
    items, cursor = IncrementalSyncService.fetch_events(
        gate, since_id=since_id, limit=limit, event_type_prefix=prefix
    )
    return jsonify(
        {
            'events': [item.to_dict() for item in items],
            'cursor': cursor,
            'domain': SYNC_DOMAIN_EVENTS,
        }
    )


@platform_sync_bp.route('/operations', methods=['POST'])
@login_required
def sync_operations_enqueue():
    gate = _require_sync_access()
    if not isinstance(gate, int):
        return gate
    body = request.get_json(silent=True) or {}
    try:
        dto = SyncOperationService.enqueue(
            gate,
            idempotency_key=str(body.get('idempotency_key') or ''),
            operation_type=str(body.get('operation_type') or ''),
            payload=body.get('payload') if isinstance(body.get('payload'), dict) else {},
            client_id=str(body.get('client_id') or 'default'),
            entity_type=body.get('entity_type'),
            entity_ref=body.get('entity_ref'),
            base_version=body.get('base_version'),
        )
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'operation': dto.to_dict()}), 201


@platform_sync_bp.route('/operations/process', methods=['POST'])
@login_required
def sync_operations_process():
    gate = _require_sync_access()
    if not isinstance(gate, int):
        return gate
    body = request.get_json(silent=True) or {}
    limit = int(body.get('limit', 50) or 50)
    from nodeone.modules.eposone.sync_handlers import process_eposone_sync_queue

    processed = process_eposone_sync_queue(organization_id=gate, limit=limit)
    return jsonify({'processed': processed, 'organization_id': gate})


@platform_sync_bp.route('/operations/<int:operation_id>', methods=['GET'])
@login_required
def sync_operations_get(operation_id: int):
    gate = _require_sync_access()
    if not isinstance(gate, int):
        return gate
    dto = SyncOperationService.get(gate, int(operation_id))
    if dto is None:
        return jsonify({'error': 'not_found'}), 404
    return jsonify({'operation': dto.to_dict()})


@platform_sync_bp.route('/cursors/<domain>', methods=['GET', 'PUT'])
@login_required
def sync_cursors(domain: str):
    gate = _require_sync_access()
    if not isinstance(gate, int):
        return gate
    client_id = (request.args.get('client_id') or 'default').strip() or 'default'
    if request.method == 'GET':
        dto = SyncCursorService.get(gate, domain, client_id=client_id)
        return jsonify({'cursor': dto.to_dict()})
    body = request.get_json(silent=True) or {}
    dto = SyncCursorService.set_cursor(
        gate,
        domain,
        str(body.get('cursor_value') or body.get('cursor') or '0'),
        client_id=str(body.get('client_id') or client_id),
    )
    return jsonify({'cursor': dto.to_dict()})


def register_platform_sync_blueprint(app) -> None:
    if 'platform_sync' in app.blueprints:
        return
    app.register_blueprint(platform_sync_bp)
