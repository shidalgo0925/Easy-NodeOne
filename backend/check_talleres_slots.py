#!/usr/bin/env python3
"""
Script para verificar slots del servicio "Talleres especializados"
"""
import sys
import os
from datetime import datetime, timezone

# Agregar el directorio backend al path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from app import app, db, AppointmentSlot, AppointmentType

def check_talleres_slots():
    """Verifica los slots del servicio Talleres especializados"""
    with app.app_context():
        print("\n🔍 Buscando servicio 'Talleres especializados'...\n")
        
        # Buscar el servicio por nombre (búsqueda flexible)
        talleres_service = AppointmentType.query.filter(
            AppointmentType.name.ilike('%Talleres especializados%')
        ).first()
        
        if not talleres_service:
            # Intentar otras variaciones
            talleres_service = AppointmentType.query.filter(
                AppointmentType.name.ilike('%Talleres%')
            ).first()
        
        if not talleres_service:
            print("❌ No se encontró el servicio 'Talleres especializados'\n")
            print("📋 Servicios disponibles en el sistema:")
            all_services = AppointmentType.query.all()
            for service in all_services:
                print(f"   - {service.name} (ID: {service.id}, Activo: {service.is_active})")
            return
        
        print(f"✅ Servicio encontrado:")
        print(f"   Nombre: {talleres_service.name}")
        print(f"   ID: {talleres_service.id}")
        print(f"   Activo: {talleres_service.is_active}")
        print(f"   Duración: {talleres_service.duration_minutes} minutos")
        print(f"   Descripción: {talleres_service.description or 'Sin descripción'}")
        print()
        
        # Buscar todos los slots (disponibles y no disponibles)
        all_slots = AppointmentSlot.query.filter(
            AppointmentSlot.appointment_type_id == talleres_service.id
        ).order_by(AppointmentSlot.start_datetime.asc()).all()
        
        print(f"📅 Total de slots registrados: {len(all_slots)}")
        
        # Slots disponibles (futuros y disponibles)
        now = datetime.now(timezone.utc)
        available_slots = AppointmentSlot.query.filter(
            AppointmentSlot.appointment_type_id == talleres_service.id,
            AppointmentSlot.is_available == True,
            AppointmentSlot.start_datetime >= now
        ).order_by(AppointmentSlot.start_datetime.asc()).all()
        
        print(f"✅ Slots disponibles (futuros): {len(available_slots)}")
        
        # Slots pasados
        past_slots = AppointmentSlot.query.filter(
            AppointmentSlot.appointment_type_id == talleres_service.id,
            AppointmentSlot.start_datetime < now
        ).count()
        
        print(f"📆 Slots pasados: {past_slots}")
        
        # Slots no disponibles
        unavailable_slots = AppointmentSlot.query.filter(
            AppointmentSlot.appointment_type_id == talleres_service.id,
            AppointmentSlot.is_available == False,
            AppointmentSlot.start_datetime >= now
        ).count()
        
        print(f"🚫 Slots no disponibles (futuros): {unavailable_slots}")
        print()
        
        if available_slots:
            print("📋 Próximos slots disponibles:")
            print("-" * 80)
            for i, slot in enumerate(available_slots[:20], 1):  # Mostrar hasta 20
                advisor_name = "Sin asesor"
                if slot.advisor and slot.advisor.user:
                    advisor_name = f"{slot.advisor.user.first_name} {slot.advisor.user.last_name}"
                
                remaining = slot.remaining_seats()
                status = "✅ Disponible" if remaining > 0 else "❌ Completo"
                
                print(f"{i}. {slot.start_datetime.strftime('%Y-%m-%d %H:%M')} - {slot.end_datetime.strftime('%H:%M')}")
                print(f"   {status} | Cupos: {remaining}/{slot.capacity} | Asesor: {advisor_name}")
                print()
            
            if len(available_slots) > 20:
                print(f"... y {len(available_slots) - 20} slots más")
        else:
            print("⚠️  No hay slots disponibles para este servicio")
            print()
            print("💡 Para crear slots:")
            print("   1. Ve al panel de administración")
            print("   2. Configura disponibilidad en el calendario")
            print("   3. O genera slots automáticamente desde la disponibilidad semanal")

if __name__ == '__main__':
    check_talleres_slots()
