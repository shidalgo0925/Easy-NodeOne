"""HTTP S2S — bridge comercial ESB ↔ EN1."""

from __future__ import annotations

import time

from flask import Blueprint, g, jsonify, request

from nodeone.modules.commercial_bridge.idempotency import (
    bootstrap_idempotency_payload,
    checkout_idempotency_payload,
    ensure_idempotency_table,
    lookup_idempotent,
    normalize_idempotency_key,
    request_body_hash,
    store_idempotent,
)
from nodeone.modules.commercial_bridge.service import (
    CommercialBridgeError,
    bootstrap,
    checkout,
    ensure_dev_promo_code,
    get_entitlement,
    migrate_dev_esb_starter_to_individual,
)

commercial_bridge_bp = Blueprint('commercial_bridge', __name__)


def _keys_svc():
    from nodeone.services import integration_api_keys as keys_svc

    return keys_svc


def _client_ip() -> str | None:
    fwd = (request.headers.get('X-Forwarded-For') or '').split(',')[0].strip()
    return fwd or (request.remote_addr or None)


def _auth_api_key():
    keys_svc = _keys_svc()
    raw = keys_svc.extract_x_api_key(request)
    api_key_row, err = keys_svc.authenticate_api_key(raw)
    if err == 'not_configured':
        raise CommercialBridgeError('not_configured', 'API key no configurada', http_status=503)
    if err or api_key_row is None:
        raise CommercialBridgeError('unauthorized', 'Unauthorized', http_status=401)
    g.integration_api_key_id = getattr(api_key_row, 'id', None)
    return api_key_row


def _provider_org_id(api_key_row) -> int:
    from nodeone.core.platform.ets_provider import ets_provider_organization_id

    if api_key_row is not None and getattr(api_key_row, 'organization_id', None):
        return int(api_key_row.organization_id)
    return int(ets_provider_organization_id())


def _log(endpoint: str, status: int, result: str, api_key_row, t0: float) -> None:
    try:
        keys_svc = _keys_svc()
        oid = int(api_key_row.organization_id) if api_key_row is not None else (
            keys_svc.resolve_org_id_from_env() or 0
        )
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
                result=result,
                duration_ms=int((time.perf_counter() - t0) * 1000),
                client_ip=_client_ip(),
            )
    except Exception:
        pass


def _with_idempotency(
    *,
    operation: str,
    api_key_row,
    body: dict,
    payload_fn,
    execute_fn,
):
    """Ejecuta escritura con Idempotency-Key opcional.

    Misma key + mismo body → respuesta cacheada.
    Misma key + body distinto → ``idempotency_conflict`` (409).
    """
    key = normalize_idempotency_key(request.headers.get('Idempotency-Key'))
    org_id = _provider_org_id(api_key_row)
    if not key:
        return execute_fn(body), 200

    req_hash = request_body_hash(payload_fn(body))
    status_code, cached = lookup_idempotent(
        organization_id=org_id,
        operation=operation,
        key=key,
        request_hash=req_hash,
    )
    if status_code == 'conflict':
        raise CommercialBridgeError(
            'idempotency_conflict',
            'Idempotency-Key reutilizado con body distinto',
            http_status=409,
        )
    if status_code == 'hit' and cached is not None:
        return cached[1], int(cached[0])

    out = execute_fn(body)
    store_idempotent(
        organization_id=org_id,
        operation=operation,
        key=key,
        request_hash=req_hash,
        status=200,
        body=out,
    )
    return out, 200


@commercial_bridge_bp.route('/api/v1/commercial/bootstrap', methods=['POST'])
def commercial_bootstrap():
    t0 = time.perf_counter()
    endpoint = '/api/v1/commercial/bootstrap'
    api_key_row = None
    status = 500
    result = 'error'
    try:
        api_key_row = _auth_api_key()
        body = request.get_json(silent=True) or {}
        out, status = _with_idempotency(
            operation='bootstrap',
            api_key_row=api_key_row,
            body=body,
            payload_fn=bootstrap_idempotency_payload,
            execute_fn=bootstrap,
        )
        result = 'ok'
        keys_svc = _keys_svc()
        keys_svc.touch_key_usage(api_key_row)
        return jsonify(out), status
    except CommercialBridgeError as exc:
        status = int(exc.http_status)
        result = exc.code
        return jsonify({'error': exc.code, 'message': exc.message}), status
    finally:
        _log(endpoint, status, result, api_key_row, t0)


@commercial_bridge_bp.route('/api/v1/commercial/checkout', methods=['POST'])
def commercial_checkout():
    t0 = time.perf_counter()
    endpoint = '/api/v1/commercial/checkout'
    api_key_row = None
    status = 500
    result = 'error'
    try:
        api_key_row = _auth_api_key()
        body = request.get_json(silent=True) or {}
        out, status = _with_idempotency(
            operation='checkout',
            api_key_row=api_key_row,
            body=body,
            payload_fn=checkout_idempotency_payload,
            execute_fn=checkout,
        )
        result = 'ok'
        _keys_svc().touch_key_usage(api_key_row)
        return jsonify(out), status
    except CommercialBridgeError as exc:
        status = int(exc.http_status)
        result = exc.code
        return jsonify({'error': exc.code, 'message': exc.message}), status
    finally:
        _log(endpoint, status, result, api_key_row, t0)


@commercial_bridge_bp.route('/api/v1/commercial/entitlement', methods=['GET'])
def commercial_entitlement():
    t0 = time.perf_counter()
    endpoint = '/api/v1/commercial/entitlement'
    api_key_row = None
    status = 500
    result = 'error'
    try:
        api_key_row = _auth_api_key()
        product_code = request.args.get('product_code') or ''
        customer_id = request.args.get('customer_id')
        out = get_entitlement(product_code=product_code, customer_id=customer_id)
        status = 200
        result = 'ok' if out.get('entitled') else 'not_entitled'
        _keys_svc().touch_key_usage(api_key_row)
        return jsonify(out), status
    except CommercialBridgeError as exc:
        status = int(exc.http_status)
        result = exc.code
        return jsonify({'error': exc.code, 'message': exc.message}), status
    finally:
        _log(endpoint, status, result, api_key_row, t0)


def register_commercial_bridge(app) -> None:
    try:
        keys_svc = _keys_svc()
        keys_svc.ensure_integration_api_tables()
        keys_svc.bootstrap_env_key_into_db_if_empty()
    except Exception:
        pass
    if 'commercial_bridge' not in app.blueprints:
        app.register_blueprint(commercial_bridge_bp)
    try:
        with app.app_context():
            ensure_idempotency_table()
            ensure_dev_promo_code()
            mig = migrate_dev_esb_starter_to_individual()
            if mig.get('subscriptions_updated') or mig.get('contracts_updated'):
                print(
                    '✅ commercial_bridge DEV migrate starter→individual: '
                    f"subs={mig.get('subscriptions_updated')} "
                    f"contracts={mig.get('contracts_updated')}"
                )
    except Exception as exc:
        print(f'⚠️ commercial_bridge promo/migrate/idem seed: {exc}')
