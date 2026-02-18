#!/usr/bin/env python3
"""
Script para verificar slots de citas disponibles
"""
import sys
import os

# Agregar el directorio backend al path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from app import app, db, AppointmentSlot, AppointmentType
from datetime import datetime

def check_slots():
    """Verifica los slots disponibles"""
    with app.app_context():
        print("\n🔍 Verificando slots de citas disponibles...\n")
        
        # Obtener todos los tipos de cita activos
        appointment_types = AppointmentType.query.filter_by(is_active=True).all()
        
        print(f"📋 Tipos de cita activos: {len(appointment_types)}\n")
        
        for appt_type in appointment_types:
            print(f"🏷️  Tipo: {appt_type.name} (ID: {appt_type.id})")
            
            # Slots disponibles para este tipo
            available_slots = AppointmentSlot.query.filter(
                AppointmentSlot.appointment_type_id == appt_type.id,
                AppointmentSlot.is_available == True,
                AppointmentSlot.start_datetime >= datetime.utcnow()
            ).order_by(AppointmentSlot.start_datetime.asc()).all()
            
            print(f"   📅 Slots disponibles: {len(available_slots)}")
            
            if available_slots:
                print(f"   Próximos 5 slots:")
                for slot in available_slots[:5]:
                    advisor_name = "Sin asesor"
                    if slot.advisor and slot.advisor.user:
                        advisor_name = f"{slot.advisor.user.first_name} {slot.advisor.user.last_name}"
                    
                    print(f"      - {slot.start_datetime.strftime('%Y-%m-%d %H:%M')} ({slot.remaining_seats()}/{slot.capacity} cupos) - {advisor_name}")
            else:
                print(f"   ⚠️  No hay slots disponibles para este tipo de cita")
            
            print()
        
        # Total de slots disponibles
        total_slots = AppointmentSlot.query.filter(
            AppointmentSlot.is_available == True,
            AppointmentSlot.start_datetime >= datetime.utcnow()
        ).count()
        
        print(f"📊 Total de slots disponibles en el sistema: {total_slots}\n")
        
        if total_slots == 0:
            print("⚠️  No hay slots disponibles. Para crear slots:")
            print("   1. Ve al panel de administración")
            print("   2. Configura disponibilidad en el calendario")
            print("   3. O genera slots automáticamente desde la disponibilidad semanal\n")

if __name__ == '__main__':
    check_slots()
