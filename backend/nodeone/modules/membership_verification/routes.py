"""POST /api/v1/membership/verification — Sprint A (sin UI)."""

from __future__ import annotations

import time

from flask import Blueprint, g, jsonify, request

from nodeone.services import integration_api_keys as keys_svc
from nodeone.services.membership_verification import (
    MembershipVerificationError,
    verify,
)

membership_verification_bp = Blueprint('membership_verification', __name__)


def _client_ip() -> str | None:
    fwd = (request.headers.get('X-Forwarded-For') or '').split(',')[0].strip()
    return fwd or (request.remote_addr or None)


@membership_verification_bp.route('/api/v1/membership/verification', methods=['POST'])
def membership_verification():
    t0 = time.perf_counter()
    endpoint = '/api/v1/membership/verification'
    api_key_row = None
    org_id = None
    result_label = 'error'
    status = 500
    body: dict = {'success': False, 'message': 'error'}

    try:
        raw = keys_svc.extract_x_api_key(request)
        api_key_row, err = keys_svc.authenticate_api_key(raw)
        if err == 'not_configured':
            status = 503
            body = {'success': False, 'message': 'not_configured'}
            result_label = 'not_configured'
            return jsonify(body), status
        if err or api_key_row is None:
            status = 401
            body = {'success': False, 'message': 'Unauthorized'}
            result_label = 'unauthorized'
            return jsonify(body), status

        org_id = int(api_key_row.organization_id)
        g.integration_api_key_id = getattr(api_key_row, 'id', None)

        data = request.get_json(silent=True) or {}
        vtype = data.get('type')
        value = data.get('value')
        try:
            body = verify(type=str(vtype or ''), value=str(value if value is not None else ''), organization_id=org_id)
            status = 200
            if not body.get('found'):
                result_label = 'not_found'
            elif (body.get('member') or {}).get('is_active_member'):
                result_label = 'found_active'
            else:
                result_label = 'found_inactive'
            keys_svc.touch_key_usage(api_key_row)
            return jsonify(body), status
        except MembershipVerificationError as exc:
            status = int(exc.http_status)
            body = {'success': False, 'message': exc.message}
            body.update(exc.extra)
            result_label = exc.message
            return jsonify(body), status
    finally:
        duration_ms = int((time.perf_counter() - t0) * 1000)
        try:
            oid = org_id
            if oid is None:
                oid = keys_svc.resolve_org_id_from_env() or 0
            kid = None
            if api_key_row is not None:
                try:
                    kid = int(api_key_row.id) if int(api_key_row.id) > 0 else None
                except (TypeError, ValueError):
                    kid = None
            if oid:
                keys_svc.log_access(
                    organization_id=int(oid),
                    api_key_id=kid,
                    endpoint=endpoint,
                    http_status=status,
                    result=result_label,
                    duration_ms=duration_ms,
                    client_ip=_client_ip(),
                )
        except Exception:
            pass


def register_membership_verification(app) -> None:
    from nodeone.services.integration_api_keys import (
        bootstrap_env_key_into_db_if_empty,
        ensure_api_manager_permission,
        ensure_integration_api_tables,
    )

    try:
        ensure_integration_api_tables()
        ensure_api_manager_permission()
        bootstrap_env_key_into_db_if_empty()
    except Exception:
        pass

    if 'membership_verification' not in app.blueprints:
        app.register_blueprint(membership_verification_bp)
