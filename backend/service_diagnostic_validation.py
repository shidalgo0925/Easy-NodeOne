#!/usr/bin/env python3
"""
Validaciones y funciones para servicios que requieren cita de diagnóstico.

Este módulo contiene funciones para manejar servicios con requires_diagnostic_appointment=True.
Las citas de diagnóstico van a COLA (no requieren slot al comprar).
El asesor asignará el slot después cuando tenga disponibilidad.
"""

from flask import jsonify
from datetime import datetime


class ServiceDiagnosticValidationError(Exception):
    """Excepción personalizada para errores de validación de servicios con diagnóstico"""
    pass


def validate_service_purchase(service, slot_id=None, user=None):
    """
    Valida que un servicio con requires_diagnostic_appointment=True
    tenga un slot seleccionado y válido.
    
    Args:
        service: Instancia del modelo Service
        slot_id: ID del slot seleccionado (opcional)
        user: Usuario que intenta comprar (opcional, para validaciones adicionales)
    
    Returns:
        tuple: (is_valid, error_message, slot)
        - is_valid: bool indicando si la validación pasó
        - error_message: str con mensaje de error si falló
        - slot: Instancia de AppointmentSlot si es válido
    
    Raises:
        ServiceDiagnosticValidationError: Si la validación falla
    """
    from app import AppointmentSlot, AppointmentType
    
    # Si el servicio no requiere diagnóstico, no hay validación adicional
    if not service.requires_diagnostic_appointment:
        return True, None, None
    
    # Si requiere diagnóstico, DEBE tener un slot seleccionado
    if not slot_id:
        error_msg = (
            "Este servicio requiere una cita de diagnóstico antes de poder utilizarlo. "
            "Por favor selecciona un horario disponible."
        )
        raise ServiceDiagnosticValidationError(error_msg)
    
    # Validar que el slot existe
    slot = AppointmentSlot.query.get(slot_id)
    if not slot:
        error_msg = "El horario seleccionado no existe."
        raise ServiceDiagnosticValidationError(error_msg)
    
    # Validar que el slot está disponible
    if not slot.is_available:
        error_msg = "El horario seleccionado ya no está disponible."
        raise ServiceDiagnosticValidationError(error_msg)
    
    if slot.remaining_seats() <= 0:
        error_msg = "El horario seleccionado ya no tiene espacios disponibles."
        raise ServiceDiagnosticValidationError(error_msg)
    
    # Validar que el slot corresponde al tipo de cita del servicio
    if service.diagnostic_appointment_type_id:
        if slot.appointment_type_id != service.diagnostic_appointment_type_id:
            error_msg = "El horario seleccionado no corresponde a este servicio."
            raise ServiceDiagnosticValidationError(error_msg)
    
    # Validar que el slot es futuro
    if slot.start_datetime < datetime.utcnow():
        error_msg = "No puedes seleccionar un horario en el pasado."
        raise ServiceDiagnosticValidationError(error_msg)
    
    # Validar que el slot tiene un asesor asignado
    if not slot.advisor_id:
        error_msg = "El horario seleccionado no tiene un asesor asignado."
        raise ServiceDiagnosticValidationError(error_msg)
    
    return True, None, slot


def validate_service_can_be_added_to_cart(service, slot_id=None):
    """
    Valida si un servicio puede ser agregado al carrito.
    
    Para servicios con requires_diagnostic_appointment=True,
    NO requiere slot_id porque la cita va a cola.
    
    Args:
        service: Instancia del modelo Service
        slot_id: ID del slot seleccionado (NO se usa, las citas van a cola)
    
    Returns:
        dict: {
            'can_add': bool,
            'requires_diagnostic': bool,
            'goes_to_queue': bool,
            'error': str (opcional)
        }
    """
    try:
        is_valid, error_msg, slot = validate_service_purchase(service, slot_id)
        return {
            'can_add': is_valid,
            'requires_diagnostic': service.requires_diagnostic_appointment,
            'goes_to_queue': service.requires_diagnostic_appointment,  # Va a cola
            'error': None,
            'slot': None  # No hay slot, va a cola
        }
    except ServiceDiagnosticValidationError as e:
        return {
            'can_add': False,
            'requires_diagnostic': service.requires_diagnostic_appointment,
            'goes_to_queue': service.requires_diagnostic_appointment,
            'error': str(e),
            'slot': None
        }


