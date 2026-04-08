# Lógica de servicios (usuario): listado, solicitud de cita, calendario API.
from datetime import datetime, timedelta
import json

from app import (
    Service,
    ServiceCategory,
    ServicePricingRule,
    AppointmentAdvisor,
    AppointmentSlot,
    Advisor,
)
from sqlalchemy.orm import joinedload

from . import repository


# Fallback cuando no hay tabla membership_plan
PLANS_INFO_FALLBACK = {
    'basic': {'name': 'GRATIS / BÁSICO', 'price': '$0', 'badge': 'Incluido con la membresía gratuita', 'color': 'bg-success'},
    'pro': {'name': 'PRO', 'price': '$60/año', 'badge': 'Plan recomendado', 'color': 'bg-info'},
    'premium': {'name': 'PREMIUM', 'price': '$120/año', 'badge': 'Más beneficios', 'color': 'bg-primary'},
    'deluxe': {'name': 'DE LUXE', 'price': '$200/año', 'badge': 'Experiencia completa', 'color': 'bg-warning text-dark'},
    'corporativo': {'name': 'CORPORATIVO', 'price': '$300/año', 'badge': 'Para empresas', 'color': 'bg-dark text-white'},
}


def _get_plans_info(user=None, organization_id=None):
    """Etiquetas de planes para /services: BD (MembershipPlan) + fallback para slugs sin fila en BD."""
    fb = PLANS_INFO_FALLBACK.copy()
    try:
        from app import MembershipPlan, _enable_multi_tenant_catalog

        oid = None
        if organization_id is not None:
            try:
                oid = int(organization_id)
            except (TypeError, ValueError):
                oid = None
        elif user is not None and _enable_multi_tenant_catalog():
            oid = int(getattr(user, 'organization_id', None) or 1)
        out = MembershipPlan.get_plans_info(organization_id=oid)
        if not out:
            return fb
        merged = dict(fb)
        merged.update(out)
        return merged
    except Exception:
        return fb


def get_services_page_data(user=None, organization_id=None):
    """
    Datos para la página /services.
    organization_id: si se pasa (p. ej. visitante anónimo en subdominio tenant), filtra catálogo por esa org.
    """
    if user is not None and getattr(user, 'is_authenticated', False):
        active_membership = user.get_active_membership()
    else:
        active_membership = None
    membership_type = active_membership.membership_type if active_membership else 'basic'

    org_kw = {}
    if organization_id is not None:
        org_kw['organization_id'] = int(organization_id)

    categories = repository.get_active_categories(**org_kw)
    all_services = repository.get_active_services(**org_kw)
    services_by_plan = {}
    for service in all_services:
        pricing_rules = ServicePricingRule.query.filter_by(
            service_id=service.id, is_active=True
        ).all()
        available_plans = set()
        if service.membership_type:
            available_plans.add(service.membership_type)
        for rule in pricing_rules:
            available_plans.add(rule.membership_type)
        if not available_plans:
            mt = (getattr(service, 'membership_type', None) or 'basic')
            if isinstance(mt, str):
                mt = mt.strip()
            available_plans.add(mt if mt else 'basic')
        user_pricing = service.pricing_for_membership(membership_type)
        at_id = service.appointment_type_id or getattr(service, 'diagnostic_appointment_type_id', None)
        advisors_list = []
        if at_id:
            for aa in AppointmentAdvisor.query.filter_by(appointment_type_id=at_id, is_active=True).all():
                if aa.advisor and getattr(aa.advisor, 'is_active', True) and aa.advisor.user:
                    advisors_list.append({
                        'id': aa.advisor.id,
                        'name': f"{aa.advisor.user.first_name} {aa.advisor.user.last_name}"
                    })
        service_data = {
            'id': service.id,
            'name': service.name,
            'description': service.description,
            'icon': service.icon or 'fas fa-cog',
            'external_link': service.external_link,
            'base_price': service.base_price,
            'pricing': user_pricing,
            'requires_diagnostic_appointment': service.requires_diagnostic_appointment if service.requires_diagnostic_appointment is not None else False,
            'appointment_type_id': service.appointment_type_id,
            'requires_appointment': service.requires_appointment(),
            'is_free': service.is_free_service(membership_type),
            'service_type': getattr(service, 'service_type', 'AGENDABLE') or 'AGENDABLE',
            'advisors': advisors_list,
            'diagnostic_appointment_type_id': getattr(service, 'diagnostic_appointment_type_id', None),
        }
        for plan_type in available_plans:
            if plan_type not in services_by_plan:
                services_by_plan[plan_type] = []
            services_by_plan[plan_type].append(service_data)
    oid_plans = organization_id
    if oid_plans is None and user is not None and getattr(user, 'is_authenticated', False):
        oid_plans = getattr(user, 'organization_id', None)

    return {
        'membership': active_membership,
        'services_by_plan': services_by_plan,
        'plans_info': _get_plans_info(user, organization_id=oid_plans),
        'categories': categories,
        'user_membership_type': membership_type,
        'membership_type': membership_type,
    }


