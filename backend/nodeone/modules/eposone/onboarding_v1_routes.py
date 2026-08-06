"""API v1 Onboarding Login — Camino B/D (ADR-027 / LOGIN_CONTRACT_V1)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from nodeone.modules.eposone.onboarding_auth_service import (
    OnboardingAuthError,
    authenticate_bearer,
    build_onboarding_session_payload,
    issue_provisioning_code_for_user,
    load_user,
    login_with_password,
)

eposone_onboarding_v1_bp = Blueprint(
    'eposone_onboarding_v1',
    __name__,
    url_prefix='/api/v1/onboarding',
)


def _err(exc: OnboardingAuthError):
    return jsonify({'error': exc.code}), int(exc.http_status)


@eposone_onboarding_v1_bp.route('/login', methods=['POST'])
def onboarding_login():
    """POST email+password → access_token + Onboarding Session Payload."""
    body = request.get_json(silent=True) or {}
    try:
        oid_raw = body.get('organization_id')
        oid = int(oid_raw) if oid_raw is not None and str(oid_raw).strip() != '' else None
    except (TypeError, ValueError):
        return jsonify({'error': 'invalid_organization_id'}), 400
    try:
        result = login_with_password(
            str(body.get('email') or ''),
            str(body.get('password') or ''),
            organization_id=oid,
        )
    except OnboardingAuthError as exc:
        return _err(exc)
    return jsonify(result), 200


@eposone_onboarding_v1_bp.route('/session', methods=['GET'])
def onboarding_session():
    """GET Bearer → refresca Onboarding Session Payload (opcional organization_id)."""
    try:
        auth = authenticate_bearer(request.headers.get('Authorization'))
        user = load_user(int(auth['user_id']))
        oid_raw = request.args.get('organization_id')
        oid = None
        if oid_raw is not None and str(oid_raw).strip() != '':
            oid = int(oid_raw)
        elif auth.get('organization_id'):
            oid = int(auth['organization_id'])
        payload = build_onboarding_session_payload(user, organization_id=oid)
    except OnboardingAuthError as exc:
        return _err(exc)
    except (TypeError, ValueError):
        return jsonify({'error': 'invalid_organization_id'}), 400
    return jsonify(payload), 200


@eposone_onboarding_v1_bp.route('/issue-code', methods=['POST'])
def onboarding_issue_code():
    """POST Bearer + register_ref → provisioning code EN1-02 (Camino C interno)."""
    body = request.get_json(silent=True) or {}
    try:
        auth = authenticate_bearer(request.headers.get('Authorization'))
        user = load_user(int(auth['user_id']))
        oid_raw = body.get('organization_id') or auth.get('organization_id')
        if oid_raw is None:
            raise OnboardingAuthError('organization_id_required', 400)
        oid = int(oid_raw)
        result = issue_provisioning_code_for_user(
            user,
            organization_id=oid,
            register_ref=str(body.get('register_ref') or ''),
        )
    except OnboardingAuthError as exc:
        return _err(exc)
    except (TypeError, ValueError):
        return jsonify({'error': 'invalid_organization_id'}), 400
    return jsonify(result), 201
