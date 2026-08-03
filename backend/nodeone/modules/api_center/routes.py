"""API Center UI — APIs Disponibles, Keys, Explorer, Registro."""

from __future__ import annotations

import time
from functools import wraps

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user

from nodeone.modules.membership_verification.catalog import (
    API_CATALOG,
    PERMISSION_API_MANAGER,
    SUPPORTED_VERIFICATION_TYPES,
)

api_center_bp = Blueprint('api_center', __name__)


def _api_manager_required(f):
    """Lazy: no importar ``app`` al decorar (evita circular en register_modules)."""

    @wraps(f)
    def wrapped(*args, **kwargs):
        import app as M

        return M.require_permission(PERMISSION_API_MANAGER)(f)(*args, **kwargs)

    return wrapped


def _org_id() -> int:
    from utils.organization import get_admin_effective_organization_id

    return int(get_admin_effective_organization_id())


def _fmt_dt(dt) -> str:
    if not dt:
        return '—'
    try:
        return dt.strftime('%d/%m/%Y %H:%M:%S')
    except Exception:
        return str(dt)


def _keys_svc():
    from nodeone.services import integration_api_keys as keys_svc

    return keys_svc


@api_center_bp.route('/admin/api-center')
@api_center_bp.route('/admin/api-center/apis')
@_api_manager_required
def apis_available():
    return render_template(
        'admin/api_center/apis.html',
        apis=list(API_CATALOG),
        page='apis',
    )


@api_center_bp.route('/admin/api-center/keys')
@_api_manager_required
def api_keys():
    oid = _org_id()
    rows = _keys_svc().list_api_keys(oid)
    return render_template(
        'admin/api_center/keys.html',
        keys=rows,
        page='keys',
        fmt_dt=_fmt_dt,
    )


@api_center_bp.route('/admin/api-center/keys', methods=['POST'])
@_api_manager_required
def api_keys_create():
    keys_svc = _keys_svc()
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'name_required'}), 400
    description = (data.get('description') or '').strip() or None
    uid = getattr(current_user, 'id', None)
    row, raw = keys_svc.create_api_key(
        organization_id=_org_id(),
        name=name,
        description=description,
        created_by_user_id=int(uid) if uid else None,
    )
    return jsonify(
        {
            'success': True,
            'key': keys_svc.key_public_dict(row),
            'raw_key': raw,
            'message': 'Guarda la clave ahora; no se volverá a mostrar.',
        }
    ), 201


@api_center_bp.route('/admin/api-center/keys/<int:key_id>/regenerate', methods=['POST'])
@_api_manager_required
def api_keys_regenerate(key_id: int):
    keys_svc = _keys_svc()
    row = keys_svc.get_api_key_for_org(key_id, _org_id())
    if row is None:
        return jsonify({'success': False, 'message': 'not_found'}), 404
    raw = keys_svc.regenerate_api_key(row)
    return jsonify(
        {
            'success': True,
            'key': keys_svc.key_public_dict(row),
            'raw_key': raw,
            'message': 'Clave regenerada. Guárdala ahora; no se volverá a mostrar.',
        }
    )


@api_center_bp.route('/admin/api-center/keys/<int:key_id>/status', methods=['POST'])
@_api_manager_required
def api_keys_status(key_id: int):
    keys_svc = _keys_svc()
    data = request.get_json(silent=True) or {}
    status = (data.get('status') or '').strip().lower()
    row = keys_svc.get_api_key_for_org(key_id, _org_id())
    if row is None:
        return jsonify({'success': False, 'message': 'not_found'}), 404
    try:
        keys_svc.set_api_key_status(row, status)
    except ValueError:
        return jsonify({'success': False, 'message': 'invalid_status'}), 400
    return jsonify({'success': True, 'key': keys_svc.key_public_dict(row)})


@api_center_bp.route('/admin/api-center/explorer')
@_api_manager_required
def api_explorer():
    oid = _org_id()
    rows = [
        k
        for k in _keys_svc().list_api_keys(oid)
        if (k.status or '').lower() == 'active'
    ]
    membership = next(
        (a for a in API_CATALOG if a.get('id') == 'membership_verification'),
        API_CATALOG[0] if API_CATALOG else None,
    )
    return render_template(
        'admin/api_center/explorer.html',
        apis=list(API_CATALOG),
        keys=rows,
        membership_api=membership,
        supported_types=sorted(SUPPORTED_VERIFICATION_TYPES),
        page='explorer',
    )


