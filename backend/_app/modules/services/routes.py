# Rutas de servicios (usuario): listado, solicitud de cita, API calendario.
from flask import Blueprint, request, redirect, url_for, flash, session, jsonify, render_template
from flask_login import login_required, current_user

from utils.organization import resolve_current_organization

from app import db

from . import service as svc

services_bp = Blueprint('services', __name__, url_prefix='')


@services_bp.route('/services')
def list():
    """
    Catálogo: visible sin login (vitrina por tenant vía subdominio).
    Solicitar cita sigue exigiendo sesión en las rutas correspondientes.
    """
    oid = resolve_current_organization()
    user = current_user if getattr(current_user, 'is_authenticated', False) else None
    data = svc.get_services_page_data(user, organization_id=oid)
    return render_template(
        'services.html',
        membership=data['membership'],
        services_by_plan=data['services_by_plan'],
        services_unique=data['services_unique'],
        featured_events=data.get('featured_events') or [],
        plans_info=data['plans_info'],
        categories=data['categories'],
        user_membership_type=data['user_membership_type'],
        membership_type=data['membership_type'],
        plan_slugs_ordered=data['plan_slugs_ordered'],
    )


@services_bp.route('/services/<int:service_id>/begin-consultive-flow')
@login_required
def begin_consultive_flow(service_id):
    """
    Fase consultiva: crea ``ServiceRequest`` (requested) y redirige al flujo de agenda o primera reunión.
    """
    from nodeone.services.commercial_flow import COMMERCIAL_FLOW_SERVICE_CONSULTATIVE, resolve_commercial_flow_type
    from _app.modules.services import repository
    from models.service_request import ServiceRequest

    service = repository.get_service_or_404(service_id)
    if not service.is_active:
        flash('Este servicio no está disponible.', 'error')
        return redirect(url_for('services.list'))
    membership = current_user.get_active_membership()
    if not membership:
        flash('Necesitás una membresía activa para continuar.', 'warning')
        return redirect(url_for('services.list'))
    pricing = service.pricing_for_membership(membership.membership_type)
    flow = resolve_commercial_flow_type(service, pricing)
    if flow != COMMERCIAL_FLOW_SERVICE_CONSULTATIVE:
        flash('Este ítem no requiere este flujo de solicitud.', 'info')
        return redirect(url_for('services.list'))
    oid = int(getattr(service, 'organization_id', None) or 1)
    sr = ServiceRequest(
        organization_id=oid,
        user_id=int(current_user.id),
        service_id=int(service.id),
        status='requested',
    )
    db.session.add(sr)
    db.session.commit()
    session['pending_service_request_id'] = int(sr.id)
    st = (getattr(service, 'service_type', None) or '').strip().upper()
    if st == 'CONSULTIVO':
        return redirect(url_for('appointments.request_appointment', service_id=service.id))
    return redirect(url_for('services.request_appointment', service_id=service.id))


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
    redirect_target, flash_msg, flash_category = result
    if flash_msg:
        flash(flash_msg, flash_category or 'success')
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
