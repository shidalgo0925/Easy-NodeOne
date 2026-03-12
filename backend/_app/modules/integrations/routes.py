# Rutas de integraciones (Office365 - usuario).
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user

from . import service as svc

integrations_bp = Blueprint('integrations', __name__, url_prefix='')


@integrations_bp.route('/office365')
@login_required
def office365_page():
    data = svc.get_page_data(current_user)
    return render_template(
        'office365.html',
        membership=data['membership'],
        is_pro_or_above=data['is_pro_or_above'],
        policy_correo=data.get('policy_correo'),
        must_accept_email_policy=data.get('must_accept_email_policy', False),
        checkbox_politica_correo=data.get('checkbox_politica_correo', ''),
    )


@integrations_bp.route('/api/office365/request', methods=['POST'])
@login_required
def api_office365_request():
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Content-Type debe ser application/json'}), 400
    data = request.get_json()
    result, err = svc.submit_request(current_user, data, request=request)
    if err is not None:
        payload, status_code = err
        return jsonify(payload), status_code
    return jsonify(result)
