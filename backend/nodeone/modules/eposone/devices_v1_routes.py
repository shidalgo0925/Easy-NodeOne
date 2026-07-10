"""API v1 dispositivos EPosOne — Hito EN1-02 (código = destino)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from nodeone.modules.eposone.device_provisioning import (
    DeviceProvisioningError,
    DeviceProvisioningService,
)

eposone_devices_v1_bp = Blueprint(
    'eposone_devices_v1',
    __name__,
    url_prefix='/api/v1/devices',
)


def _provisioning_code_from_request() -> str | None:
    return (
        request.headers.get('X-EN1-Provisioning-Code')
        or request.headers.get('X-EPosOne-Provisioning-Code')
        or (request.get_json(silent=True) or {}).get('provisioning_code')
    )


@eposone_devices_v1_bp.route('/register', methods=['POST'])
def devices_register():
    """Contrato oficial EN1-02: device_uuid + metadatos + código de destino.

    Legacy EN1-01: si el body incluye organization_id + branch/pos/register_ref
    y el código es el de org, sigue funcionando.
    """
    body = request.get_json(silent=True) or {}
    try:
        result = DeviceProvisioningService.register(
            provisioning_code=_provisioning_code_from_request(),
            device_uuid=str(body.get('device_uuid') or body.get('uuid') or ''),
            organization_id=body.get('organization_id'),
            organization_ref=body.get('organization_ref') or body.get('organization_slug'),
            branch_ref=(body.get('branch_ref') or body.get('branch_id') or None),
            pos_ref=(body.get('pos_ref') or body.get('pos_id') or None),
            register_ref=(
                body.get('register_ref') or body.get('register_id') or body.get('caja_ref') or None
            ),
            device_name=body.get('device_name') or body.get('name'),
            platform=body.get('platform'),
            device_model=body.get('device_model') or body.get('model'),
            android_version=body.get('android_version'),
            app_version=body.get('app_version'),
        )
    except DeviceProvisioningError as exc:
        return jsonify({'error': exc.code}), int(exc.http_status)
    return jsonify(result), 201


@eposone_devices_v1_bp.route('/config', methods=['GET'])
def devices_config():
    try:
        row = DeviceProvisioningService.authenticate_bearer(request.headers.get('Authorization'))
        config = DeviceProvisioningService.get_config_for_terminal(row)
    except DeviceProvisioningError as exc:
        return jsonify({'error': exc.code}), int(exc.http_status)
    return jsonify(config)