def get_request_appointment_data(service_id, user, selected_advisor_id=None, return_url=None):
    """
    Devuelve (data_dict, None) para render o (None, (redirect_url, code)) en caso de error.
    """
    from flask import url_for
    service = repository.get_service_or_404(service_id)
    if not service.is_active:
        return None, (url_for('services.list'), 'Este servicio no está disponible.', 'error')
    if not service.requires_appointment():
        return None, (url_for('services.list'), 'Este servicio no requiere cita.', 'info')
    membership = user.get_active_membership()
    if not membership:
        return None, (url_for('services.list'), 'Necesitas una membresía activa para solicitar citas.', 'warning')
    membership_type = membership.membership_type
    if service.is_free_service(membership_type):
        return None, (url_for('services.list'), 'Este servicio es gratuito y no requiere cita con pago.', 'info')
    appointment_type = repository.get_appointment_type(service.appointment_type_id)
    if not appointment_type or not appointment_type.is_active:
        return None, (url_for('services.list'), 'El tipo de cita asociado no está disponible.', 'error')
    pricing = service.pricing_for_membership(membership_type)
    deposit_info = service.calculate_deposit(membership_type)
    today = datetime.utcnow().date()
    future_date = today + timedelta(days=90)
    advisors_list = []
    advisors_with_schedules = set()
    for assignment in repository.get_advisor_assignments(service.appointment_type_id):
        if not assignment.is_active or not assignment.advisor.is_active:
            continue
        advisor = assignment.advisor
        aid = advisor.id
        if not repository.advisor_has_availability(aid, service.appointment_type_id, today, future_date):
            continue
        advisors_list.append({
            'id': advisor.id,
            'name': f"{advisor.user.first_name} {advisor.user.last_name}" if advisor.user else 'Asesor',
            'bio': advisor.bio,
            'specializations': advisor.specializations,
            'photo_url': advisor.photo_url
        })
        advisors_with_schedules.add(aid)
    if not advisors_list:
        return None, (url_for('services.list'), 'Este servicio no tiene asesores con horarios configurados. Por favor, contacta al administrador.', 'error')
    # Generar slots si faltan
    from nodeone.modules.appointments.slot_generation import generate_slots_from_availability
    for aid in advisors_with_schedules:
        try:
            if repository.count_slots(aid, service.appointment_type_id, 30) < 10:
                try:
                    generate_slots_from_availability(aid, service.appointment_type_id, days_ahead=30)
                except Exception:
                    pass
        except Exception:
            continue
    slots = AppointmentSlot.query.options(
        joinedload(AppointmentSlot.advisor).joinedload(Advisor.user)
    ).filter(
        AppointmentSlot.appointment_type_id == service.appointment_type_id,
        AppointmentSlot.start_datetime >= datetime.utcnow(),
        AppointmentSlot.start_datetime <= datetime.utcnow() + timedelta(days=30),
        AppointmentSlot.is_available == True
    ).order_by(AppointmentSlot.start_datetime.asc()).limit(200).all()
    slots_data = []
    for slot in slots:
        try:
            advisor_name = 'Asesor'
            if slot.advisor:
                advisor_name = (f"{slot.advisor.user.first_name} {slot.advisor.user.last_name}" if slot.advisor.user else f"Asesor #{slot.advisor.id}")
            slots_data.append({
                'id': slot.id,
                'advisor_id': slot.advisor_id,
                'advisor_name': advisor_name,
                'start_datetime': slot.start_datetime.isoformat() if slot.start_datetime else None,
                'end_datetime': slot.end_datetime.isoformat() if slot.end_datetime else None,
                'capacity': slot.capacity if slot.capacity else 1,
                'remaining_seats': slot.remaining_seats() if hasattr(slot, 'remaining_seats') else 1
            })
        except Exception:
            continue
    return {
        'service': service,
        'appointment_type': appointment_type,
        'advisors': advisors_list,
        'selected_advisor_id': selected_advisor_id,
        'membership': membership,
        'pricing': pricing,
        'deposit_info': deposit_info,
        'available_slots_json': json.dumps(slots_data),
        'available_slots': slots,
        'user': user,
        'return_url': return_url,
    }, None


