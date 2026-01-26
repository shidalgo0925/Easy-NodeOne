#!/usr/bin/env python3
"""
Rutas y vistas para la gestión de citas (appointments) tanto para miembros
como para administradores, inspiradas en el flujo de Odoo.
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

# Blueprints
appointments_bp = Blueprint('appointments', __name__, url_prefix='/appointments')
admin_appointments_bp = Blueprint('admin_appointments', __name__, url_prefix='/admin/appointments')
appointments_api_bp = Blueprint('appointments_api', __name__, url_prefix='/api/appointments')

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
    global ActivityLog

    if db is not None:
        return

    from app import (
        db as _db,
        User as _User,
        Advisor as _Advisor,
        AppointmentType as _AppointmentType,
        AppointmentAdvisor as _AppointmentAdvisor,
        AppointmentSlot as _AppointmentSlot,
        Appointment as _Appointment,
        AppointmentParticipant as _AppointmentParticipant,
        AppointmentPricing as _AppointmentPricing,
        AdvisorAvailability as _AdvisorAvailability,
        AdvisorServiceAvailability as _AdvisorServiceAvailability,
        ActivityLog as _ActivityLog,
    )

    db = _db
    User = _User
    Advisor = _Advisor
    AppointmentType = _AppointmentType
    AppointmentAdvisor = _AppointmentAdvisor
    AppointmentSlot = _AppointmentSlot
    Appointment = _Appointment
    AppointmentParticipant = _AppointmentParticipant
    AppointmentPricing = _AppointmentPricing
    AdvisorAvailability = _AdvisorAvailability
    AdvisorServiceAvailability = _AdvisorServiceAvailability
    ActivityLog = _ActivityLog


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


def _slot_queryset():
    ensure_models()
    return AppointmentSlot.query.filter(AppointmentSlot.start_datetime >= datetime.utcnow()).order_by(AppointmentSlot.start_datetime.asc())


@appointments_bp.route('/')
@login_required
def appointments_home():
    ensure_models()
    membership = current_user.get_active_membership()
    membership_type = membership.membership_type if membership else None

    appointment_types = AppointmentType.query.filter_by(is_active=True).order_by(AppointmentType.display_order.asc()).all()
    types_with_pricing = [
        (appt_type, appt_type.pricing_for_membership(membership_type))
        for appt_type in appointment_types
    ]

    upcoming = Appointment.query.filter(
        Appointment.user_id == current_user.id,
        Appointment.start_datetime >= datetime.utcnow()
    ).order_by(Appointment.start_datetime.asc()).all()

    past = Appointment.query.filter(
        Appointment.user_id == current_user.id,
        Appointment.start_datetime < datetime.utcnow()
    ).order_by(Appointment.start_datetime.desc()).limit(5).all()

    return render_template(
        'appointments/index.html',
        membership=membership,
        types_with_pricing=types_with_pricing,
        upcoming_appointments=upcoming,
        past_appointments=past,
    )


@appointments_bp.route('/type/<int:type_id>')
@login_required
def appointment_type_detail(type_id):
    ensure_models()
    membership = current_user.get_active_membership()
    membership_type = membership.membership_type if membership else None

    appointment_type = AppointmentType.query.get_or_404(type_id)
    pricing = appointment_type.pricing_for_membership(membership_type)
    advisors = [
        assignment.advisor for assignment in appointment_type.advisor_assignments
        if assignment.is_active and assignment.advisor.is_active
    ]

    available_slots = _slot_queryset().filter(
        AppointmentSlot.appointment_type_id == appointment_type.id,
        AppointmentSlot.is_available == True  # noqa
    ).limit(20).all()

    return render_template(
        'appointments/type_detail.html',
        appointment_type=appointment_type,
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

    slot = AppointmentSlot.query.get_or_404(slot_id)
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


@appointments_bp.route('/cancel/<int:appointment_id>', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    ensure_models()
    appointment = Appointment.query.get_or_404(appointment_id)
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

    flash('Tu cita fue cancelada.', 'info')
    return redirect(url_for('appointments.appointments_home'))


# ---------------------------------------------------------------------------
# Vistas Administrativas
# ---------------------------------------------------------------------------
@admin_appointments_bp.route('/')
@admin_required
def admin_appointments_dashboard():
    ensure_models()
    types = AppointmentType.query.order_by(AppointmentType.display_order.asc()).all()
    advisors = Advisor.query.order_by(Advisor.created_at.desc()).all()
    upcoming = _slot_queryset().limit(15).all()
    waiting_confirmation = Appointment.query.filter_by(status='pending').order_by(Appointment.start_datetime.asc()).limit(10).all()

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
    appointment = Appointment.query.get_or_404(appointment_id)
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

    flash('La cita fue confirmada y se notificará al miembro.', 'success')
    return redirect(url_for('admin_appointments.admin_appointments_dashboard'))


@admin_appointments_bp.route('/<int:appointment_id>/cancel', methods=['POST'])
@admin_required
def admin_cancel_appointment(appointment_id):
    ensure_models()
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.status == 'cancelled':
        flash('La cita ya estaba cancelada.', 'info')
        return redirect(url_for('admin_appointments.admin_appointments_dashboard'))

    appointment.status = 'cancelled'
    appointment.cancellation_reason = request.form.get('reason', 'Cancelada por el administrador.')

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

    flash('La cita fue cancelada y los participantes serán notificados.', 'info')
    return redirect(url_for('admin_appointments.admin_appointments_dashboard'))


@admin_appointments_bp.route('/types/create', methods=['GET', 'POST'])
@admin_required
def create_appointment_type():
    ensure_models()
    advisors = Advisor.query.filter_by(is_active=True).order_by(Advisor.created_at.asc()).all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        duration = request.form.get('duration_minutes', type=int) or 60
        base_price = request.form.get('base_price', type=float) or 0.0

        if not name:
            flash('El nombre del servicio es obligatorio.', 'error')
            return redirect(request.url)

        appointment_type = AppointmentType(
            name=name,
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
            advisor = Advisor.query.get(int(advisor_id))
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
    )


@admin_appointments_bp.route('/slots/create', methods=['POST'])
@admin_required
def create_manual_slot():
    ensure_models()
    type_id = request.form.get('appointment_type_id', type=int)
    advisor_id = request.form.get('advisor_id', type=int)
    start_raw = request.form.get('start_datetime', '').strip()
    capacity = request.form.get('capacity', type=int) or 1

    appointment_type = AppointmentType.query.get_or_404(type_id)
    advisor = Advisor.query.get_or_404(advisor_id)

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
    advisors = Advisor.query.order_by(Advisor.created_at.desc()).all()
    available_users = User.query.filter_by(is_advisor=False).order_by(User.first_name.asc()).all()
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
    user = User.query.get_or_404(user_id)

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
    
    # Obtener todos los tipos de cita activos
    appointment_types = AppointmentType.query.filter_by(is_active=True).order_by(AppointmentType.display_order, AppointmentType.name).all()
    
    # Obtener todos los asesores activos
    advisors = Advisor.query.filter_by(is_active=True).order_by(Advisor.created_at.desc()).all()
    
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
    
    return render_template(
        'admin/appointments/service_availability.html',
        appointment_types=appointment_types,
        advisors=advisors,
        availability_map=availability_map,
    )


@admin_appointments_bp.route('/availability/manage/<int:advisor_id>/<int:appointment_type_id>', methods=['GET', 'POST'])
@admin_required
def manage_service_availability(advisor_id, appointment_type_id):
    """Gestionar horarios de disponibilidad de un asesor para un servicio específico"""
    ensure_models()
    
    advisor = Advisor.query.get_or_404(advisor_id)
    appointment_type = AppointmentType.query.get_or_404(appointment_type_id)
    
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
    
    advisor = Advisor.query.get_or_404(advisor_id)
    appointment_type = AppointmentType.query.get_or_404(appointment_type_id)
    
    days_ahead = request.form.get('days_ahead', type=int) or 30
    
    # Importar función desde app.py
    from app import generate_slots_from_availability
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
    
    # Slots disponibles del asesor
    my_slots = AppointmentSlot.query.filter(
        AppointmentSlot.advisor_id == advisor.id,
        AppointmentSlot.start_datetime >= datetime.utcnow(),
        AppointmentSlot.is_available == True
    ).order_by(AppointmentSlot.start_datetime.asc()).limit(20).all()
    
    # Citas confirmadas próximas
    upcoming_appointments = Appointment.query.filter(
        Appointment.advisor_id == advisor.id,
        Appointment.status == 'confirmed',
        Appointment.start_datetime >= datetime.utcnow()
    ).order_by(Appointment.start_datetime.asc()).limit(10).all()
    
    # Cola de citas pendientes (sin slot asignado)
    queue_appointments = Appointment.query.filter(
        Appointment.advisor_id == advisor.id,
        Appointment.status == 'pending',
        Appointment.slot_id.is_(None)
    ).order_by(Appointment.queue_position.asc(), Appointment.created_at.asc()).all()
    
    # Tipos de cita asignados al asesor
    appointment_types = AppointmentType.query.join(AppointmentAdvisor).filter(
        AppointmentAdvisor.advisor_id == advisor.id,
        AppointmentAdvisor.is_active == True,
        AppointmentType.is_active == True
    ).all()
    
    stats = {
        'available_slots': len(my_slots),
        'upcoming_appointments': len(upcoming_appointments),
        'queue_appointments': len(queue_appointments),
        'appointment_types': len(appointment_types)
    }
    
    return render_template(
        'appointments/advisor_dashboard.html',
        advisor=advisor,
        slots=my_slots,  # Espacios disponibles futuros
        all_slots=all_my_slots,  # Todos los slots para ver historial
        occupied_slots=occupied_slots,  # Slots ocupados futuros
        past_slots=past_slots,  # Slots pasados
        upcoming_appointments=upcoming_appointments,
        queue_appointments=queue_appointments,
        appointment_types=appointment_types,
        stats=stats
    )


@appointments_bp.route('/advisor/slots/create', methods=['GET', 'POST'])
@advisor_required
def advisor_create_slot():
    """Crear un slot disponible"""
    ensure_models()
    advisor = Advisor.query.filter_by(user_id=current_user.id).first()
    
    # Tipos de cita asignados al asesor
    appointment_types = AppointmentType.query.join(AppointmentAdvisor).filter(
        AppointmentAdvisor.advisor_id == advisor.id,
        AppointmentAdvisor.is_active == True,
        AppointmentType.is_active == True
    ).all()
    
    if request.method == 'POST':
        type_id = request.form.get('appointment_type_id', type=int)
        start_raw = request.form.get('start_datetime', '').strip()
        capacity = request.form.get('capacity', type=int) or 1
        
        appointment_type = AppointmentType.query.get_or_404(type_id)
        
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
    
    queue_appointments = Appointment.query.filter(
        Appointment.advisor_id == advisor.id,
        Appointment.status == 'pending',
        Appointment.slot_id.is_(None)
    ).order_by(Appointment.queue_position.asc(), Appointment.created_at.asc()).all()
    
    # Slots disponibles del asesor para asignar
    available_slots = AppointmentSlot.query.filter(
        AppointmentSlot.advisor_id == advisor.id,
        AppointmentSlot.start_datetime >= datetime.utcnow(),
        AppointmentSlot.is_available == True,
        AppointmentSlot.reserved_seats < AppointmentSlot.capacity
    ).order_by(AppointmentSlot.start_datetime.asc()).all()
    
    return render_template(
        'appointments/advisor_queue.html',
        advisor=advisor,
        queue_appointments=queue_appointments,
        available_slots=available_slots,
        partially_available_slots=partially_available
    )


@appointments_bp.route('/advisor/queue/<int:appointment_id>/assign-slot', methods=['POST'])
@advisor_required
def advisor_assign_slot_to_appointment(appointment_id):
    """Asignar un slot a una cita en cola"""
    ensure_models()
    advisor = Advisor.query.filter_by(user_id=current_user.id).first()
    
    appointment = Appointment.query.get_or_404(appointment_id)
    
    # Verificar que la cita es del asesor y está en cola
    if appointment.advisor_id != advisor.id:
        flash('Esta cita no te corresponde.', 'error')
        return redirect(url_for('appointments.advisor_queue'))
    
    if appointment.status != 'pending' or appointment.slot_id is not None:
        flash('Esta cita ya tiene un slot asignado o no está en cola.', 'error')
        return redirect(url_for('appointments.advisor_queue'))
    
    slot_id = request.form.get('slot_id', type=int)
    if not slot_id:
        flash('Debes seleccionar un slot.', 'error')
        return redirect(url_for('appointments.advisor_queue'))
    
    slot = AppointmentSlot.query.get_or_404(slot_id)
    
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