@api_center_bp.route('/admin/api-center/explorer/execute', methods=['POST'])
@_api_manager_required
def api_explorer_execute():
    """Ejecuta Membership Verification en nombre del org (sin revelar hash)."""
    from nodeone.services.membership_verification import (
        MembershipVerificationError,
        verify,
    )

    keys_svc = _keys_svc()
    data = request.get_json(silent=True) or {}
    api_id = (data.get('api_id') or 'membership_verification').strip()
    vtype = (data.get('type') or 'email').strip()
    value = data.get('value')
    key_id = data.get('key_id')
    raw_key = (data.get('raw_key') or '').strip()

    catalog_entry = next((a for a in API_CATALOG if a.get('id') == api_id), None)
    if catalog_entry is None:
        return jsonify({'success': False, 'message': 'unknown_api'}), 400

    oid = _org_id()
    key_row = None
    auth_mode = 'org_session'

    if raw_key:
        key_row, err = keys_svc.authenticate_api_key(raw_key)
        if err or key_row is None:
            return jsonify(
                {
                    'success': True,
                    'http_status': 401,
                    'body': {'success': False, 'message': 'Unauthorized'},
                    'duration_ms': 0,
                    'auth_mode': 'x_api_key',
                }
            )
        if int(key_row.organization_id) != oid and getattr(key_row, 'id', 0):
            return jsonify({'success': False, 'message': 'key_org_mismatch'}), 403
        oid = int(key_row.organization_id)
        auth_mode = 'x_api_key'
    elif key_id:
        key_row = keys_svc.get_api_key_for_org(int(key_id), oid)
        if key_row is None:
            return jsonify({'success': False, 'message': 'key_not_found'}), 404
        if (key_row.status or '').lower() != 'active':
            return jsonify({'success': False, 'message': 'key_not_active'}), 400

    t0 = time.perf_counter()
    endpoint = catalog_entry.get('path') or '/api/v1/membership/verification'
    result_label = 'error'
    status = 500
    body: dict = {'success': False, 'message': 'error'}

    try:
        body = verify(
            type=str(vtype or ''),
            value=str(value if value is not None else ''),
            organization_id=oid,
        )
        status = 200
        if not body.get('found'):
            result_label = 'not_found'
        elif (body.get('member') or {}).get('is_active_member'):
            result_label = 'found_active'
        else:
            result_label = 'found_inactive'
        if key_row is not None and getattr(key_row, 'id', 0):
            keys_svc.touch_key_usage(key_row)
    except MembershipVerificationError as exc:
        status = int(exc.http_status)
        body = {'success': False, 'message': exc.message}
        body.update(exc.extra)
        result_label = exc.message

    duration_ms = int((time.perf_counter() - t0) * 1000)
    try:
        kid = int(key_row.id) if key_row is not None and int(key_row.id) > 0 else None
    except (TypeError, ValueError):
        kid = None
    keys_svc.log_access(
        organization_id=oid,
        api_key_id=kid,
        endpoint=f'{endpoint}#explorer',
        http_status=status,
        result=f'explorer:{result_label}',
        duration_ms=duration_ms,
        client_ip=(request.remote_addr or None),
    )

    return jsonify(
        {
            'success': True,
            'http_status': status,
            'body': body,
            'duration_ms': duration_ms,
            'auth_mode': auth_mode,
            'endpoint': endpoint,
            'method': catalog_entry.get('method') or 'POST',
        }
    )


@api_center_bp.route('/admin/api-center/logs')
@_api_manager_required
def api_logs():
    keys_svc = _keys_svc()
    oid = _org_id()
    rows = keys_svc.list_access_logs(oid, limit=200)
    key_map = {k.id: k for k in keys_svc.list_api_keys(oid)}
    return render_template(
        'admin/api_center/logs.html',
        logs=rows,
        key_map=key_map,
        page='logs',
        fmt_dt=_fmt_dt,
    )


def register_api_center(app) -> None:
    try:
        keys_svc = _keys_svc()
        keys_svc.ensure_integration_api_tables()
        keys_svc.ensure_api_manager_permission()
    except Exception:
        pass
    if 'api_center' not in app.blueprints:
        app.register_blueprint(api_center_bp)
