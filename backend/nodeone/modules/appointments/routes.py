#!/usr/bin/env python3
"""
Citas (appointments): miembros, asesores y admin.

Ubicación modular: nodeone.modules.appointments.routes
Compat: appointment_routes reexporta estos blueprints.
"""

from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from nodeone.services.communication_dispatch import request_base_url_optional
from nodeone.modules.appointments.services import (
    appt_platform_admin as _svc_appt_platform_admin,
    appointment_types_scoped_query as _svc_appointment_types_scoped_query,
    appointments_scoped_query as _svc_appointments_scoped_query,
    advisors_scoped_query as _svc_advisors_scoped_query,
    get_admin_availability_payload,
    org_filter_appt_optional as _svc_org_filter_appt_optional,
    require_appointment_by_id as _svc_require_appointment_by_id,
    require_appointment_slot_in_scope as _svc_require_appointment_slot_in_scope,
    require_appointment_type_by_id as _svc_require_appointment_type_by_id,
    slot_queryset as _svc_slot_queryset,
    tenant_org_appt as _svc_tenant_org_appt,
)

# Blueprints
appointments_bp = Blueprint('appointments', __name__, url_prefix='/appointments')
admin_appointments_bp = Blueprint('admin_appointments', __name__, url_prefix='/admin/appointments')
appointments_api_bp = Blueprint('appointments_api', __name__, url_prefix='/api/appointments')
# Rutas que conservan URLs históricas fuera de /api/appointments (antes en app.py).
appointments_http_legacy_bp = Blueprint('appointments_http_legacy', __name__)

# Model references (se inicializan perezosamente para evitar import circular)
db = None
User = None
Advisor = None
AppointmentType = None
AppointmentAdvisor = None
AppointmentSlot = None
Appointment = None
AppointmentParticipant = None
AppointmentPricing = None
AdvisorAvailability = None
AdvisorServiceAvailability = None
ActivityLog = None
Service = None
Notification = None
Proposal = None


def init_models():
    """Importa modelos desde app.py cuando sea necesario."""
    global db
    global User
    global Advisor
    global AppointmentType
    global AppointmentAdvisor
    global AppointmentSlot
    global Appointment
    global AppointmentParticipant
    global AppointmentPricing
    global AdvisorAvailability
    global AdvisorServiceAvailability
    global DailyServiceAvailability
    global ActivityLog
    global Service
    global Notification
    global Proposal

    if db is not None:
        return

    from nodeone.modules.appointments.models import load_appointment_context

    ctx = load_appointment_context()
    db = ctx['db']
    User = ctx['User']
    Advisor = ctx['Advisor']
    AppointmentType = ctx['AppointmentType']
    AppointmentAdvisor = ctx['AppointmentAdvisor']
    AppointmentSlot = ctx['AppointmentSlot']
    Appointment = ctx['Appointment']
    AppointmentParticipant = ctx['AppointmentParticipant']
    AppointmentPricing = ctx['AppointmentPricing']
    AdvisorAvailability = ctx['AdvisorAvailability']
    AdvisorServiceAvailability = ctx['AdvisorServiceAvailability']
    DailyServiceAvailability = ctx['DailyServiceAvailability']
    ActivityLog = ctx['ActivityLog']
    Service = ctx['Service']
    Notification = ctx['Notification']
    Proposal = ctx['Proposal']
    globals()['Proposal'] = Proposal


def ensure_models():
    if db is None:
        init_models()


