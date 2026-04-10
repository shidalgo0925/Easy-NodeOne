# Rutas de integraciones (Office365 - usuario).
from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import current_user, login_required

from nodeone.services.office365_module import is_office365_module_enabled_for_org
from nodeone.services.org_scope import org_id_for_module_visibility

from . import service as svc

integrations_bp = Blueprint('integrations', __name__, url_prefix='')


def _require_office365_for_current_org():
    if not is_office365_module_enabled_for_org(org_id_for_module_visibility()):
        abort(404)


@integrations_bp.route('/office365')
@login_required
def office365_page():
    _require_office365_for_current_org()
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
    _require_office365_for_current_org()
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Content-Type debe ser application/json'}), 400
    data = request.get_json()
    result, err = svc.submit_request(current_user, data, request=request)
    if err is not None:
        payload, status_code = err
        return jsonify(payload), status_code
    return jsonify(result)
