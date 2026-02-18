#!/usr/bin/env python3
"""
Script para listar TODOS los tipos de citas (activos e inactivos)
"""
import sys
import os
from datetime import datetime, timezone

# Agregar el directorio backend al path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from app import app, db, AppointmentSlot, AppointmentType

def check_all_appointment_types():
    """Lista todos los tipos de citas"""
    with app.app_context():
        print("\n" + "="*80)
        print("📋 TODOS los tipos de citas en el sistema (activos e inactivos)")
        print("="*80 + "\n")
        
        all_types = AppointmentType.query.order_by(AppointmentType.id).all()
        
        if not all_types:
            print("❌ No hay tipos de citas registrados en el sistema\n")
            return
        
        for appt_type in all_types:
            status = "✅ ACTIVO" if appt_type.is_active else "❌ INACTIVO"
            print(f"\n{'='*80}")
            print(f"ID: {appt_type.id} | {status}")
            print(f"Nombre: {appt_type.name}")
            print(f"Descripción: {appt_type.description or 'Sin descripción'}")
            print(f"Duración: {appt_type.duration_minutes} minutos")
            print(f"Categoría: {appt_type.service_category or 'Sin categoría'}")
            print(f"Icono: {appt_type.icon or 'Sin icono'}")
            print(f"Color: {appt_type.color_tag or 'Sin color'}")
            print(f"Orden de visualización: {appt_type.display_order}")
            
            # Contar slots
            total_slots = AppointmentSlot.query.filter(
                AppointmentSlot.appointment_type_id == appt_type.id
            ).count()
            
            now = datetime.now(timezone.utc)
            available_slots = AppointmentSlot.query.filter(
                AppointmentSlot.appointment_type_id == appt_type.id,
                AppointmentSlot.is_available == True,
                AppointmentSlot.start_datetime >= now
            ).count()
            
            past_slots = AppointmentSlot.query.filter(
                AppointmentSlot.appointment_type_id == appt_type.id,
                AppointmentSlot.start_datetime < now
            ).count()
            
            print(f"\n📅 Slots:")
            print(f"   - Totales registrados: {total_slots}")
            print(f"   - Disponibles (futuros): {available_slots}")
            print(f"   - Pasados: {past_slots}")
            
            if available_slots > 0:
                print(f"\n   Próximos 3 slots disponibles:")
                next_slots = AppointmentSlot.query.filter(
                    AppointmentSlot.appointment_type_id == appt_type.id,
                    AppointmentSlot.is_available == True,
                    AppointmentSlot.start_datetime >= now
                ).order_by(AppointmentSlot.start_datetime.asc()).limit(3).all()
                
                for slot in next_slots:
                    advisor_name = "Sin asesor"
                    if slot.advisor and slot.advisor.user:
                        advisor_name = f"{slot.advisor.user.first_name} {slot.advisor.user.last_name}"
                    print(f"      • {slot.start_datetime.strftime('%Y-%m-%d %H:%M')} - {slot.remaining_seats()}/{slot.capacity} cupos - {advisor_name}")
        
        print("\n" + "="*80)
        print(f"📊 Resumen: {len(all_types)} tipo(s) de cita en total")
        print("="*80 + "\n")

if __name__ == '__main__':
    check_all_appointment_types()
