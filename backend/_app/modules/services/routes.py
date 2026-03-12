# Rutas de servicios (usuario): listado, solicitud de cita, API calendario.
from flask import Blueprint, request, redirect, url_for, flash, session, jsonify, render_template
from flask_login import login_required, current_user

from . import service as svc

services_bp = Blueprint('services', __name__, url_prefix='')


@services_bp.route('/services')
@login_required
def list():
    data = svc.get_services_page_data(current_user)
    return render_template(
        'services.html',
        membership=data['membership'],
        services_by_plan=data['services_by_plan'],
        plans_info=data['plans_info'],
        categories=data['categories'],
        user_membership_type=data['user_membership_type'],
        membership_type=data['membership_type'],
    )


@services_bp.route('/services/<int:service_id>/request-appointment')
@login_required
def request_appointment(service_id):
    return_url = request.args.get('return_url') or request.referrer or url_for('services.list')
    if return_url and (return_url.startswith('/') or (request.url_root and return_url.startswith(request.url_root))):
        session['appointment_return_url'] = return_url
    selected_advisor_id = request.args.get('advisor_id', type=int)
    data, err = svc.get_request_appointment_data(
        service_id, current_user,
        selected_advisor_id=selected_advisor_id,
        return_url=return_url,
    )
    if err is not None:
        redirect_url, msg, category = err
        flash(msg, category)
        return redirect(redirect_url)
    return render_template(
        'services/request_appointment.html',
        service=data['service'],
        appointment_type=data['appointment_type'],
        advisors=data['advisors'],
        selected_advisor_id=data['selected_advisor_id'],
        membership=data['membership'],
        pricing=data['pricing'],
        deposit_info=data['deposit_info'],
        available_slots_json=data['available_slots_json'],
        available_slots=data['available_slots'],
        user=data['user'],
    )


@services_bp.route('/services/<int:service_id>/request-appointment', methods=['POST'])
@login_required
def request_appointment_submit(service_id):
    result, err = svc.submit_request_appointment(service_id, current_user, request.form)
    if err is not None:
        redirect_url, msg, category = err
        flash(msg, category)
        return redirect(redirect_url)
    redirect_target, _, _ = result
    flash('Servicio agregado al carrito exitosamente. Puedes continuar con el proceso de pago desde tu carrito.', 'success')
    return redirect(url_for(redirect_target))


@services_bp.route('/api/services/<int:service_id>/calendar', methods=['GET'])
@login_required
def api_calendar(service_id):
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    advisor_id_filter = request.args.get('advisor_id', type=int)
    data, err_msg, status_code = svc.get_calendar_data(
        service_id,
        start_date=start_date,
        end_date=end_date,
        advisor_id_filter=advisor_id_filter,
    )
    if err_msg is not None:
        return jsonify({'success': False, 'error': err_msg}), status_code
    return jsonify(data)