def admin_required(f):
    """Decorator para vistas administrativas."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('No tienes permisos para acceder a esta sección.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)

    return decorated_function


def _active_membership_or_warning():
    """Devuelve la membresía activa del usuario o None, mostrando advertencia."""
    membership = current_user.get_active_membership()
    if not membership:
        flash('Necesitas una membresía activa para reservar citas. Revisa tus planes disponibles.', 'warning')
    return membership


def _tenant_org_appt():
    return _svc_tenant_org_appt()


def _appt_platform_admin():
    return _svc_appt_platform_admin()


def _org_filter_appt_optional():
    return _svc_org_filter_appt_optional()


def _appointment_types_scoped_query():
    ensure_models()
    return _svc_appointment_types_scoped_query(AppointmentType)


def _require_appointment_type_by_id(type_id):
    ensure_models()
    return _svc_require_appointment_type_by_id(type_id, AppointmentType)


def _require_appointment_slot_in_scope(slot_id):
    ensure_models()
    return _svc_require_appointment_slot_in_scope(
        slot_id,
        AppointmentSlot,
        _require_appointment_type_by_id,
    )


def _appointments_scoped_query():
    ensure_models()
    return _svc_appointments_scoped_query(Appointment)


def _require_appointment_by_id(appt_id):
    ensure_models()
    return _svc_require_appointment_by_id(appt_id, Appointment)


def _advisors_scoped_query():
    ensure_models()
    return _svc_advisors_scoped_query(Advisor, User)


def _slot_queryset():
    ensure_models()
    return _svc_slot_queryset(AppointmentSlot, AppointmentType)


@appointments_bp.route('/my-requests')
@login_required
def my_requests():
    """Fase 8: Mis solicitudes = solo PENDIENTES y RECHAZADAS (confirmadas van en Mis citas)."""
    ensure_models()
    requests_list = Appointment.query.filter(
        Appointment.user_id == current_user.id,
        Appointment.organization_id == _tenant_org_appt(),
        Appointment.status.in_(['PENDIENTE', 'RECHAZADA', 'pending'])
    ).order_by(Appointment.created_at.desc()).limit(50).all()
    from app import SaasOrganization
    _roid = {a.appointment_type.organization_id for a in requests_list if a.appointment_type}
    _rorg = (
        {o.id: (o.name or '').strip() for o in SaasOrganization.query.filter(SaasOrganization.id.in_(_roid)).all()}
        if _roid
        else {}
    )
    return render_template(
        'appointments/my_requests.html',
        requests_list=requests_list,
        appt_tenant_names=_rorg,
    )


@appointments_bp.route('/')
@login_required
def appointments_home():
    ensure_models()
    membership = current_user.get_active_membership()
    membership_type = membership.membership_type if membership else None

    appointment_types = _appointment_types_scoped_query().filter_by(is_active=True).order_by(AppointmentType.display_order.asc()).all()
    types_with_pricing = [
        (appt_type, appt_type.pricing_for_membership(membership_type))
        for appt_type in appointment_types
    ]
    from app import SaasOrganization
    _oids = {t.organization_id for t in appointment_types}
    _org_by_id = (
        {o.id: o for o in SaasOrganization.query.filter(SaasOrganization.id.in_(_oids)).all()}
        if _oids
        else {}
    )
    types_with_pricing = [(t, p, _org_by_id.get(t.organization_id)) for t, p in types_with_pricing]

    upcoming = Appointment.query.filter(
        Appointment.user_id == current_user.id,
        Appointment.organization_id == _tenant_org_appt(),
        Appointment.start_datetime >= datetime.utcnow()
    ).order_by(Appointment.start_datetime.asc()).all()

    past = Appointment.query.filter(
        Appointment.user_id == current_user.id,
        Appointment.organization_id == _tenant_org_appt(),
        Appointment.start_datetime < datetime.utcnow()
    ).order_by(Appointment.start_datetime.desc()).limit(5).all()

    appt_org_names = {}
    _all_member_appts = upcoming + past
    _appt_oids = {a.appointment_type.organization_id for a in _all_member_appts if a.appointment_type}
    _appt_orgs = (
        {o.id: o for o in SaasOrganization.query.filter(SaasOrganization.id.in_(_appt_oids)).all()}
        if _appt_oids
        else {}
    )
    for a in _all_member_appts:
        if a.appointment_type:
            o = _appt_orgs.get(a.appointment_type.organization_id)
            appt_org_names[a.id] = (o.name or '').strip() if o else ''

    return render_template(
        'appointments/index.html',
        membership=membership,
        types_with_pricing=types_with_pricing,
        upcoming_appointments=upcoming,
        past_appointments=past,
        appt_org_names=appt_org_names,
    )


@appointments_bp.route('/type/<int:type_id>')
@login_required
def appointment_type_detail(type_id):
    ensure_models()
    membership = current_user.get_active_membership()
    membership_type = membership.membership_type if membership else None

    appointment_type = _require_appointment_type_by_id(type_id)
    pricing = appointment_type.pricing_for_membership(membership_type)
    advisors = [
        assignment.advisor for assignment in appointment_type.advisor_assignments
        if assignment.is_active and assignment.advisor.is_active
    ]

    available_slots = _slot_queryset().filter(
        AppointmentSlot.appointment_type_id == appointment_type.id,
        AppointmentSlot.is_available == True  # noqa
    ).limit(20).all()

    from app import SaasOrganization
    tenant_org = SaasOrganization.query.get(appointment_type.organization_id)

    return render_template(
        'appointments/type_detail.html',
        appointment_type=appointment_type,
        tenant_org=tenant_org,
        advisors=advisors,
        pricing=pricing,
        slots=available_slots,
        membership=membership,
    )


@appointments_bp.route('/book/<int:slot_id>', methods=['POST'])
@login_required
def book_appointment(slot_id):
    ensure_models()
    membership = _active_membership_or_warning()
    if membership is None:
        return redirect(request.referrer or url_for('appointments.appointments_home'))

    slot = _require_appointment_slot_in_scope(slot_id)
    if not slot.is_available or slot.remaining_seats() <= 0:
        flash('Este horario ya no está disponible. Intenta con otro slot.', 'warning')
        return redirect(url_for('appointments.appointment_type_detail', type_id=slot.appointment_type_id))

    notes = request.form.get('notes', '').strip()
    membership_type = membership.membership_type if membership else None
    pricing = slot.appointment_type.pricing_for_membership(membership_type)
    base_price = pricing['base_price']
    final_price = pricing['final_price']
    discount = max(0.0, base_price - final_price)

    appointment = Appointment(
        appointment_type_id=slot.appointment_type_id,
        organization_id=int(getattr(slot.appointment_type, 'organization_id', None) or 1),
        advisor_id=slot.advisor_id,
        slot_id=slot.id,
        user_id=current_user.id,
        membership_type=membership_type,
        is_group=slot.capacity > 1,
        start_datetime=slot.start_datetime,
        end_datetime=slot.end_datetime,
        status='pending',
        base_price=base_price,
        final_price=final_price,
        discount_applied=discount,
        user_notes=notes,
    )

    slot.reserved_seats = (slot.reserved_seats or 0) + 1
    if slot.remaining_seats() == 0:
        slot.is_available = False

    db.session.add(appointment)
    db.session.commit()

    ActivityLog.log_activity(
        current_user.id,
        'book_appointment',
        'appointment',
        appointment.id,
        f'Reservó la cita {appointment.reference}',
        request
    )

    flash('Tu cita fue registrada y está pendiente de confirmación del asesor.', 'success')
    return redirect(url_for('appointments.appointments_home'))


@appointments_bp.route('/request', methods=['GET', 'POST'])
@login_required
def request_appointment():
    """
    Fase 2: Solicitar primera reunión sin validar calendario.
    GET: formulario (service_id en query). POST: crear cita PENDIENTE.
    Solicitar primera reunión: no exige membresía activa.
    """
    ensure_models()
    membership = current_user.get_active_membership() if current_user else None

    if request.method == 'GET':
        service_id = request.args.get('service_id', type=int)
        if not service_id:
            flash('Indica el servicio.', 'error')
            return redirect(url_for('services.list'))
        from app import _catalog_org_for_member_and_theme
        _svc_org = int(_catalog_org_for_member_and_theme())
        service = Service.query.filter_by(id=service_id, organization_id=_svc_org).first()
        if not service:
            flash('Servicio no encontrado.', 'error')
            return redirect(url_for('services.list'))
        if not (service.appointment_type_id or service.diagnostic_appointment_type_id):
            flash('Este servicio no tiene citas configuradas.', 'error')
            return redirect(url_for('services.list'))
        at_id = service.appointment_type_id or service.diagnostic_appointment_type_id
        _require_appointment_type_by_id(at_id)
        advisors_for_service = [
            a.advisor for a in AppointmentAdvisor.query.filter_by(
                appointment_type_id=at_id, is_active=True
            ).all() if a.advisor and getattr(a.advisor, 'is_active', True) and a.advisor.user
        ]
        from datetime import date
        min_date = date.today().isoformat()
        return render_template('appointments/request_first_meeting.html', service=service, min_date=min_date, advisors_for_service=advisors_for_service)

    data = request.get_json(silent=True) or request.form
    service_id = data.get('service_id', type=int)
    proposed_datetime_str = data.get('proposed_datetime') or (data.get('proposed_date') and data.get('proposed_time') and f"{data.get('proposed_date')}T{data.get('proposed_time')}:00")
    notes = (data.get('notes') or data.get('user_notes') or '').strip()

    if not service_id:
        if request.is_json:
            return jsonify({'success': False, 'error': 'service_id requerido.'}), 400
        flash('Servicio no indicado.', 'error')
        return redirect(request.referrer or url_for('services.list'))
    if not proposed_datetime_str:
        if request.is_json:
            return jsonify({'success': False, 'error': 'proposed_datetime (o proposed_date + proposed_time) requerido.'}), 400
        flash('Indica fecha y hora deseadas.', 'error')
        return redirect(request.referrer or url_for('services.list'))

    s = (proposed_datetime_str or '').strip().replace('T', ' ')[:19]
    start_dt = None
    for fmt, size in (('%Y-%m-%d %H:%M:%S', 19), ('%Y-%m-%d %H:%M', 16), ('%Y-%m-%d', 10)):
        try:
            start_dt = datetime.strptime(s[:size], fmt)
            if fmt == '%Y-%m-%d':
                start_dt = start_dt.replace(hour=9, minute=0, second=0, microsecond=0)
            break
        except (ValueError, TypeError):
            continue
    if not start_dt or start_dt <= datetime.utcnow():
        if request.is_json:
            return jsonify({'success': False, 'error': 'Fecha/hora debe ser futura.'}), 400
        flash('La fecha y hora deben ser futuras.', 'error')
        return redirect(request.referrer or url_for('services.list'))

    from app import _catalog_org_for_member_and_theme
    _svc_org = int(_catalog_org_for_member_and_theme())
    service = Service.query.filter_by(id=service_id, organization_id=_svc_org).first()
    if not service:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Servicio no encontrado.'}), 404
        flash('Servicio no encontrado.', 'error')
        return redirect(request.referrer or url_for('services.list'))

    appointment_type_id = service.appointment_type_id or service.diagnostic_appointment_type_id
    if not appointment_type_id:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Servicio sin tipo de cita configurado.'}), 400
        flash('Este servicio no tiene citas configuradas.', 'error')
        return redirect(request.referrer or url_for('services.list'))

    appointment_type = _require_appointment_type_by_id(appointment_type_id)
    duration = (appointment_type.duration_minutes or 60) if appointment_type else 60
    end_dt = start_dt + timedelta(minutes=duration)

    advisor_id = data.get('advisor_id', type=int)
    if advisor_id:
        assignment = AppointmentAdvisor.query.filter_by(
            appointment_type_id=appointment_type_id,
            advisor_id=advisor_id,
            is_active=True
        ).first()
        if not assignment:
            advisor_id = None
    if not advisor_id:
        assignment = AppointmentAdvisor.query.filter_by(
            appointment_type_id=appointment_type_id,
            is_active=True
        ).first()
        if not assignment:
            if request.is_json:
                return jsonify({'success': False, 'error': 'No hay asesor disponible para este servicio.'}), 400
            flash('No hay asesor disponible para este servicio.', 'error')
            return redirect(request.referrer or url_for('services.list'))
        advisor_id = assignment.advisor_id
    membership_type = membership.membership_type if membership else 'basic'
    pricing = appointment_type.pricing_for_membership(membership_type)
    base_price = pricing.get('base_price', 0.0)
    final_price = pricing.get('final_price', 0.0)
    discount = max(0.0, base_price - final_price)

    appointment = Appointment(
        appointment_type_id=appointment_type_id,
        organization_id=int(getattr(appointment_type, 'organization_id', None) or 1),
        advisor_id=advisor_id,
        slot_id=None,
        user_id=current_user.id,
        service_id=service.id,
        membership_type=membership_type,
        is_group=False,
        start_datetime=start_dt,
        end_datetime=end_dt,
        status='PENDIENTE',
        is_initial_consult=True,
        advisor_confirmed=False,
        advisor_confirmed_at=None,
        confirmed_at=None,
        base_price=base_price,
        final_price=final_price,
        discount_applied=max(0, discount),
        user_notes=notes or 'Solicitud de primera reunión.',
    )
    db.session.add(appointment)
    db.session.flush()

    ActivityLog.log_activity(
        current_user.id,
        'request_appointment',
        'appointment',
        appointment.id,
        f'Solicitó primera reunión {appointment.reference}',
        request
    )

    advisor = Advisor.query.get(advisor_id)
    advisor_user_id = advisor.user_id if advisor and advisor.user_id else None
    if advisor_user_id and Notification:
        notif = Notification(
            user_id=advisor_user_id,
            notification_type='appointment_request',
            title='Nueva solicitud de primera reunión',
            message=f'{current_user.first_name} {current_user.last_name} solicita una reunión para {start_dt.strftime("%d/%m/%Y %H:%M")}. Servicio: {service.name}.'
        )
        db.session.add(notif)
    db.session.commit()

    # Email al asesor (no bloquea el flujo si falla)
    try:
        from app import NotificationEngine
        advisor_user = User.query.get(advisor_user_id) if advisor_user_id else None
        if advisor_user:
            NotificationEngine.notify_appointment_new_to_advisor(appointment, current_user, advisor_user, service)
            try:
                from nodeone.services.communication_dispatch import dispatch_appointment_new_to_advisor

                bu = request_base_url_optional()
                dispatch_appointment_new_to_advisor(
                    appointment, current_user, advisor_user, service, bu
                )
            except Exception:
                pass
    except Exception as e:
        import traceback
        print(f"⚠️ Error enviando notificación/email al asesor por nueva solicitud: {e}")
        traceback.print_exc()

    if request.is_json:
        return jsonify({
            'success': True,
            'appointment_id': appointment.id,
            'reference': appointment.reference,
            'status': appointment.status,
            'message': 'Solicitud enviada. El asesor la confirmará o rechazará.',
        })
    flash('Solicitud enviada. Revisa "Mis solicitudes" para ver el estado; el asesor confirmará o rechazará.', 'success')
    return redirect(url_for('appointments.my_requests'))


def _advisor_for_current_user():
    ensure_models()
    return Advisor.query.filter_by(user_id=current_user.id).first()


@appointments_bp.route('/<int:appointment_id>/confirm', methods=['POST'])
@login_required
def confirm_appointment(appointment_id):
    """
    Fase 3: Asesor confirma la cita. Valida que no exista otra CONFIRMADA en el mismo horario.
    """
    ensure_models()
    advisor = _advisor_for_current_user()
    if not advisor or not getattr(current_user, 'is_advisor', False):
        if request.is_json:
            return jsonify({'success': False, 'error': 'Solo el asesor puede confirmar.'}), 403
        flash('No tienes permiso para confirmar esta cita.', 'error')
        return redirect(request.referrer or url_for('appointments.appointments_home'))

    appointment = _require_appointment_by_id(appointment_id)
    if appointment.advisor_id != advisor.id:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Esta cita no te corresponde.'}), 403
        flash('Esta cita no te corresponde.', 'error')
        return redirect(request.referrer or url_for('appointments.advisor_queue'))
    if appointment.status not in ('PENDIENTE', 'pending'):
        if request.is_json:
            return jsonify({'success': False, 'error': 'La cita no está pendiente de confirmación.'}), 400
        flash('La cita no está pendiente.', 'info')
        return redirect(request.referrer or url_for('appointments.advisor_queue'))

    start = appointment.start_datetime
    end = appointment.end_datetime
    if start and end:
        conflict = Appointment.query.filter(
            Appointment.id != appointment.id,
            Appointment.advisor_id == advisor.id,
            Appointment.status.in_(['CONFIRMADA', 'confirmed']),
            Appointment.start_datetime.isnot(None),
            Appointment.end_datetime.isnot(None),
            Appointment.start_datetime < end,
            Appointment.end_datetime > start,
        ).first()
        if conflict:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Ya tienes otra cita confirmada en ese horario.'}), 409
            flash('Ya tienes otra cita confirmada en ese horario.', 'error')
            return redirect(request.referrer or url_for('appointments.advisor_queue'))

    now = datetime.utcnow()
    appointment.status = 'CONFIRMADA'
    appointment.advisor_confirmed = True
    appointment.advisor_confirmed_at = now
    appointment.confirmed_at = now
    ActivityLog.log_activity(current_user.id, 'confirm_appointment', 'appointment', appointment.id, f'Confirmó cita {appointment.reference}', request)
    if Notification and appointment.user_id:
        n = Notification(
            user_id=appointment.user_id,
            notification_type='appointment_confirmation',
            title='Cita confirmada',
            message=f'Tu solicitud de reunión ({appointment.reference}) ha sido confirmada por el asesor para el {start.strftime("%d/%m/%Y %H:%M") if start else "próximo"}.'
        )
        db.session.add(n)
    db.session.commit()

    # Email al cliente (no bloquea si falla)
    try:
        from app import NotificationEngine
        client_user = User.query.get(appointment.user_id)
        if client_user and advisor and advisor.user:
            NotificationEngine.notify_appointment_confirmation(appointment, client_user, advisor.user)
            try:
                from nodeone.services.communication_dispatch import dispatch_appointment_confirmation_member

                bu = request_base_url_optional()
                dispatch_appointment_confirmation_member(
                    appointment, client_user, advisor.user, bu
                )
            except Exception:
                pass
    except Exception as e:
        import traceback
        print(f"⚠️ Error enviando email de confirmación al cliente: {e}")
        traceback.print_exc()

    if request.is_json:
        return jsonify({'success': True, 'status': appointment.status, 'message': 'Cita confirmada.'})
    flash('Cita confirmada. Se notificó al cliente.', 'success')
    return redirect(request.referrer or url_for('appointments.advisor_queue'))


@appointments_bp.route('/<int:appointment_id>/reject', methods=['POST'])
@login_required
def reject_appointment(appointment_id):
    """
    Fase 4: Asesor rechaza la cita. Guarda comentario y notifica al cliente.
    """
    ensure_models()
    advisor = _advisor_for_current_user()
    if not advisor or not getattr(current_user, 'is_advisor', False):
        if request.is_json:
            return jsonify({'success': False, 'error': 'Solo el asesor puede rechazar.'}), 403
        flash('No tienes permiso.', 'error')
        return redirect(request.referrer or url_for('appointments.appointments_home'))

    appointment = _require_appointment_by_id(appointment_id)
    if appointment.advisor_id != advisor.id:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Esta cita no te corresponde.'}), 403
        flash('Esta cita no te corresponde.', 'error')
        return redirect(request.referrer or url_for('appointments.advisor_queue'))
    if appointment.status not in ('PENDIENTE', 'pending'):
        if request.is_json:
            return jsonify({'success': False, 'error': 'La cita no está pendiente.'}), 400
        flash('La cita no está pendiente.', 'info')
        return redirect(request.referrer or url_for('appointments.advisor_queue'))

    data = request.get_json(silent=True) or request.form
    notes = (data.get('notes') or data.get('advisor_response_notes') or '').strip()
    appointment.status = 'RECHAZADA'
    appointment.advisor_response_notes = notes or 'Rechazada por el asesor.'
    ActivityLog.log_activity(current_user.id, 'reject_appointment', 'appointment', appointment.id, f'Rechazó cita {appointment.reference}', request)
    if Notification and appointment.user_id:
        n = Notification(
            user_id=appointment.user_id,
            notification_type='appointment_rejected',
            title='Solicitud de cita rechazada',
            message=f'Tu solicitud de reunión ({appointment.reference}) fue rechazada por el asesor.' + (f' Comentario: {notes[:200]}' if notes else '')
        )
        db.session.add(n)
    db.session.commit()

    if request.is_json:
        return jsonify({'success': True, 'status': appointment.status, 'message': 'Cita rechazada.'})
    flash('Cita rechazada. Se notificó al cliente.', 'info')
    return redirect(request.referrer or url_for('appointments.advisor_queue'))


@appointments_bp.route('/proposals', methods=['POST'])
@login_required
def create_proposal():
    """
    Fase 6: Crear propuesta (solo asesor). Solo para cita CONFIRMADA del asesor.
    """
    ensure_models()
    advisor = _advisor_for_current_user()
    if not advisor or not getattr(current_user, 'is_advisor', False):
        return jsonify({'success': False, 'error': 'Solo el asesor puede crear propuestas.'}), 403

    data = request.get_json(silent=True) or request.form
    appointment_id = data.get('appointment_id', type=int)
    description = (data.get('description') or '').strip()
    total_amount = data.get('total_amount', type=float)
    if total_amount is None:
        total_amount = 0.0

    if not appointment_id:
        return jsonify({'success': False, 'error': 'appointment_id requerido.'}), 400

    appointment = _require_appointment_by_id(appointment_id)
    if appointment.advisor_id != advisor.id:
        return jsonify({'success': False, 'error': 'Esta cita no te corresponde.'}), 403
    if appointment.status not in ('CONFIRMADA', 'confirmed'):
        return jsonify({'success': False, 'error': 'Solo se puede crear propuesta para una cita confirmada.'}), 400

    proposal = Proposal(
        client_id=appointment.user_id,
        appointment_id=appointment.id,
        description=description or None,
        total_amount=float(total_amount),
        status='ENVIADA',
    )
    db.session.add(proposal)
    db.session.commit()
    ActivityLog.log_activity(current_user.id, 'create_proposal', 'proposal', proposal.id, f'Propuesta para cita {appointment.reference}', request)
    if Notification and appointment.user_id:
        n = Notification(
            user_id=appointment.user_id,
            notification_type='proposal_sent',
            title='Nueva propuesta',
            message=f'El asesor te ha enviado una propuesta para la cita {appointment.reference}.'
        )
        db.session.add(n)
        db.session.commit()
    return jsonify({'success': True, 'proposal_id': proposal.id, 'status': proposal.status})


@appointments_bp.route('/my-proposals')
@login_required
def my_proposals():
    """Fase 8: Mis propuestas (ENVIADA, ACEPTADA, RECHAZADA)."""
    ensure_models()
    proposals_list = Proposal.query.filter(
        Proposal.client_id == current_user.id
    ).order_by(Proposal.created_at.desc()).limit(50).all()
    return render_template('appointments/my_proposals.html', proposals_list=proposals_list)


@appointments_bp.route('/proposals/<int:proposal_id>/reject', methods=['POST'])
@login_required
def reject_proposal(proposal_id):
    """Cliente rechaza la propuesta."""
    ensure_models()
    proposal = Proposal.query.get_or_404(proposal_id)
    if proposal.client_id != current_user.id:
        flash('No puedes rechazar esta propuesta.', 'error')
        return redirect(url_for('appointments.my_proposals'))
    if proposal.status != 'ENVIADA':
        flash('Esta propuesta ya fue procesada.', 'info')
        return redirect(url_for('appointments.my_proposals'))
    proposal.status = 'RECHAZADA'
    db.session.commit()
    flash('Propuesta rechazada.', 'info')
    return redirect(url_for('appointments.my_proposals'))


@appointments_bp.route('/proposals/<int:proposal_id>/accept', methods=['POST'])
@login_required
def accept_proposal(proposal_id):
    """Cliente acepta: si tiene monto → carrito y pago; si no → ACEPTADA directo."""
    ensure_models()
    proposal = Proposal.query.get_or_404(proposal_id)
    if proposal.client_id != current_user.id:
        flash('No puedes aceptar esta propuesta.', 'error')
        return redirect(url_for('appointments.my_proposals'))
    if proposal.status != 'ENVIADA':
        flash('Esta propuesta ya fue procesada.', 'info')
        return redirect(url_for('appointments.my_proposals'))

    total = (proposal.total_amount or 0)
    if total <= 0:
        proposal.status = 'ACEPTADA'
        db.session.commit()
        flash('Propuesta aceptada.', 'success')
        return redirect(url_for('appointments.my_proposals'))

    # Monto > 0: agregar al carrito y redirigir a pago
    from app import add_to_cart
    import json
    add_to_cart(
        user_id=current_user.id,
        product_type='proposal',
        product_id=proposal.id,
        product_name=f"Propuesta - {proposal.appointment.reference if proposal.appointment else 'Cita'}",
        unit_price=int(round(total * 100)),  # centavos
        quantity=1,
        product_description=(proposal.description or '')[:200],
        metadata={'proposal_id': proposal.id}
    )
    flash('Propuesta agregada al carrito. Completa el pago para confirmar.', 'success')
    return redirect(url_for('payments.cart'))


@appointments_bp.route('/cancel/<int:appointment_id>', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    ensure_models()
    appointment = _require_appointment_by_id(appointment_id)
    if appointment.user_id != current_user.id and not current_user.is_admin:
        flash('No puedes cancelar esta cita.', 'error')
        return redirect(url_for('appointments.appointments_home'))

    if appointment.status == 'cancelled':
        flash('La cita ya estaba cancelada.', 'info')
        return redirect(url_for('appointments.appointments_home'))

    if appointment.start_datetime <= datetime.utcnow():
        flash('No puedes cancelar citas que ya iniciaron.', 'warning')
        return redirect(url_for('appointments.appointments_home'))

    appointment.status = 'cancelled'
    appointment.cancellation_reason = request.form.get('reason', 'Cancelada por el miembro.')
    appointment.cancelled_at = datetime.utcnow()
    appointment.cancelled_by = 'admin' if current_user.is_admin else 'member'

    if appointment.slot:
        appointment.slot.reserved_seats = max(0, (appointment.slot.reserved_seats or 1) - 1)
        appointment.slot.is_available = True

    db.session.commit()

    ActivityLog.log_activity(
        current_user.id,
        'cancel_appointment',
        'appointment',
        appointment.id,
        f'Canceló la cita {appointment.reference}',
        request
    )

    try:
        from app import NotificationEngine
        client_user = User.query.get(appointment.user_id)
        if client_user:
            NotificationEngine.notify_appointment_cancelled(
                appointment,
                client_user,
                cancellation_reason=appointment.cancellation_reason,
                cancelled_by=appointment.cancelled_by or 'member',
            )
            try:
                from nodeone.services.communication_dispatch import dispatch_appointment_cancellation_member

                bu = request_base_url_optional()
                dispatch_appointment_cancellation_member(
                    appointment,
                    client_user,
                    bu,
                    reason=appointment.cancellation_reason,
                    cancelled_by=appointment.cancelled_by or 'member',
                )
            except Exception:
                pass
    except Exception as _e:
        print(f'⚠️ notify_appointment_cancelled (miembro): {_e}')

    flash('Tu cita fue cancelada.', 'info')
    return redirect(url_for('appointments.appointments_home'))


# ---------------------------------------------------------------------------
# Vistas Administrativas
# ---------------------------------------------------------------------------
@admin_appointments_bp.route('/')
@admin_required
def admin_appointments_dashboard():
    ensure_models()
    from utils.organization import get_admin_effective_organization_id

    _oid = get_admin_effective_organization_id()
    types = (
        AppointmentType.query.filter_by(organization_id=_oid)
        .order_by(AppointmentType.display_order.asc())
        .all()
    )
    advisors = _advisors_scoped_query().order_by(Advisor.created_at.desc()).all()
    upcoming = _slot_queryset().limit(15).all()
    waiting_confirmation = _appointments_scoped_query().filter(
        Appointment.status.in_(['pending', 'PENDIENTE'])
    ).order_by(Appointment.start_datetime.asc()).limit(10).all()

    stats = {
        'active_types': len(types),
        'active_advisors': sum(1 for advisor in advisors if advisor.is_active),
        'pending_appointments': len(waiting_confirmation),
        'next_slots': len(upcoming),
    }

    return render_template(
        'admin/appointments/list.html',
        types=types,
        advisors=advisors,
        stats=stats,
        slots=upcoming,
        pending_appointments=waiting_confirmation,
    )


@admin_appointments_bp.route('/<int:appointment_id>/confirm', methods=['POST'])
@admin_required
def admin_confirm_appointment(appointment_id):
    ensure_models()
    appointment = _require_appointment_by_id(appointment_id)
    if appointment.status == 'confirmed':
        flash('La cita ya estaba confirmada.', 'info')
        return redirect(url_for('admin_appointments.admin_appointments_dashboard'))

    appointment.status = 'confirmed'
    appointment.advisor_confirmed = True
    appointment.advisor_confirmed_at = datetime.utcnow()
    db.session.commit()

    ActivityLog.log_activity(
        current_user.id,
        'confirm_appointment',
        'appointment',
        appointment.id,
        f'Confirmó la cita {appointment.reference}',
        request
    )

    try:
        from app import NotificationEngine, User

        client_user = User.query.get(appointment.user_id)
        advisor_row = Advisor.query.get(appointment.advisor_id) if appointment.advisor_id else None
        advisor_user = advisor_row.user if advisor_row and getattr(advisor_row, 'user', None) else None
        if client_user and advisor_user:
            NotificationEngine.notify_appointment_confirmation(appointment, client_user, advisor_user)
            try:
                from nodeone.services.communication_dispatch import dispatch_appointment_confirmation_member

                bu = request_base_url_optional()
                dispatch_appointment_confirmation_member(
                    appointment, client_user, advisor_user, bu
                )
            except Exception:
                pass
    except Exception as _e:
        print(f'⚠️ admin_confirm_appointment notificación: {_e}')

    flash('La cita fue confirmada y se notificará al miembro.', 'success')
    return redirect(url_for('admin_appointments.admin_appointments_dashboard'))


@admin_appointments_bp.route('/<int:appointment_id>/cancel', methods=['POST'])
@admin_required
def admin_cancel_appointment(appointment_id):
    ensure_models()
    appointment = _require_appointment_by_id(appointment_id)
    if appointment.status == 'cancelled':
        flash('La cita ya estaba cancelada.', 'info')
        return redirect(url_for('admin_appointments.admin_appointments_dashboard'))

    appointment.status = 'cancelled'
    appointment.cancellation_reason = request.form.get('reason', 'Cancelada por el administrador.')
    appointment.cancelled_at = datetime.utcnow()
    appointment.cancelled_by = 'admin'

    if appointment.slot:
        appointment.slot.reserved_seats = max(0, (appointment.slot.reserved_seats or 1) - 1)
        appointment.slot.is_available = True

    db.session.commit()

    ActivityLog.log_activity(
        current_user.id,
        'cancel_appointment_admin',
        'appointment',
        appointment.id,
        f'Canceló la cita {appointment.reference}',
        request
    )

    try:
        from app import NotificationEngine
        client_user = User.query.get(appointment.user_id)
        if client_user:
            NotificationEngine.notify_appointment_cancelled(
                appointment,
                client_user,
                cancellation_reason=appointment.cancellation_reason,
                cancelled_by='admin',
            )
            try:
                from nodeone.services.communication_dispatch import dispatch_appointment_cancellation_member

                bu = request_base_url_optional()
                dispatch_appointment_cancellation_member(
                    appointment,
                    client_user,
                    bu,
                    reason=appointment.cancellation_reason,
                    cancelled_by='admin',
                )
            except Exception:
                pass
    except Exception as _e:
        print(f'⚠️ notify_appointment_cancelled (admin): {_e}')

    flash('La cita fue cancelada y los participantes serán notificados.', 'info')
    return redirect(url_for('admin_appointments.admin_appointments_dashboard'))


@admin_appointments_bp.route('/types/create', methods=['GET', 'POST'])
@admin_required
def create_appointment_type():
    ensure_models()
    advisors = _advisors_scoped_query().order_by(Advisor.created_at.asc()).all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        duration = request.form.get('duration_minutes', type=int) or 60
        base_price = request.form.get('base_price', type=float) or 0.0

        if not name:
            flash('El nombre del servicio es obligatorio.', 'error')
            return redirect(request.url)

        from app import get_current_organization_id, SaasOrganization, _platform_admin_data_scope_organization_id
        _co = get_current_organization_id()
        if _co is None:
            flash('No hay organización activa en sesión.', 'error')
            return redirect(request.url)
        oid = int(_co)
        if _appt_platform_admin():
            cand = request.form.get('organization_id', type=int)
            if cand and SaasOrganization.query.get(cand):
                oid = cand
            else:
                scoped = _platform_admin_data_scope_organization_id()
                if scoped is not None:
                    oid = int(scoped)
        appointment_type = AppointmentType(
            name=name,
            display_name=(request.form.get('display_name') or '').strip() or None,
            organization_id=oid,
            description=request.form.get('description', '').strip(),
            service_category=request.form.get('service_category', '').strip() or 'general',
            duration_minutes=duration,
            is_group_allowed=bool(request.form.get('is_group_allowed')),
            max_participants=request.form.get('max_participants', type=int) or 1,
            base_price=base_price,
            currency=request.form.get('currency', 'USD'),
            is_virtual=bool(request.form.get('is_virtual', True)),
            requires_confirmation=bool(request.form.get('requires_confirmation', True)),
            color_tag=request.form.get('color_tag', '#0d6efd'),
            icon=request.form.get('icon', 'fa-calendar-check'),
            display_order=request.form.get('display_order', type=int) or 1,
        )

        db.session.add(appointment_type)
        db.session.flush()

        advisor_ids = request.form.getlist('advisor_ids')
        for idx, advisor_id in enumerate(advisor_ids, start=1):
            advisor = _advisors_scoped_query().filter(Advisor.id == int(advisor_id)).first()
            if advisor:
                db.session.add(AppointmentAdvisor(
                    appointment_type_id=appointment_type.id,
                    advisor_id=advisor.id,
                    priority=idx
                ))

        db.session.commit()

        ActivityLog.log_activity(
            current_user.id,
            'create_appointment_type',
            'appointment_type',
            appointment_type.id,
            f'Creó el servicio de citas {appointment_type.name}',
            request
        )

        flash('Servicio de citas creado correctamente.', 'success')
        return redirect(url_for('admin_appointments.admin_appointments_dashboard'))

    return render_template(
        'admin/appointments/type_form.html',
        appointment_type=None,
        advisors=advisors,
        assigned_advisor_ids=[],
    )


@admin_appointments_bp.route('/types/<int:type_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_appointment_type(type_id):
    """Editar tipo de cita (nombre, duración, precio, asesores asignados)."""
    ensure_models()
    appointment_type = _require_appointment_type_by_id(type_id)
    advisors = _advisors_scoped_query().order_by(Advisor.created_at.asc()).all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        duration = request.form.get('duration_minutes', type=int) or 60
        base_price = request.form.get('base_price', type=float) or 0.0

        if not name:
            flash('El nombre del servicio es obligatorio.', 'error')
            return redirect(request.url)

        appointment_type.name = name
        appointment_type.display_name = (request.form.get('display_name') or '').strip() or None
        appointment_type.description = request.form.get('description', '').strip()
        appointment_type.service_category = request.form.get('service_category', '').strip() or 'general'
        appointment_type.duration_minutes = duration
        appointment_type.is_group_allowed = bool(request.form.get('is_group_allowed'))
        appointment_type.max_participants = request.form.get('max_participants', type=int) or 1
        appointment_type.base_price = base_price
        appointment_type.currency = request.form.get('currency', 'USD')
        appointment_type.is_virtual = bool(request.form.get('is_virtual', True))
        appointment_type.requires_confirmation = bool(request.form.get('requires_confirmation', True))
        appointment_type.color_tag = request.form.get('color_tag', '#0d6efd')
        appointment_type.icon = request.form.get('icon', 'fa-calendar-check')
        appointment_type.display_order = request.form.get('display_order', type=int) or 1

        # Reemplazar asesores asignados
        AppointmentAdvisor.query.filter_by(appointment_type_id=appointment_type.id).delete()
        advisor_ids = request.form.getlist('advisor_ids')
        for idx, advisor_id in enumerate(advisor_ids, start=1):
            advisor = _advisors_scoped_query().filter(Advisor.id == int(advisor_id)).first()
            if advisor:
                db.session.add(AppointmentAdvisor(
                    appointment_type_id=appointment_type.id,
                    advisor_id=advisor.id,
                    priority=idx,
                    is_active=True,
                ))

        db.session.commit()

        ActivityLog.log_activity(
            current_user.id,
            'edit_appointment_type',
            'appointment_type',
            appointment_type.id,
            f'Actualizó el servicio de citas {appointment_type.name}',
            request
        )

        flash('Servicio de citas actualizado. Los asesores asignados se reflejan en el catálogo.', 'success')
        return redirect(url_for('admin_appointments.admin_appointments_dashboard'))

    assigned_advisor_ids = [a.advisor_id for a in appointment_type.advisor_assignments if getattr(a, 'is_active', True)]
    return render_template(
        'admin/appointments/type_form.html',
        appointment_type=appointment_type,
        advisors=advisors,
        assigned_advisor_ids=assigned_advisor_ids,
    )


@admin_appointments_bp.route('/types/<int:type_id>/assign-all-advisors', methods=['POST'])
@admin_required
def assign_all_advisors_to_type(type_id):
    """Asigna todos los asesores activos a este tipo de cita (desde la interfaz)."""
    ensure_models()
    appointment_type = _require_appointment_type_by_id(type_id)
    advisors = _advisors_scoped_query().filter_by(is_active=True).all()
    added = 0
    for advisor in advisors:
        existing = AppointmentAdvisor.query.filter_by(
            appointment_type_id=appointment_type.id,
            advisor_id=advisor.id,
        ).first()
        if not existing:
            db.session.add(AppointmentAdvisor(
                appointment_type_id=appointment_type.id,
                advisor_id=advisor.id,
                priority=1,
                is_active=True,
            ))
            added += 1
        elif not getattr(existing, 'is_active', True):
            existing.is_active = True
            added += 1
    db.session.commit()
    if added:
        ActivityLog.log_activity(
            current_user.id,
            'assign_all_advisors_to_type',
            'appointment_type',
            appointment_type.id,
            f'Asignó todos los asesores activos ({added} añadidos/reactivados) a {appointment_type.name}',
            request
        )
        flash(f'Se asignaron todos los asesores activos a este servicio ({added} añadidos).', 'success')
    else:
        flash('Todos los asesores activos ya estaban asignados.', 'info')
    return redirect(url_for('admin_appointments.edit_appointment_type', type_id=type_id))


@admin_appointments_bp.route('/types/<int:type_id>/toggle-active', methods=['POST'])
@admin_required
def toggle_appointment_type_active(type_id):
    """Activar o desactivar un tipo de cita (no se elimina)."""
    ensure_models()
    appointment_type = _require_appointment_type_by_id(type_id)
    appointment_type.is_active = not getattr(appointment_type, 'is_active', True)
    db.session.commit()
    status = 'activado' if appointment_type.is_active else 'desactivado'
    ActivityLog.log_activity(
        current_user.id,
        'toggle_appointment_type',
        'appointment_type',
        appointment_type.id,
        f'{status.capitalize()} el servicio de citas {appointment_type.name}',
        request
    )
    flash(f'Servicio de citas {status}. Ya no aparecerá en opciones mientras esté desactivado.', 'success')
    return redirect(url_for('admin_appointments.admin_appointments_dashboard'))


@admin_appointments_bp.route('/slots/create', methods=['POST'])
@admin_required
def create_manual_slot():
    ensure_models()
    type_id = request.form.get('appointment_type_id', type=int)
    advisor_id = request.form.get('advisor_id', type=int)
    start_raw = request.form.get('start_datetime', '').strip()
    capacity = request.form.get('capacity', type=int) or 1

    appointment_type = _require_appointment_type_by_id(type_id)
    advisor = _advisors_scoped_query().filter(Advisor.id == advisor_id).first()
    if not advisor:
        from flask import abort
        abort(404)

    try:
        start_datetime = datetime.strptime(start_raw, '%Y-%m-%dT%H:%M')
    except ValueError:
        flash('Formato de fecha inválido.', 'error')
        return redirect(url_for('admin_appointments.admin_appointments_dashboard'))

    end_datetime = start_datetime + appointment_type.duration()

    slot = AppointmentSlot(
        appointment_type_id=appointment_type.id,
        advisor_id=advisor.id,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        capacity=max(1, capacity),
        is_auto_generated=False,
        created_by=current_user.id,
    )

    db.session.add(slot)
    db.session.commit()

    ActivityLog.log_activity(
        current_user.id,
        'create_slot',
        'appointment_slot',
        slot.id,
        f'Creó un slot manual para {appointment_type.name}',
        request
    )

    flash('Slot creado satisfactoriamente.', 'success')
    return redirect(url_for('admin_appointments.admin_appointments_dashboard'))


@admin_appointments_bp.route('/advisors')
@admin_required
def list_advisors():
    ensure_models()
    advisors = _advisors_scoped_query().order_by(Advisor.created_at.desc()).all()
    from app import admin_data_scope_organization_id

    oid = admin_data_scope_organization_id()
    available_users = (
        User.query.filter_by(is_advisor=False, organization_id=oid)
        .order_by(User.first_name.asc())
        .all()
    )
    return render_template(
        'admin/appointments/advisors.html',
        advisors=advisors,
        available_users=available_users,
    )


@admin_appointments_bp.route('/advisors/create', methods=['POST'])
@admin_required
def create_advisor():
    ensure_models()
    user_id = request.form.get('user_id', type=int)
    from app import admin_data_scope_organization_id

    oid = admin_data_scope_organization_id()
    user = User.query.filter_by(id=user_id, organization_id=oid).first()
    if not user:
        from flask import abort
        abort(404)

    if user.is_advisor:
        flash('Este usuario ya es asesor.', 'warning')
        return redirect(url_for('admin_appointments.list_advisors'))

    advisor = Advisor(
        user_id=user.id,
        headline=request.form.get('headline', '').strip(),
        bio=request.form.get('bio', '').strip(),
        specializations=request.form.get('specializations', '').strip(),
        meeting_url=request.form.get('meeting_url', '').strip(),
    )

    user.is_advisor = True
    db.session.add(advisor)
    db.session.commit()

    ActivityLog.log_activity(
        current_user.id,
        'create_advisor',
        'advisor',
        advisor.id,
        f'Designó como asesor a {user.first_name} {user.last_name}',
        request
    )

    flash('Asesor creado correctamente.', 'success')
    return redirect(url_for('admin_appointments.list_advisors'))


# ===========================================================================
# GESTIÓN DE DISPONIBILIDAD DE ASESORES POR SERVICIO
# ===========================================================================

@admin_appointments_bp.route('/availability')
@admin_required
def list_service_availability():
    """Lista de configuración de disponibilidad de asesores por servicio"""
    ensure_models()
    
    # Obtener todos los tipos de cita activos (alcance tenant / filtro plataforma)
    appointment_types = _appointment_types_scoped_query().filter_by(is_active=True).order_by(AppointmentType.display_order, AppointmentType.name).all()

    # Asesores del mismo alcance
    advisors = _advisors_scoped_query().filter_by(is_active=True).order_by(Advisor.created_at.desc()).all()
    
    # Obtener disponibilidades agrupadas por asesor y tipo de cita
    availabilities = AdvisorServiceAvailability.query.filter_by(is_active=True).order_by(
        AdvisorServiceAvailability.advisor_id,
        AdvisorServiceAvailability.appointment_type_id,
        AdvisorServiceAvailability.day_of_week,
        AdvisorServiceAvailability.start_time
    ).all()
    
    # Agrupar por asesor y tipo de cita
    availability_map = {}
    for av in availabilities:
        key = (av.advisor_id, av.appointment_type_id)
        if key not in availability_map:
            availability_map[key] = []
        availability_map[key].append(av)

    # Solo pares con asignación activa (AppointmentAdvisor); evita filas engañosas asesor×tipo sin vínculo.
    advisor_ids = [a.id for a in advisors]
    type_ids = [t.id for t in appointment_types]
    assigned_pairs = []
    if advisor_ids and type_ids:
        adv_by_id = {a.id: a for a in advisors}
        type_by_id = {t.id: t for t in appointment_types}
        for aa in (
            AppointmentAdvisor.query.filter(
                AppointmentAdvisor.is_active == True,
                AppointmentAdvisor.advisor_id.in_(advisor_ids),
                AppointmentAdvisor.appointment_type_id.in_(type_ids),
            )
            .order_by(AppointmentAdvisor.appointment_type_id, AppointmentAdvisor.advisor_id)
            .all()
        ):
            adv = adv_by_id.get(aa.advisor_id)
            at = type_by_id.get(aa.appointment_type_id)
            if adv and at:
                assigned_pairs.append((adv, at))

    return render_template(
        'admin/appointments/service_availability.html',
        appointment_types=appointment_types,
        advisors=advisors,
        availability_map=availability_map,
        assigned_pairs=assigned_pairs,
    )


@admin_appointments_bp.route('/availability/manage/<int:advisor_id>/<int:appointment_type_id>', methods=['GET', 'POST'])
@admin_required
def manage_service_availability(advisor_id, appointment_type_id):
    """Gestionar horarios de disponibilidad de un asesor para un servicio específico"""
    ensure_models()

    advisor = _advisors_scoped_query().filter(Advisor.id == advisor_id).first()
    if not advisor:
        from flask import abort
        abort(404)
    appointment_type = _require_appointment_type_by_id(appointment_type_id)

    # Verificar que el asesor está asignado a este tipo de cita
    assignment = AppointmentAdvisor.query.filter_by(
        appointment_type_id=appointment_type_id,
        advisor_id=advisor_id,
        is_active=True
    ).first()
    
    if not assignment:
        flash('El asesor no está asignado a este tipo de cita. Primero debe asignarlo.', 'error')
        return redirect(url_for('admin_appointments.list_service_availability'))
    
    if request.method == 'POST':
        # Eliminar disponibilidades existentes para este asesor-servicio
        AdvisorServiceAvailability.query.filter_by(
            advisor_id=advisor_id,
            appointment_type_id=appointment_type_id
        ).delete()
        
        # Procesar horarios enviados
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        day_map = {day: idx for idx, day in enumerate(days)}
        
        created_count = 0
        for day_name, day_idx in day_map.items():
            # Obtener horarios para este día
            start_times = request.form.getlist(f'{day_name}_start')
            end_times = request.form.getlist(f'{day_name}_end')
            
            for start_str, end_str in zip(start_times, end_times):
                if start_str and end_str:
                    try:
                        from datetime import time as dt_time
                        start_time = datetime.strptime(start_str, '%H:%M').time()
                        end_time = datetime.strptime(end_str, '%H:%M').time()
                        
                        if end_time > start_time:
                            availability = AdvisorServiceAvailability(
                                advisor_id=advisor_id,
                                appointment_type_id=appointment_type_id,
                                day_of_week=day_idx,
                                start_time=start_time,
                                end_time=end_time,
                                timezone=request.form.get('timezone', 'America/Panama'),
                                is_active=True,
                                created_by=current_user.id
                            )
                            db.session.add(availability)
                            created_count += 1
                    except ValueError:
                        continue
        
        db.session.commit()
        
        ActivityLog.log_activity(
            current_user.id,
            'update_service_availability',
            'advisor_service_availability',
            advisor_id,
            f'Actualizó horarios de {advisor.user.first_name} {advisor.user.last_name} para {appointment_type.name}',
            request
        )
        
        flash(f'Horarios actualizados correctamente. Se crearon {created_count} bloques de disponibilidad.', 'success')
        return redirect(url_for('admin_appointments.manage_service_availability', 
                                advisor_id=advisor_id, 
                                appointment_type_id=appointment_type_id))
    
    # GET: Mostrar formulario
    existing_availabilities = AdvisorServiceAvailability.query.filter_by(
        advisor_id=advisor_id,
        appointment_type_id=appointment_type_id,
        is_active=True
    ).order_by('day_of_week', 'start_time').all()
    
    # Agrupar por día de la semana
    availabilities_by_day = {day: [] for day in range(7)}
    for av in existing_availabilities:
        availabilities_by_day[av.day_of_week].append(av)
    
    return render_template(
        'admin/appointments/manage_availability.html',
        advisor=advisor,
        appointment_type=appointment_type,
        availabilities_by_day=availabilities_by_day,
    )


@admin_appointments_bp.route('/availability/delete/<int:availability_id>', methods=['POST'])
@admin_required
def delete_service_availability(availability_id):
    """Eliminar un bloque de disponibilidad"""
    ensure_models()
    
    availability = AdvisorServiceAvailability.query.get_or_404(availability_id)
    advisor_id = availability.advisor_id
    appointment_type_id = availability.appointment_type_id
    if _advisors_scoped_query().filter(Advisor.id == advisor_id).first() is None:
        from flask import abort
        abort(404)
    _require_appointment_type_by_id(appointment_type_id)

    db.session.delete(availability)
    db.session.commit()
    
    ActivityLog.log_activity(
        current_user.id,
        'delete_service_availability',
        'advisor_service_availability',
        availability_id,
        f'Eliminó bloque de disponibilidad',
        request
    )
    
    flash('Bloque de disponibilidad eliminado correctamente.', 'success')
    return redirect(url_for('admin_appointments.manage_service_availability',
                          advisor_id=advisor_id,
                          appointment_type_id=appointment_type_id))


@admin_appointments_bp.route('/availability/generate-slots/<int:advisor_id>/<int:appointment_type_id>', methods=['POST'])
@admin_required
def generate_slots_from_service_availability(advisor_id, appointment_type_id):
    """Generar slots automáticamente desde la configuración de disponibilidad"""
    ensure_models()

    advisor = _advisors_scoped_query().filter(Advisor.id == advisor_id).first()
    if not advisor:
        from flask import abort
        abort(404)
    appointment_type = _require_appointment_type_by_id(appointment_type_id)
    
    days_ahead = request.form.get('days_ahead', type=int) or 30
    
    from nodeone.modules.appointments.slot_generation import generate_slots_from_availability

    slots_created = generate_slots_from_availability(advisor_id, appointment_type_id, days_ahead=days_ahead)
    
    ActivityLog.log_activity(
        current_user.id,
        'generate_slots',
        'appointment_slot',
        advisor_id,
        f'Generó {len(slots_created)} slots para {advisor.user.first_name} {advisor.user.last_name} - {appointment_type.name}',
        request
    )
    
    flash(f'Se generaron {len(slots_created)} slots automáticamente para los próximos {days_ahead} días.', 'success')
    return redirect(url_for('admin_appointments.manage_service_availability',
                          advisor_id=advisor_id,
                          appointment_type_id=appointment_type_id))


# ===========================================================================
# GESTIÓN DE DISPONIBILIDAD DIARIA (NUEVO SISTEMA)
# ===========================================================================

@admin_appointments_bp.route('/calendar')
@admin_required
def calendar_view():
    """Vista de calendario visual para configurar disponibilidad (Servicio + Asesor + Hora)"""
    ensure_models()
    from utils.organization import get_admin_effective_organization_id

    # Misma org que el resto del admin de citas (evita lista vacía si sesión difiere de efectiva).
    _coid = int(get_admin_effective_organization_id())
    services = Service.query.filter(
        Service.organization_id == _coid,
        Service.is_active == True,
        Service.appointment_type_id.isnot(None)
    ).order_by(Service.display_order, Service.name).all()

    services_missing_appointment_type = Service.query.filter(
        Service.organization_id == _coid,
        Service.is_active == True,
        Service.appointment_type_id.is_(None),
    ).order_by(Service.display_order, Service.name).limit(50).all()

    # Asesores por servicio (solo los asignados al tipo de cita; coincide con validación al guardar).
    from collections import defaultdict

    from nodeone.services.user_organization import user_in_org_clause

    type_ids = list({s.appointment_type_id for s in services if s.appointment_type_id})
    by_type_id = defaultdict(list)
    if type_ids:
        seen_pairs = set()
        for aa in (
            AppointmentAdvisor.query.filter(
                AppointmentAdvisor.appointment_type_id.in_(type_ids),
                AppointmentAdvisor.is_active == True,
            )
            .join(Advisor, AppointmentAdvisor.advisor_id == Advisor.id)
            .filter(Advisor.is_active == True)
            .join(User, Advisor.user_id == User.id)
            .filter(user_in_org_clause(User, _coid))
            .all()
        ):
            adv = aa.advisor
            if not adv or not getattr(adv, 'user', None):
                continue
            pair = (aa.appointment_type_id, adv.id)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            by_type_id[aa.appointment_type_id].append(adv)

    advisors_by_service_json = {}
    for s in services:
        tid = s.appointment_type_id
        if not tid:
            continue
        advisors_by_service_json[str(s.id)] = [
            {
                'id': adv.id,
                'name': (
                    f'{adv.user.first_name or ""} {adv.user.last_name or ""}'.strip() or f'Asesor #{adv.id}'
                ),
            }
            for adv in by_type_id.get(tid, [])
        ]

    advisors = _advisors_scoped_query().filter_by(is_active=True).order_by(Advisor.created_at.desc()).all()

    return render_template(
        'admin/appointments/calendar.html',
        services=services,
        services_missing_appointment_type=services_missing_appointment_type,
        advisors=advisors,
        advisors_by_service_json=advisors_by_service_json,
    )


@admin_appointments_bp.route('/calendar/configure/<date>', methods=['GET', 'POST'])
@admin_required
def configure_daily_availability(date):
    """Configurar disponibilidad para un día específico"""
    ensure_models()
    
    try:
        selected_date = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        flash('Fecha inválida.', 'error')
        return redirect(url_for('admin_appointments.calendar_view'))
    
    # Verificar que la fecha no sea en el pasado
    if selected_date < datetime.now().date():
        flash('No se puede configurar disponibilidad para fechas pasadas.', 'error')
        return redirect(url_for('admin_appointments.calendar_view'))
    
    if request.method == 'POST':
        # Obtener datos del formulario
        appointment_type_id = request.form.get('appointment_type_id', type=int)
        advisor_id = request.form.get('advisor_id', type=int)
        
        if not appointment_type_id or not advisor_id:
            flash('Debes seleccionar un servicio y un asesor.', 'error')
            return redirect(url_for('admin_appointments.configure_daily_availability', date=date))
        
        # Verificar que el asesor está asignado al servicio
        assignment = AppointmentAdvisor.query.filter_by(
            appointment_type_id=appointment_type_id,
            advisor_id=advisor_id,
            is_active=True
        ).first()
        
        if not assignment:
            flash('El asesor seleccionado no está asignado a este servicio.', 'error')
            return redirect(url_for('admin_appointments.configure_daily_availability', date=date))

        _require_appointment_type_by_id(appointment_type_id)
        if _advisors_scoped_query().filter(Advisor.id == advisor_id).first() is None:
            flash('Asesor no válido para su contexto.', 'error')
            return redirect(url_for('admin_appointments.configure_daily_availability', date=date))

        # Iniciar transacción
        try:
            # Eliminar disponibilidades existentes para este día, servicio y asesor
            DailyServiceAvailability.query.filter_by(
                date=selected_date,
                appointment_type_id=appointment_type_id,
                advisor_id=advisor_id
            ).delete()
            
            # Procesar horarios enviados
            start_times = request.form.getlist('start_time')
            end_times = request.form.getlist('end_time')
            
            created_count = 0
            for start_str, end_str in zip(start_times, end_times):
                if start_str and end_str:
                    try:
                        start_time = datetime.strptime(start_str, '%H:%M').time()
                        end_time = datetime.strptime(end_str, '%H:%M').time()
                        
                        if end_time > start_time:
                            availability = DailyServiceAvailability(
                                date=selected_date,
                                advisor_id=advisor_id,
                                appointment_type_id=appointment_type_id,
                                start_time=start_time,
                                end_time=end_time,
                                timezone=request.form.get('timezone', 'America/Panama'),
                                is_active=True,
                                created_by=current_user.id
                            )
                            db.session.add(availability)
                            created_count += 1
                    except ValueError:
                        continue
            
            # Commit de disponibilidades
            db.session.commit()
            
            # Generar slots automáticamente desde la disponibilidad diaria
            if created_count > 0:
                _generate_slots_from_daily_availability(selected_date, advisor_id, appointment_type_id)
            
            # Log de actividad
            advisor = Advisor.query.get(advisor_id)
            appointment_type = AppointmentType.query.get(appointment_type_id)
            ActivityLog.log_activity(
                current_user.id,
                'configure_daily_availability',
                'daily_service_availability',
                advisor_id,
                f'Configuró disponibilidad para {selected_date.strftime("%d/%m/%Y")} - {appointment_type.name if appointment_type else "N/A"} - {advisor.user.first_name if advisor and advisor.user else "N/A"}',
                request
            )
            
            flash(f'Disponibilidad configurada correctamente. Se crearon {created_count} bloques de horario.', 'success')
            return redirect(url_for('admin_appointments.calendar_view', saved='true'))
            
        except Exception as e:
            # Rollback en caso de error
            db.session.rollback()
            import traceback
            traceback.print_exc()
            flash(f'Error al guardar disponibilidad: {str(e)}', 'error')
            return redirect(url_for('admin_appointments.configure_daily_availability', date=date))
    
    # GET: Mostrar formulario
    appointment_types = _appointment_types_scoped_query().filter_by(is_active=True).order_by(AppointmentType.display_order, AppointmentType.name).all()
    advisors = _advisors_scoped_query().filter_by(is_active=True).order_by(Advisor.created_at.desc()).all()
    
    # Obtener disponibilidades existentes para este día
    existing_availabilities = DailyServiceAvailability.query.filter_by(
        date=selected_date,
        is_active=True
    ).order_by('appointment_type_id', 'advisor_id', 'start_time').all()
    
    # Agrupar por servicio y asesor
    availabilities_by_service_advisor = {}
    for av in existing_availabilities:
        key = (av.appointment_type_id, av.advisor_id)
        if key not in availabilities_by_service_advisor:
            availabilities_by_service_advisor[key] = []
        availabilities_by_service_advisor[key].append(av)
    
    return render_template(
        'admin/appointments/configure_daily.html',
        selected_date=selected_date,
        appointment_types=appointment_types,
        advisors=advisors,
        availabilities_by_service_advisor=availabilities_by_service_advisor,
    )


def _generate_slots_from_daily_availability(date, advisor_id, appointment_type_id):
    """
    Genera slots automáticamente desde disponibilidad diaria configurada.
    Se ejecuta cuando se guarda una configuración diaria.
    """
    ensure_models()
    
    advisor = Advisor.query.get(advisor_id)
    appointment_type = AppointmentType.query.get(appointment_type_id)
    
    if not advisor or not appointment_type:
        return []
    
    # Obtener disponibilidades del día
    availabilities = DailyServiceAvailability.query.filter_by(
        date=date,
        advisor_id=advisor_id,
        appointment_type_id=appointment_type_id,
        is_active=True
    ).all()
    
    if not availabilities:
        return []
    
    # Duración del slot
    slot_duration = appointment_type.duration()
    
    slots_created = []
    
    for availability in availabilities:
        # Combinar fecha con hora de inicio
        slot_start = datetime.combine(date, availability.start_time)
        slot_end_time = availability.end_time
        
        # Generar slots dentro de este bloque de disponibilidad
        current_slot_start = slot_start
        
        while current_slot_start.time() < slot_end_time:
            current_slot_end = current_slot_start + slot_duration
            
            # Verificar que el slot no exceda el bloque de disponibilidad
            if current_slot_end.time() > slot_end_time:
                break
            
            # Verificar que no esté en el pasado
            if current_slot_start < datetime.utcnow():
                current_slot_start += slot_duration
                continue
            
            # Verificar que no exista ya un slot en este horario
            existing_slot = AppointmentSlot.query.filter(
                AppointmentSlot.advisor_id == advisor_id,
                AppointmentSlot.appointment_type_id == appointment_type_id,
                AppointmentSlot.start_datetime == current_slot_start,
                AppointmentSlot.is_available == True
            ).first()
            
            if not existing_slot:
                # Verificar conflictos con otros slots del mismo asesor
                conflicting = AppointmentSlot.query.filter(
                    AppointmentSlot.advisor_id == advisor_id,
                    AppointmentSlot.start_datetime < current_slot_end,
                    AppointmentSlot.end_datetime > current_slot_start,
                    AppointmentSlot.is_available == True
                ).first()
                
                if not conflicting:
                    # Crear nuevo slot
                    new_slot = AppointmentSlot(
                        appointment_type_id=appointment_type_id,
                        advisor_id=advisor_id,
                        start_datetime=current_slot_start,
                        end_datetime=current_slot_end,
                        capacity=1,
                        is_available=True,
                        is_auto_generated=True
                    )
                    db.session.add(new_slot)
                    slots_created.append(new_slot)
            
            current_slot_start += slot_duration
    
    db.session.commit()
    return slots_created


# ---------------------------------------------------------------------------
# API Pública mínima (slots disponibles)
# ---------------------------------------------------------------------------
@appointments_api_bp.route('/slots')
@login_required
def api_slots():
    ensure_models()
    type_id = request.args.get('type_id', type=int)
    query = _slot_queryset().filter(AppointmentSlot.is_available == True)  # noqa
    if type_id:
        query = query.filter(AppointmentSlot.appointment_type_id == type_id)

    slots = query.limit(50).all()
    return jsonify([
        {
            'id': slot.id,
            'appointment_type': slot.appointment_type.name,
            'advisor': slot.advisor.user.first_name if slot.advisor and slot.advisor.user else None,
            'start': slot.start_datetime.isoformat(),
            'end': slot.end_datetime.isoformat(),
            'capacity': slot.capacity,
            'remaining': slot.remaining_seats(),
        }
        for slot in slots
    ])


# ---------------------------------------------------------------------------
# Rutas para Asesores (Advisors)
# ---------------------------------------------------------------------------
def advisor_required(f):
    """Decorator para verificar que el usuario es asesor"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        ensure_models()
        if not current_user.is_advisor:
            flash('No tienes permisos para acceder a esta sección.', 'error')
            return redirect(url_for('dashboard'))
        
        # Verificar que tiene perfil de asesor
        advisor = Advisor.query.filter_by(user_id=current_user.id).first()
        if not advisor or not advisor.is_active:
            flash('Tu perfil de asesor no está activo.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function


@appointments_bp.route('/advisor/dashboard')
@advisor_required
def advisor_dashboard():
    """Dashboard del asesor: ver slots, cola de citas, etc."""
    ensure_models()
    advisor = Advisor.query.filter_by(user_id=current_user.id).first()
    oid = _tenant_org_appt()
    
    # Slots disponibles del asesor (mismo tenant que el tipo de cita)
    my_slots = (
        AppointmentSlot.query.join(
            AppointmentType,
            AppointmentSlot.appointment_type_id == AppointmentType.id,
        )
        .filter(
            AppointmentSlot.advisor_id == advisor.id,
            AppointmentType.organization_id == oid,
            AppointmentSlot.start_datetime >= datetime.utcnow(),
            AppointmentSlot.is_available == True,
        )
        .order_by(AppointmentSlot.start_datetime.asc())
        .limit(20)
        .all()
    )
    
    # Citas confirmadas próximas
    upcoming_appointments = Appointment.query.filter(
        Appointment.advisor_id == advisor.id,
        Appointment.organization_id == oid,
        Appointment.status.in_(['confirmed', 'CONFIRMADA']),
        Appointment.start_datetime >= datetime.utcnow()
    ).order_by(Appointment.start_datetime.asc()).limit(10).all()

    # Cola de solicitudes de primera reunión (consultivo)
    queue_appointments = Appointment.query.filter(
        Appointment.advisor_id == advisor.id,
        Appointment.organization_id == oid,
        Appointment.status.in_(['pending', 'PENDIENTE']),
        Appointment.slot_id.is_(None),
        Appointment.is_initial_consult == True
    ).order_by(Appointment.queue_position.asc(), Appointment.created_at.asc()).all()

    # Tipos de cita asignados al asesor
    appointment_types = AppointmentType.query.join(AppointmentAdvisor).filter(
        AppointmentAdvisor.advisor_id == advisor.id,
        AppointmentAdvisor.is_active == True,
        AppointmentType.is_active == True,
        AppointmentType.organization_id == oid,
    ).all()
    
    all_my_slots = (
        AppointmentSlot.query.join(AppointmentType, AppointmentSlot.appointment_type_id == AppointmentType.id)
        .filter(AppointmentSlot.advisor_id == advisor.id, AppointmentType.organization_id == oid)
        .order_by(AppointmentSlot.start_datetime.desc())
        .limit(50)
        .all()
    )
    occupied_slots = []
    past_slots = (
        AppointmentSlot.query.join(AppointmentType, AppointmentSlot.appointment_type_id == AppointmentType.id)
        .filter(
            AppointmentSlot.advisor_id == advisor.id,
            AppointmentType.organization_id == oid,
            AppointmentSlot.end_datetime < datetime.utcnow(),
        )
        .order_by(AppointmentSlot.start_datetime.desc())
        .limit(20)
        .all()
    )
    
    stats = {
        'available_slots': len(my_slots),
        'upcoming_appointments': len(upcoming_appointments),
        'queue_appointments': len(queue_appointments),
        'appointment_types': len(appointment_types)
    }
    from app import SaasOrganization
    _adv_combined = upcoming_appointments + queue_appointments
    _adv_oids = {a.appointment_type.organization_id for a in _adv_combined if a.appointment_type}
    appt_tenant_names = (
        {o.id: (o.name or '').strip() for o in SaasOrganization.query.filter(SaasOrganization.id.in_(_adv_oids)).all()}
        if _adv_oids
        else {}
    )
    
    return render_template(
        'appointments/advisor_dashboard.html',
        advisor=advisor,
        slots=my_slots,
        all_slots=all_my_slots,
        occupied_slots=occupied_slots,
        past_slots=past_slots,
        upcoming_appointments=upcoming_appointments,
        queue_appointments=queue_appointments,
        appointment_types=appointment_types,
        stats=stats,
        appt_tenant_names=appt_tenant_names,
    )


@appointments_bp.route('/advisor/slots/create', methods=['GET', 'POST'])
@advisor_required
def advisor_create_slot():
    """Crear un slot disponible"""
    ensure_models()
    advisor = Advisor.query.filter_by(user_id=current_user.id).first()
    
    # Tipos de cita asignados al asesor
    oid = _tenant_org_appt()
    appointment_types = AppointmentType.query.join(AppointmentAdvisor).filter(
        AppointmentAdvisor.advisor_id == advisor.id,
        AppointmentAdvisor.is_active == True,
        AppointmentType.is_active == True,
        AppointmentType.organization_id == oid,
    ).all()

    if request.method == 'POST':
        type_id = request.form.get('appointment_type_id', type=int)
        start_raw = request.form.get('start_datetime', '').strip()
        capacity = request.form.get('capacity', type=int) or 1
        
        appointment_type = _require_appointment_type_by_id(type_id)
        
        # Verificar que el asesor está asignado a este tipo
        assignment = AppointmentAdvisor.query.filter_by(
            appointment_type_id=type_id,
            advisor_id=advisor.id,
            is_active=True
        ).first()
        
        if not assignment:
            flash('No estás asignado a este tipo de cita.', 'error')
            return redirect(url_for('appointments.advisor_create_slot'))
        
        try:
            start_datetime = datetime.strptime(start_raw, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Formato de fecha inválido. Use: YYYY-MM-DDTHH:MM', 'error')
            return redirect(url_for('appointments.advisor_create_slot'))
        
        # Validar que la fecha es futura
        if start_datetime < datetime.utcnow():
            flash('No puedes crear slots en el pasado.', 'error')
            return redirect(url_for('appointments.advisor_create_slot'))
        
        end_datetime = start_datetime + appointment_type.duration()
        
        # Verificar que no hay conflicto con otros slots
        conflicting_slot = AppointmentSlot.query.filter(
            AppointmentSlot.advisor_id == advisor.id,
            AppointmentSlot.start_datetime < end_datetime,
            AppointmentSlot.end_datetime > start_datetime,
            AppointmentSlot.is_available == True
        ).first()
        
        if conflicting_slot:
            flash(f'Ya tienes un slot en ese horario: {conflicting_slot.start_datetime.strftime("%Y-%m-%d %H:%M")}', 'error')
            return redirect(url_for('appointments.advisor_create_slot'))
        
        slot = AppointmentSlot(
            appointment_type_id=appointment_type.id,
            advisor_id=advisor.id,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            capacity=max(1, capacity),
            is_auto_generated=False,
            created_by=current_user.id,
        )
        
        db.session.add(slot)
        db.session.commit()
        
        ActivityLog.log_activity(
            current_user.id,
            'advisor_create_slot',
            'appointment_slot',
            slot.id,
            f'Creó un slot para {appointment_type.name}',
            request
        )
        
        flash(f'Slot creado: {start_datetime.strftime("%d/%m/%Y %H:%M")}', 'success')
        return redirect(url_for('appointments.advisor_dashboard'))
    
    return render_template(
        'appointments/advisor_create_slot.html',
        advisor=advisor,
        appointment_types=appointment_types
    )


@appointments_bp.route('/advisor/queue')
@advisor_required
def advisor_queue():
    """Ver cola de citas pendientes (sin slot asignado)"""
    ensure_models()
    advisor = Advisor.query.filter_by(user_id=current_user.id).first()
    
    # Fase 7: Solo solicitudes de primera reunión (consultivo)
    oid = _tenant_org_appt()
    queue_appointments = Appointment.query.filter(
        Appointment.advisor_id == advisor.id,
        Appointment.organization_id == oid,
        Appointment.status.in_(['pending', 'PENDIENTE']),
        Appointment.slot_id.is_(None),
        Appointment.is_initial_consult == True
    ).order_by(Appointment.queue_position.asc(), Appointment.created_at.asc()).all()
    
    # Slots disponibles del asesor para asignar
    available_slots = (
        AppointmentSlot.query.join(AppointmentType, AppointmentSlot.appointment_type_id == AppointmentType.id)
        .filter(
            AppointmentSlot.advisor_id == advisor.id,
            AppointmentType.organization_id == oid,
            AppointmentSlot.start_datetime >= datetime.utcnow(),
            AppointmentSlot.is_available == True,
            AppointmentSlot.reserved_seats < AppointmentSlot.capacity,
        )
        .order_by(AppointmentSlot.start_datetime.asc())
        .all()
    )
    
    from app import SaasOrganization
    _qoid = {a.appointment_type.organization_id for a in queue_appointments if a.appointment_type}
    appt_tenant_names = (
        {o.id: (o.name or '').strip() for o in SaasOrganization.query.filter(SaasOrganization.id.in_(_qoid)).all()}
        if _qoid
        else {}
    )
    return render_template(
        'appointments/advisor_queue.html',
        advisor=advisor,
        queue_appointments=queue_appointments,
        available_slots=available_slots,
        partially_available_slots=[],
        appt_tenant_names=appt_tenant_names,
    )


@appointments_bp.route('/advisor/queue/<int:appointment_id>/assign-slot', methods=['POST'])
@advisor_required
def advisor_assign_slot_to_appointment(appointment_id):
    """Asignar un slot a una cita en cola"""
    ensure_models()
    advisor = Advisor.query.filter_by(user_id=current_user.id).first()
    
    appointment = _require_appointment_by_id(appointment_id)
    
    # Verificar que la cita es del asesor y está en cola
    if appointment.advisor_id != advisor.id:
        flash('Esta cita no te corresponde.', 'error')
        return redirect(url_for('appointments.advisor_queue'))
    
    if appointment.status not in ('pending', 'PENDIENTE') or appointment.slot_id is not None:
        flash('Esta cita ya tiene un slot asignado o no está en cola.', 'error')
        return redirect(url_for('appointments.advisor_queue'))
    
    slot_id = request.form.get('slot_id', type=int)
    if not slot_id:
        flash('Debes seleccionar un slot.', 'error')
        return redirect(url_for('appointments.advisor_queue'))
    
    slot = _require_appointment_slot_in_scope(slot_id)
    
    # Verificar que el slot es del asesor y está disponible
    if slot.advisor_id != advisor.id:
        flash('Este slot no te corresponde.', 'error')
        return redirect(url_for('appointments.advisor_queue'))
    
    if not slot.is_available or slot.remaining_seats() <= 0:
        flash('Este slot ya no está disponible.', 'error')
        return redirect(url_for('appointments.advisor_queue'))
    
    # Asignar slot a la cita
    appointment.slot_id = slot.id
    appointment.start_datetime = slot.start_datetime
    appointment.end_datetime = slot.end_datetime
    appointment.status = 'confirmed'
    appointment.advisor_confirmed = True
    appointment.advisor_confirmed_at = datetime.utcnow()
    
    # Marcar slot como ocupado
    slot.reserved_seats = (slot.reserved_seats or 0) + 1
    if slot.remaining_seats() == 0:
        slot.is_available = False
    
    db.session.commit()
    
    ActivityLog.log_activity(
        current_user.id,
        'advisor_assign_slot',
        'appointment',
        appointment.id,
        f'Asignó slot a cita {appointment.reference}',
        request
    )
    
    # TODO: Enviar email de confirmación al cliente
    # send_appointment_confirmation_email(appointment, appointment.user, advisor)
    
    flash(f'Slot asignado. Cita confirmada para {slot.start_datetime.strftime("%d/%m/%Y %H:%M")}', 'success')
    return redirect(url_for('appointments.advisor_queue'))


# ===========================================================================
# API PARA CALENDARIO ADMINISTRATIVO
# ===========================================================================

@appointments_api_bp.route('/admin/availability', methods=['GET'])
@admin_required
def api_admin_availability():
    """API para obtener disponibilidades configuradas para el calendario"""
    ensure_models()

    try:
        service_id = request.args.get('service_id', type=int)
        advisor_id = request.args.get('advisor_id', type=int)
        start_date = request.args.get('start')  # YYYY-MM-DD (week_start)
        end_date = request.args.get('end')  # YYYY-MM-DD (week_end)

        payload, status_code = get_admin_availability_payload(
            service_id=service_id,
            advisor_id=advisor_id,
            start_date_raw=start_date,
            end_date_raw=end_date,
        )
        return jsonify(payload), status_code

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 400


# --- HTTP legacy (URLs fijas; antes en app.py) ---


@appointments_http_legacy_bp.route('/api/admin/appointment-types', methods=['GET'])
@admin_required
def admin_appointment_types_list():
    """Lista de tipos de cita (activos) para la misma org que /admin/services (selector/sesión)."""
    ensure_models()
    try:
        from utils.organization import get_admin_effective_organization_id

        _oid = get_admin_effective_organization_id()
        appointment_types = (
            AppointmentType.query.filter_by(organization_id=_oid, is_active=True)
            .order_by(AppointmentType.display_order, AppointmentType.name)
            .all()
        )
        types_list = [
            {
                'id': at.id,
                'name': at.name,
                'description': at.description or '',
                'duration_minutes': at.duration_minutes or 60,
            }
            for at in appointment_types
        ]
        return jsonify({'success': True, 'appointment_types': types_list})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@appointments_http_legacy_bp.route('/api/appointments/calendar/<int:advisor_id>', methods=['GET'])
@login_required
def get_advisor_calendar(advisor_id):
    """Disponibilidad del asesor para calendario (FullCalendar)."""
    ensure_models()
    from app import Service, User, _catalog_org_for_member_and_theme

    try:
        appointment_type_id = request.args.get('appointment_type_id', type=int)
        service_id = request.args.get('service_id', type=int)
        start_date = request.args.get('start')
        end_date = request.args.get('end')

        if service_id and not appointment_type_id:
            _cal_org = int(_catalog_org_for_member_and_theme())
            service = Service.query.filter_by(id=service_id, organization_id=_cal_org).first()
            if service and service.appointment_type_id:
                appointment_type_id = service.appointment_type_id

        if not appointment_type_id:
            return jsonify({'success': False, 'error': 'appointment_type_id o service_id requerido'}), 400

        advisor = Advisor.query.get_or_404(advisor_id)

        assignment = AppointmentAdvisor.query.filter_by(
            appointment_type_id=appointment_type_id,
            advisor_id=advisor_id,
            is_active=True,
        ).first()

        if not assignment:
            return jsonify({'success': False, 'error': 'Asesor no asignado a este tipo de cita'}), 400

        from nodeone.modules.appointments.slot_generation import generate_slots_from_availability

        appointment_type = AppointmentType.query.get(appointment_type_id)
        if appointment_type:
            existing_slots_count = AppointmentSlot.query.filter(
                AppointmentSlot.advisor_id == advisor_id,
                AppointmentSlot.appointment_type_id == appointment_type_id,
                AppointmentSlot.start_datetime >= datetime.utcnow(),
                AppointmentSlot.start_datetime <= datetime.utcnow() + timedelta(days=30),
            ).count()

            if existing_slots_count < 10:
                generate_slots_from_availability(advisor_id, appointment_type_id, days_ahead=30)

        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            except Exception:
                start_dt = datetime.utcnow()
        else:
            start_dt = datetime.utcnow()

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            except Exception:
                end_dt = start_dt + timedelta(days=30)
        else:
            end_dt = start_dt + timedelta(days=30)

        slots = AppointmentSlot.query.filter(
            AppointmentSlot.advisor_id == advisor_id,
            AppointmentSlot.appointment_type_id == appointment_type_id,
            AppointmentSlot.start_datetime >= start_dt,
            AppointmentSlot.start_datetime < end_dt,
            AppointmentSlot.is_available == True,
        ).order_by(AppointmentSlot.start_datetime.asc()).all()

        availabilities = AdvisorAvailability.query.filter_by(
            advisor_id=advisor_id,
            is_active=True,
        ).all()

        calendar_events = []

        for slot in slots:
            calendar_events.append({
                'id': f'slot_{slot.id}',
                'title': f'Disponible ({slot.remaining_seats()} cupos)',
                'start': slot.start_datetime.isoformat(),
                'end': slot.end_datetime.isoformat(),
                'backgroundColor': '#28a745',
                'borderColor': '#28a745',
                'textColor': '#fff',
                'extendedProps': {
                    'type': 'slot',
                    'slot_id': slot.id,
                    'available': True,
                    'remaining_seats': slot.remaining_seats(),
                    'capacity': slot.capacity,
                },
            })

        appointments_in_range = Appointment.query.filter(
            Appointment.advisor_id == advisor_id,
            Appointment.status.in_(['CONFIRMADA', 'PENDIENTE', 'confirmed', 'pending']),
            Appointment.start_datetime.isnot(None),
            Appointment.start_datetime >= start_dt,
            Appointment.start_datetime < end_dt,
        ).all()
        for apt in appointments_in_range:
            if not apt.start_datetime or not apt.end_datetime:
                continue
            try:
                client_name = 'Cliente'
                if apt.user_id:
                    u = User.query.get(apt.user_id)
                    if u:
                        client_name = f'{u.first_name} {u.last_name}'
                label = 'Confirmada' if apt.status in ('CONFIRMADA', 'confirmed') else 'Pendiente'
                calendar_events.append({
                    'id': f'apt_{apt.id}',
                    'title': f'Cita {label} - {client_name}',
                    'start': apt.start_datetime.isoformat(),
                    'end': (apt.end_datetime or apt.start_datetime).isoformat(),
                    'backgroundColor': '#17a2b8' if apt.status in ('PENDIENTE', 'pending') else '#6f42c1',
                    'borderColor': '#17a2b8' if apt.status in ('PENDIENTE', 'pending') else '#6f42c1',
                    'textColor': '#fff',
                    'extendedProps': {
                        'type': 'appointment',
                        'appointment_id': apt.id,
                        'status': apt.status,
                    },
                })
            except Exception as e:
                print(f'Error agregando cita {apt.id} al calendario asesor: {e}')
                continue

        availability_info = []
        for av in availabilities:
            day_names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            availability_info.append({
                'day_of_week': av.day_of_week,
                'day_name': day_names[av.day_of_week],
                'start_time': av.start_time.strftime('%H:%M'),
                'end_time': av.end_time.strftime('%H:%M'),
                'timezone': av.timezone,
            })

        return jsonify({
            'success': True,
            'advisor': {
                'id': advisor.id,
                'name': f'{advisor.user.first_name} {advisor.user.last_name}' if advisor.user else 'Asesor',
                'bio': advisor.bio,
                'specializations': advisor.specializations,
            },
            'appointment_type': {
                'id': appointment_type.id,
                'name': appointment_type.name,
                'duration_minutes': appointment_type.duration_minutes,
            },
            'events': calendar_events,
            'availability': availability_info,
            'timezone': availabilities[0].timezone if availabilities else 'America/Panama',
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 400

