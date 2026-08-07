"""API v1 Activación — ADR-035 v1.4 (validate / redeem email+código / reissue)."""

from __future__ import annotations

import io

from flask import Blueprint, jsonify, request, send_file
from flask_login import current_user, login_required

from nodeone.core.platform.activation_service import ActivationError, ActivationService

eposone_activation_v1_bp = Blueprint(
    'eposone_activation_v1',
    __name__,
    url_prefix='/api/v1/activation',
)


def _err(exc: ActivationError):
    return jsonify({'ok': False, 'error': exc.code, 'message': exc.message}), int(exc.http_status)


@eposone_activation_v1_bp.route('/validate', methods=['POST'])
def activation_validate():
    body = request.get_json(silent=True) or {}
    try:
        data = ActivationService.validate(
            credentials=body,
            product_code=body.get('product_code') or 'eposone',
        )
    except ActivationError as exc:
        return _err(exc)
    return jsonify(data), 200


@eposone_activation_v1_bp.route('/redeem', methods=['POST'])
def activation_redeem():
    body = request.get_json(silent=True) or {}
    try:
        data = ActivationService.redeem(
            credentials=body,
            device_uuid=str(body.get('device_uuid') or ''),
            product_code=body.get('product_code') or 'eposone',
        )
    except ActivationError as exc:
        return _err(exc)
    return jsonify(data), 200


@eposone_activation_v1_bp.route('/licenses', methods=['POST'])
@login_required
def activation_create_license():
    body = request.get_json(silent=True) or {}
    try:
        oid = int(body.get('organization_id') or 0)
        if oid <= 0:
            raise ActivationError('activation_token_invalid', http_status=400, message='organization_id_required')
        lic = ActivationService.ensure_license(
            organization_id=oid,
            modality=str(body.get('modality') or ''),
            implementation_strategy=body.get('implementation_strategy'),
            product_code=str(body.get('product_code') or 'eposone'),
            contract_id=body.get('contract_id'),
            subscription_id=body.get('subscription_id'),
            user_id=getattr(current_user, 'id', None),
            metadata=body.get('metadata') if isinstance(body.get('metadata'), dict) else None,
        )
    except ActivationError as exc:
        return _err(exc)
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'error': 'activation_token_invalid'}), 400
    return jsonify({
        'ok': True,
        'license_id': int(lic.id),
        'organization_id': int(lic.organization_id),
        'modality': lic.modality,
        'implementation_strategy': lic.implementation_strategy,
        'status': lic.status,
        'product_code': lic.product_code,
    }), 201


@eposone_activation_v1_bp.route('/reissue', methods=['POST'])
@login_required
def activation_reissue():
    """Reemite código Standalone sobre la misma licencia (ADR-035 v1.4)."""
    body = request.get_json(silent=True) or {}
    try:
        oid = int(body.get('organization_id') or 0)
        if oid <= 0:
            # Inferir org del usuario si no viene
            oid = int(getattr(current_user, 'organization_id', 0) or 0)
        if oid <= 0:
            raise ActivationError(
                'activation_token_invalid',
                http_status=400,
                message='organization_id_required',
            )
        email = (body.get('email') or getattr(current_user, 'email', '') or '').strip().lower()
        if not email:
            raise ActivationError(
                'activation_credential_missing',
                http_status=400,
                message='email_required',
            )
        send_email = bool(body.get('send_email', True))
        data = ActivationService.reissue_standalone_for_organization(
            organization_id=oid,
            bound_email=email,
            user_id=getattr(current_user, 'id', None),
            send_email=send_email,
            organization_name=body.get('organization_name'),
        )
    except ActivationError as exc:
        return _err(exc)
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'error': 'activation_token_invalid'}), 400
    return jsonify({'ok': True, **data}), 201


@eposone_activation_v1_bp.route('/tokens', methods=['POST'])
@login_required
def activation_issue_token():
    body = request.get_json(silent=True) or {}
    try:
        license_id = int(body.get('license_id') or 0)
        if license_id <= 0:
            raise ActivationError('license_revoked', http_status=400, message='license_id_required')
        data = ActivationService.issue_token(
            license_id=license_id,
            ttl_days=body.get('ttl_days'),
            max_uses=int(body.get('max_uses') or 1),
            register_ref=body.get('register_ref'),
            user_id=getattr(current_user, 'id', None),
            ops_ready=body.get('ops_ready'),
            bound_email=body.get('bound_email') or getattr(current_user, 'email', None),
        )
    except ActivationError as exc:
        return _err(exc)
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'error': 'activation_token_invalid'}), 400
    return jsonify({'ok': True, **data}), 201


@eposone_activation_v1_bp.route('/tokens/<int:token_id>/revoke', methods=['POST'])
@login_required
def activation_revoke_token(token_id: int):
    body = request.get_json(silent=True) or {}
    try:
        ActivationService.revoke_token(token_id, reason=body.get('reason'))
    except ActivationError as exc:
        return _err(exc)
    return jsonify({'ok': True, 'token_id': token_id, 'status': 'revoked'}), 200


@eposone_activation_v1_bp.route('/licenses/<int:license_id>/revoke', methods=['POST'])
@login_required
def activation_revoke_license(license_id: int):
    body = request.get_json(silent=True) or {}
    try:
        ActivationService.revoke_license(license_id, reason=body.get('reason'))
    except ActivationError as exc:
        return _err(exc)
    return jsonify({'ok': True, 'license_id': license_id, 'status': 'revoked'}), 200


@eposone_activation_v1_bp.route('/tokens/<int:token_id>/qr.png', methods=['GET'])
@login_required
def activation_token_qr(token_id: int):
    """QR técnico = App Link (secundario ADR-035 v1.4), no /start."""
    from models.ets_activation_license import EtsActivationLicense
    from models.ets_activation_token import EtsActivationToken

    tok = EtsActivationToken.query.get(int(token_id))
    if tok is None:
        return jsonify({'ok': False, 'error': 'activation_token_invalid'}), 404
    lic = EtsActivationLicense.query.get(int(tok.license_id))
    if lic is None:
        return jsonify({'ok': False, 'error': 'license_revoked'}), 404
    pub = ActivationService._token_public(tok, lic)
    try:
        import qrcode

        img = qrcode.make(pub['app_link'])
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return send_file(buf, mimetype='image/png', download_name=f'activation-{token_id}.png')
    except Exception:
        return jsonify({'ok': False, 'error': 'qr_unavailable', 'app_link': pub['app_link']}), 501