def submit_request_appointment(service_id, user, form):
    """
    Valida formulario y agrega al carrito. Devuelve (redirect_response, None) o (None, (redirect_url, flash_message, flash_category)).
    """
    from flask import url_for
    from app import add_to_cart, db
    service = repository.get_service_or_404(service_id)
    if not service.is_active or not service.requires_appointment():
        return None, (url_for('services.list'), 'Este servicio no está disponible para citas.', 'error')
    membership = user.get_active_membership()
    if not membership:
        return None, (url_for('services.list'), 'Necesitas una membresía activa.', 'warning')
    slot_id = form.get('slot_id', type=int)
    case_description = (form.get('case_description') or '').strip()
    if not case_description or len(case_description) < 20:
        return None, (url_for('services.request_appointment', service_id=service_id), 'La descripción del caso debe tener al menos 20 caracteres.', 'error')
    if len(case_description) > 1000:
        return None, (url_for('services.request_appointment', service_id=service_id), 'La descripción del caso no puede exceder 1000 caracteres.', 'error')
    if not slot_id:
        return None, (url_for('services.request_appointment', service_id=service_id), 'Debes seleccionar un horario disponible.', 'error')
    slot = AppointmentSlot.query.get_or_404(slot_id)
    if slot.appointment_type_id != service.appointment_type_id:
        return None, (url_for('services.request_appointment', service_id=service_id), 'El horario seleccionado no corresponde a este servicio.', 'error')
    if not slot.is_available or slot.remaining_seats() <= 0:
        return None, (url_for('services.request_appointment', service_id=service_id), 'Este horario ya no está disponible. Por favor selecciona otro.', 'warning')
    membership_type = membership.membership_type
    pricing = service.pricing_for_membership(membership_type)
    final_price = pricing['final_price']
    cart_metadata = {
        'service_id': service.id,
        'service_name': service.name,
        'slot_id': slot.id,
        'slot_datetime': slot.start_datetime.isoformat(),
        'case_description': case_description,
        'final_price': final_price,
        'appointment_type_id': service.appointment_type_id,
        'advisor_id': slot.advisor_id,
        'requires_appointment': True,
        'slot_end_datetime': slot.end_datetime.isoformat() if slot.end_datetime else None
    }
    try:
        add_to_cart(
            user_id=user.id,
            product_type='service',
            product_id=service.id,
            product_name=f"{service.name} - Cita",
            unit_price=int(final_price * 100),
            quantity=1,
            product_description=f"Servicio con cita agendada: {case_description[:100]}...",
            metadata=cart_metadata
        )
        return ('payments.cart', None, None), None  # redirect to cart
    except Exception as e:
        db.session.rollback()
        return None, (url_for('services.request_appointment', service_id=service_id), str(e), 'error')