def get_available_slots_for_service(service, limit=50):
    """
    Obtiene los slots disponibles para un servicio que requiere diagnóstico.
    
    Args:
        service: Instancia del modelo Service
        limit: Límite de resultados (default: 50)
    
    Returns:
        list: Lista de AppointmentSlot disponibles
    """
    from app import AppointmentSlot
    
    if not service.requires_diagnostic_appointment:
        return []
    
    if not service.diagnostic_appointment_type_id:
        return []
    
    slots = AppointmentSlot.query.filter(
        AppointmentSlot.appointment_type_id == service.diagnostic_appointment_type_id,
        AppointmentSlot.is_available == True,
        AppointmentSlot.start_datetime >= datetime.utcnow(),
        AppointmentSlot.reserved_seats < AppointmentSlot.capacity
    ).order_by(
        AppointmentSlot.start_datetime.asc()
    ).limit(limit).all()
    
    return slots


def create_diagnostic_appointment_from_payment(service, user, payment):
    """
    Crea un Appointment en cola (pending) después de un pago exitoso.
    El asesor asignará el slot después.
    
    Args:
        service: Instancia del modelo Service
        user: Instancia del modelo User
        payment: Instancia del modelo Payment
    
    Returns:
        Appointment: La cita creada en cola (status='pending', sin slot)
    """
    from app import Appointment, AppointmentType, db, Advisor, AppointmentAdvisor
    from datetime import datetime
    
    # Calcular precio según membresía del usuario
    active_membership = user.get_active_membership()
    membership_type = active_membership.membership_type if active_membership else 'basic'
    
    # Obtener pricing del servicio (la cita usa el precio del servicio)
    pricing = service.pricing_for_membership(membership_type)
    base_price = pricing['base_price']
    final_price = pricing['final_price']
    discount = base_price - final_price
    
    # Obtener el tipo de cita de diagnóstico
    appointment_type_id = service.diagnostic_appointment_type_id
    if not appointment_type_id:
        raise ValueError(f"El servicio {service.name} requiere diagnóstico pero no tiene appointment_type_id configurado")
    
    # Asignar un asesor disponible (el primero disponible, o se puede mejorar la lógica)
    # Por ahora, asignar el primer asesor activo que tenga este tipo de cita
    advisor_assignment = AppointmentAdvisor.query.filter_by(
        appointment_type_id=appointment_type_id,
        is_active=True
    ).first()
    
    if not advisor_assignment:
        raise ValueError(f"No hay asesores disponibles para el tipo de cita de diagnóstico")
    
    advisor_id = advisor_assignment.advisor_id
    
    # Obtener posición en cola (contar citas pendientes sin slot)
    queue_position = Appointment.query.filter(
        Appointment.service_id.isnot(None),
        Appointment.status == 'pending',
        Appointment.slot_id.is_(None)
    ).count() + 1
    
    # Crear la cita en cola (pending, sin slot, sin fecha)
    appointment = Appointment(
        appointment_type_id=appointment_type_id,
        advisor_id=advisor_id,
        slot_id=None,  # Sin slot, está en cola
        user_id=user.id,
        service_id=service.id,
        payment_id=payment.id,
        membership_type=membership_type,
        is_group=False,
        start_datetime=None,  # Se asignará cuando el asesor confirme
        end_datetime=None,  # Se asignará cuando el asesor confirme
        status='pending',  # En cola, esperando asignación de slot
        advisor_confirmed=False,  # No confirmado aún
        advisor_confirmed_at=None,
        queue_position=queue_position,
        base_price=base_price,
        final_price=final_price,
        discount_applied=discount,
        payment_status='paid',
        payment_method=payment.payment_method if hasattr(payment, 'payment_method') else 'stripe',
        payment_reference=payment.stripe_payment_id if hasattr(payment, 'stripe_payment_id') else None,
        user_notes=f"Cita de diagnóstico para servicio: {service.name} (en cola, esperando asignación de horario)"
    )
    
    db.session.add(appointment)
    db.session.commit()
    
    return appointment
