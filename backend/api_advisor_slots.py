#!/usr/bin/env python3
"""
API endpoints para que los asesores gestionen sus slots.
Puede usarse desde el frontend o para debugging.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime

advisor_slots_api_bp = Blueprint('advisor_slots_api', __name__, url_prefix='/api/advisor/slots')

def init_models():
    """Importa modelos cuando sea necesario"""
    from app import db, Advisor, AppointmentSlot, AppointmentType
    return db, Advisor, AppointmentSlot, AppointmentType

@advisor_slots_api_bp.route('/')
@login_required
def list_slots():
    """Listar todos los slots del asesor actual"""
    db, Advisor, AppointmentSlot, AppointmentType = init_models()
    
    if not current_user.is_advisor:
        return jsonify({'error': 'No eres asesor'}), 403
    
    advisor = Advisor.query.filter_by(user_id=current_user.id).first()
    if not advisor:
        return jsonify({'error': 'Perfil de asesor no encontrado'}), 404
    
    # Parámetros de filtro
    show_all = request.args.get('show_all', 'false').lower() == 'true'
    only_available = request.args.get('only_available', 'false').lower() == 'true'
    only_future = request.args.get('only_future', 'true').lower() == 'true'
    
    query = AppointmentSlot.query.filter(
        AppointmentSlot.advisor_id == advisor.id
    )
    
    if only_future:
        query = query.filter(AppointmentSlot.start_datetime >= datetime.utcnow())
    
    if only_available:
        query = query.filter(AppointmentSlot.is_available == True)
    
    slots = query.order_by(AppointmentSlot.start_datetime.asc()).all()
    
    return jsonify({
        'total': len(slots),
        'slots': [
            {
                'id': slot.id,
                'appointment_type_id': slot.appointment_type_id,
                'appointment_type_name': slot.appointment_type.name if slot.appointment_type else None,
                'start_datetime': slot.start_datetime.isoformat() if slot.start_datetime else None,
                'end_datetime': slot.end_datetime.isoformat() if slot.end_datetime else None,
                'capacity': slot.capacity,
                'reserved_seats': slot.reserved_seats or 0,
                'remaining_seats': slot.remaining_seats(),
                'is_available': slot.is_available,
                'is_auto_generated': slot.is_auto_generated,
                'created_at': slot.created_at.isoformat() if slot.created_at else None
            }
            for slot in slots
        ]
    })

@advisor_slots_api_bp.route('/create', methods=['POST'])
@login_required
def create_slot():
    """Crear un nuevo slot"""
    db, Advisor, AppointmentSlot, AppointmentType = init_models()
    
    if not current_user.is_advisor:
        return jsonify({'error': 'No eres asesor'}), 403
    
    advisor = Advisor.query.filter_by(user_id=current_user.id).first()
    if not advisor:
        return jsonify({'error': 'Perfil de asesor no encontrado'}), 404
    
    data = request.get_json()
    appointment_type_id = data.get('appointment_type_id')
    start_datetime_str = data.get('start_datetime')
    capacity = data.get('capacity', 1)
    
    if not appointment_type_id or not start_datetime_str:
        return jsonify({'error': 'appointment_type_id y start_datetime son requeridos'}), 400
    
    # Verificar que el asesor está asignado a este tipo
    from app import AppointmentAdvisor
    assignment = AppointmentAdvisor.query.filter_by(
        appointment_type_id=appointment_type_id,
        advisor_id=advisor.id,
        is_active=True
    ).first()
    
    if not assignment:
        return jsonify({'error': 'No estás asignado a este tipo de cita'}), 403
    
    appointment_type = AppointmentType.query.get(appointment_type_id)
    if not appointment_type:
        return jsonify({'error': 'Tipo de cita no encontrado'}), 404
    
    try:
        start_datetime = datetime.fromisoformat(start_datetime_str.replace('Z', '+00:00'))
    except:
        try:
            start_datetime = datetime.strptime(start_datetime_str, '%Y-%m-%dT%H:%M')
        except:
            return jsonify({'error': 'Formato de fecha inválido. Use: YYYY-MM-DDTHH:MM'}), 400
    
    if start_datetime < datetime.utcnow():
        return jsonify({'error': 'No puedes crear slots en el pasado'}), 400
    
    end_datetime = start_datetime + appointment_type.duration()
    
    # Verificar conflictos
    conflicting = AppointmentSlot.query.filter(
        AppointmentSlot.advisor_id == advisor.id,
        AppointmentSlot.start_datetime < end_datetime,
        AppointmentSlot.end_datetime > start_datetime,
        AppointmentSlot.is_available == True
    ).first()
    
    if conflicting:
        return jsonify({
            'error': f'Ya tienes un slot en ese horario: {conflicting.start_datetime.isoformat()}'
        }), 400
    
    slot = AppointmentSlot(
        appointment_type_id=appointment_type_id,
        advisor_id=advisor.id,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        capacity=max(1, capacity),
        is_auto_generated=False,
        created_by=current_user.id
    )
    
    db.session.add(slot)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'slot': {
            'id': slot.id,
            'start_datetime': slot.start_datetime.isoformat(),
            'end_datetime': slot.end_datetime.isoformat(),
            'capacity': slot.capacity
        }
    }), 201
