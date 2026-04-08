"""
Servicios de negocio para citas (separados de routes.py).
Paso incremental: mover lógica de consultas/serialización sin cambiar endpoints.
"""
from datetime import datetime, timedelta


def _parse_date_or_default(raw_value, default_value):
    if not raw_value:
        return default_value
    try:
        return datetime.strptime(raw_value, "%Y-%m-%d").date()
    except Exception:
        return default_value


def get_admin_availability_payload(
    service_id,
    advisor_id,
    start_date_raw=None,
    end_date_raw=None,
):
    """
    Construye payload para /api/appointments/admin/availability.

    Retorna: (payload_dict, status_code)
    """
    if not service_id or not advisor_id:
        return {'success': False, 'error': 'service_id y advisor_id son obligatorios'}, 400

    from app import Service as ServiceModel
    from nodeone.modules.appointments.models import load_appointment_context

    ctx = load_appointment_context()
    DailyServiceAvailability = ctx['DailyServiceAvailability']

    service = ServiceModel.query.get(service_id)
    if not service or not service.appointment_type_id:
        return {'success': False, 'error': 'Servicio no encontrado o sin appointment_type'}, 404

    appointment_type_id = service.appointment_type_id
    start_dt = _parse_date_or_default(start_date_raw, datetime.now().date())
    end_dt = _parse_date_or_default(end_date_raw, start_dt + timedelta(days=30))

    query = DailyServiceAvailability.query.filter(
        DailyServiceAvailability.date >= start_dt,
        DailyServiceAvailability.date <= end_dt,
        DailyServiceAvailability.is_active == True,
    )

    if appointment_type_id:
        query = query.filter(DailyServiceAvailability.appointment_type_id == appointment_type_id)
    if advisor_id:
        query = query.filter(DailyServiceAvailability.advisor_id == advisor_id)

    availabilities = query.order_by(
        DailyServiceAvailability.date,
        DailyServiceAvailability.start_time,
    ).all()

    availabilities_data = [
        {
            'id': av.id,
            'date': av.date.isoformat(),
            'start_time': av.start_time.strftime('%H:%M'),
            'end_time': av.end_time.strftime('%H:%M'),
            'appointment_type_id': av.appointment_type_id,
            'advisor_id': av.advisor_id,
            'appointment_type_name': av.appointment_type.name if av.appointment_type else 'N/A',
            'advisor_name': (
                f"{av.advisor.user.first_name} {av.advisor.user.last_name}"
                if av.advisor and av.advisor.user
                else 'Asesor'
            ),
        }
        for av in availabilities
    ]

    return {
        'success': True,
        'availabilities': availabilities_data,
        'total': len(availabilities_data),
    }, 200


def tenant_org_appt():
    from app import get_current_organization_id
    oid = get_current_organization_id()
    if oid is None:
        raise RuntimeError('tenant_org_appt: sin organization_id en sesión')
    return int(oid)


def appt_platform_admin():
    from app import _admin_can_view_all_organizations
    return _admin_can_view_all_organizations()


def org_filter_appt_optional():
    """Misma regla que listados admin: URL, subdominio, sesión Empresa (admin plataforma)."""
    from app import _platform_admin_data_scope_organization_id
    return _platform_admin_data_scope_organization_id()


def appointment_types_scoped_query(AppointmentType):
    q = AppointmentType.query
    if appt_platform_admin():
        org_filter = org_filter_appt_optional()
        if org_filter is not None:
            q = q.filter(AppointmentType.organization_id == org_filter)
        return q
    return q.filter(AppointmentType.organization_id == tenant_org_appt())


def require_appointment_type_by_id(type_id, AppointmentType):
    from flask import abort
    appointment_type = AppointmentType.query.get(type_id)
    if appointment_type is None:
        abort(404)
    if appt_platform_admin():
        org_filter = org_filter_appt_optional()
        if org_filter is not None and int(getattr(appointment_type, 'organization_id', 1) or 1) != org_filter:
            abort(404)
        return appointment_type
    if int(getattr(appointment_type, 'organization_id', 1) or 1) != tenant_org_appt():
        abort(404)
    return appointment_type


def require_appointment_slot_in_scope(slot_id, AppointmentSlot, require_type_fn):
    from flask import abort
    slot = AppointmentSlot.query.get(slot_id)
    if slot is None:
        abort(404)
    require_type_fn(slot.appointment_type_id)
    return slot


def appointments_scoped_query(Appointment):
    q = Appointment.query
    if appt_platform_admin():
        org_filter = org_filter_appt_optional()
        if org_filter is not None:
            q = q.filter(Appointment.organization_id == org_filter)
        return q
    return q.filter(Appointment.organization_id == tenant_org_appt())


def require_appointment_by_id(appt_id, Appointment):
    from flask import abort
    appointment = Appointment.query.get(appt_id)
    if appointment is None:
        abort(404)
    if appt_platform_admin():
        org_filter = org_filter_appt_optional()
        if org_filter is not None and int(getattr(appointment, 'organization_id', 1) or 1) != org_filter:
            abort(404)
        return appointment
    if int(getattr(appointment, 'organization_id', 1) or 1) != tenant_org_appt():
        abort(404)
    return appointment


def advisors_scoped_query(Advisor, User):
    from nodeone.services.user_organization import user_in_org_clause

    query = Advisor.query.join(User, Advisor.user_id == User.id)
    if not appt_platform_admin():
        query = query.filter(user_in_org_clause(User, tenant_org_appt()))
    else:
        scope = org_filter_appt_optional()
        if scope is not None:
            query = query.filter(user_in_org_clause(User, scope))
    return query


def slot_queryset(AppointmentSlot, AppointmentType):
    query = AppointmentSlot.query.join(
        AppointmentType,
        AppointmentSlot.appointment_type_id == AppointmentType.id,
    )
    if appt_platform_admin():
        org_filter = org_filter_appt_optional()
        if org_filter is not None:
            query = query.filter(AppointmentType.organization_id == org_filter)
    else:
        query = query.filter(AppointmentType.organization_id == tenant_org_appt())
    return query.filter(AppointmentSlot.start_datetime >= datetime.utcnow()).order_by(AppointmentSlot.start_datetime.asc())