def get_calendar_data(service_id, start_date=None, end_date=None, advisor_id_filter=None):
    """
    Datos para GET /api/services/<id>/calendar. Devuelve dict para jsonify o (None, error_msg, status_code).
    """
    from nodeone.modules.appointments.slot_generation import generate_slots_from_availability
    from app import Advisor, Appointment
    service = repository.get_service_or_404(service_id)
    if not service.is_active:
        return None, 'Este servicio no está disponible', 400
    if not service.requires_appointment():
        return None, 'Este servicio no requiere cita', 400
    appointment_type_id = service.appointment_type_id
    if not appointment_type_id:
        return None, 'Este servicio no tiene tipo de cita configurado', 400
    appointment_type = repository.get_appointment_type(appointment_type_id)
    if not appointment_type or not appointment_type.is_active:
        return None, 'El tipo de cita asociado no está disponible', 400
    advisor_assignments = AppointmentAdvisor.query.filter_by(
        appointment_type_id=appointment_type_id, is_active=True
    ).join(Advisor).filter(Advisor.is_active == True).all()
    if not advisor_assignments:
        return {
            'success': True,
            'service': {'id': service.id, 'name': service.name},
            'advisors': [],
            'events': [],
            'total_slots': 0,
            'message': 'No hay asesores asignados a este servicio'
        }, None, None
    advisor_ids = [aa.advisor_id for aa in advisor_assignments]
    if advisor_id_filter and advisor_id_filter not in advisor_ids:
        return None, 'Asesor no asignado a este servicio', 400
    if advisor_id_filter:
        advisor_ids = [advisor_id_filter]
    for aid in advisor_ids:
        if repository.count_slots(aid, appointment_type_id, 30) < 10:
            try:
                generate_slots_from_availability(aid, appointment_type_id, days_ahead=30)
            except Exception:
                pass
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
    slots = AppointmentSlot.query.options(
        joinedload(AppointmentSlot.advisor).joinedload(Advisor.user)
    ).filter(
        AppointmentSlot.appointment_type_id == appointment_type_id,
        AppointmentSlot.advisor_id.in_(advisor_ids),
        AppointmentSlot.start_datetime >= start_dt,
        AppointmentSlot.start_datetime < end_dt,
        AppointmentSlot.is_available == True
    ).order_by(AppointmentSlot.start_datetime.asc()).all()
    appointments = Appointment.query.options(
        joinedload(Appointment.advisor).joinedload(Advisor.user)
    ).filter(
        Appointment.appointment_type_id == appointment_type_id,
        Appointment.advisor_id.in_(advisor_ids),
        Appointment.status.in_(['CONFIRMADA', 'PENDIENTE', 'confirmed', 'pending']),
        Appointment.start_datetime.isnot(None),
        Appointment.start_datetime >= start_dt,
        Appointment.start_datetime < end_dt
    ).all()
    calendar_events = []
    for slot in slots:
        try:
            advisor_name = 'Asesor'
            if slot.advisor and slot.advisor.user:
                advisor_name = f"{slot.advisor.user.first_name} {slot.advisor.user.last_name}"
            elif slot.advisor:
                advisor_name = f"Asesor #{slot.advisor.id}"
            if not slot.start_datetime or not slot.end_datetime:
                continue
            remaining = slot.remaining_seats() if hasattr(slot, 'remaining_seats') else (slot.capacity or 1)
            calendar_events.append({
                'id': f'slot_{slot.id}',
                'title': f'Disponible - {advisor_name}',
                'start': slot.start_datetime.isoformat(),
                'end': slot.end_datetime.isoformat(),
                'backgroundColor': '#28a745',
                'borderColor': '#28a745',
                'textColor': '#fff',
                'extendedProps': {
                    'type': 'slot', 'slot_id': slot.id, 'advisor_id': slot.advisor_id,
                    'advisor_name': advisor_name, 'service_id': service_id, 'service_name': service.name,
                    'remaining_seats': remaining, 'capacity': slot.capacity or 1, 'available': True
                }
            })
        except Exception:
            continue
    for apt in appointments:
        if not apt.start_datetime or not apt.end_datetime:
            continue
        try:
            advisor_name = 'Asesor'
            if apt.advisor and apt.advisor.user:
                advisor_name = f"{apt.advisor.user.first_name} {apt.advisor.user.last_name}"
            label = 'Confirmada' if apt.status in ('CONFIRMADA', 'confirmed') else 'Pendiente'
            calendar_events.append({
                'id': f'apt_{apt.id}',
                'title': f'Cita ({label}) - {advisor_name}',
                'start': apt.start_datetime.isoformat(),
                'end': (apt.end_datetime or apt.start_datetime).isoformat(),
                'backgroundColor': '#17a2b8' if apt.status in ('PENDIENTE', 'pending') else '#6f42c1',
                'borderColor': '#17a2b8' if apt.status in ('PENDIENTE', 'pending') else '#6f42c1',
                'textColor': '#fff',
                'extendedProps': {'type': 'appointment', 'appointment_id': apt.id, 'status': apt.status, 'advisor_id': apt.advisor_id}
            })
        except Exception:
            continue
    advisors_info = []
    for assignment in advisor_assignments:
        advisor = assignment.advisor
        if advisor_id_filter and advisor.id != advisor_id_filter:
            continue
        name = (f"{advisor.user.first_name} {advisor.user.last_name}" if advisor.user else f"Asesor #{advisor.id}")
        advisors_info.append({
            'id': advisor.id,
            'name': name,
            'bio': advisor.bio or '',
            'specializations': advisor.specializations or '',
            'photo_url': advisor.photo_url or ''
        })
    return {
        'success': True,
        'service': {
            'id': service.id,
            'name': service.name,
            'appointment_type_id': appointment_type_id,
            'appointment_type_name': appointment_type.name,
            'duration_minutes': appointment_type.duration_minutes
        },
        'advisors': advisors_info,
        'events': calendar_events,
        'total_slots': len(calendar_events),
        'date_range': {'start': start_dt.isoformat(), 'end': end_dt.isoformat()}
    }, None, None
