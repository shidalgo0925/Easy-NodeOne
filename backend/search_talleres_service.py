#!/usr/bin/env python3
"""
Script para buscar exhaustivamente el servicio "Talleres especializados"
"""
import sys
import os
from datetime import datetime, timezone

# Agregar el directorio backend al path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from app import app, db, AppointmentSlot, AppointmentType

def search_talleres_service():
    """Busca exhaustivamente el servicio Talleres especializados"""
    with app.app_context():
        print("\n🔍 Búsqueda exhaustiva de 'Talleres especializados'...\n")
        
        # Buscar todos los servicios que contengan "Taller" o "taller"
        print("📋 Buscando servicios con 'Taller' en el nombre:")
        talleres_services = AppointmentType.query.filter(
            db.or_(
                AppointmentType.name.ilike('%Taller%'),
                AppointmentType.name.ilike('%taller%'),
                AppointmentType.name.ilike('%especializado%'),
                AppointmentType.name.ilike('%Especializado%')
            )
        ).all()
        
        if talleres_services:
            for service in talleres_services:
                print(f"\n✅ Servicio encontrado:")
                print(f"   ID: {service.id}")
                print(f"   Nombre: {service.name}")
                print(f"   Activo: {service.is_active}")
                print(f"   Duración: {service.duration_minutes} minutos")
                print(f"   Descripción: {service.description or 'Sin descripción'}")
                
                # Buscar slots
                now = datetime.now(timezone.utc)
                available_slots = AppointmentSlot.query.filter(
                    AppointmentSlot.appointment_type_id == service.id,
                    AppointmentSlot.is_available == True,
                    AppointmentSlot.start_datetime >= now
                ).order_by(AppointmentSlot.start_datetime.asc()).all()
                
                total_slots = AppointmentSlot.query.filter(
                    AppointmentSlot.appointment_type_id == service.id
                ).count()
                
                print(f"   📅 Total slots registrados: {total_slots}")
                print(f"   ✅ Slots disponibles (futuros): {len(available_slots)}")
                
                if available_slots:
                    print(f"\n   Próximos 10 slots disponibles:")
                    for i, slot in enumerate(available_slots[:10], 1):
                        advisor_name = "Sin asesor"
                        if slot.advisor and slot.advisor.user:
                            advisor_name = f"{slot.advisor.user.first_name} {slot.advisor.user.last_name}"
                        
                        remaining = slot.remaining_seats()
                        print(f"      {i}. {slot.start_datetime.strftime('%Y-%m-%d %H:%M')} - {slot.end_datetime.strftime('%H:%M')} | {remaining}/{slot.capacity} cupos | {advisor_name}")
        else:
            print("❌ No se encontró ningún servicio con 'Taller' en el nombre\n")
        
        # Mostrar TODOS los servicios para referencia
        print("\n" + "="*80)
        print("📋 TODOS los servicios en el sistema (para referencia):")
        print("="*80)
        all_services = AppointmentType.query.order_by(AppointmentType.id).all()
        for service in all_services:
            status = "✅ Activo" if service.is_active else "❌ Inactivo"
            print(f"\n   ID: {service.id} | {status}")
            print(f"   Nombre: {service.name}")
            if service.description:
                print(f"   Descripción: {service.description[:100]}...")
            
            # Contar slots
            total_slots = AppointmentSlot.query.filter(
                AppointmentSlot.appointment_type_id == service.id
            ).count()
            
            now = datetime.now(timezone.utc)
            available_slots = AppointmentSlot.query.filter(
                AppointmentSlot.appointment_type_id == service.id,
                AppointmentSlot.is_available == True,
                AppointmentSlot.start_datetime >= now
            ).count()
            
            print(f"   Slots: {available_slots} disponibles de {total_slots} totales")

if __name__ == '__main__':
    search_talleres_service()
