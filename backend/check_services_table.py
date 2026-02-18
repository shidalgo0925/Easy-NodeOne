#!/usr/bin/env python3
"""
Script para buscar el servicio "Talleres especializados" en la tabla Service
"""
import sys
import os

# Agregar el directorio backend al path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from app import app, db, Service, AppointmentType

def check_services_table():
    """Busca servicios en la tabla Service"""
    with app.app_context():
        print("\n🔍 Buscando 'Talleres especializados' en tabla Service...\n")
        
        # Buscar servicios con "Taller" en el nombre
        talleres_services = Service.query.filter(
            db.or_(
                Service.name.ilike('%Taller%'),
                Service.name.ilike('%taller%'),
                Service.name.ilike('%especializado%'),
                Service.name.ilike('%Especializado%')
            )
        ).all()
        
        if talleres_services:
            print(f"✅ Encontrados {len(talleres_services)} servicio(s) con 'Taller' en el nombre:\n")
            for service in talleres_services:
                print(f"   ID: {service.id}")
                print(f"   Nombre: {service.name}")
                print(f"   Descripción: {service.description or 'Sin descripción'}")
                print(f"   Activo: {service.is_active}")
                print(f"   Appointment Type ID: {service.appointment_type_id}")
                
                if service.appointment_type_id:
                    appt_type = AppointmentType.query.get(service.appointment_type_id)
                    if appt_type:
                        print(f"   Tipo de cita asociado: {appt_type.name} (ID: {appt_type.id})")
                    else:
                        print(f"   ⚠️  Tipo de cita ID {service.appointment_type_id} no existe")
                else:
                    print(f"   ⚠️  No tiene appointment_type_id asociado")
                print()
        else:
            print("❌ No se encontró ningún servicio con 'Taller' en el nombre\n")
        
        # Mostrar TODOS los servicios
        print("\n" + "="*80)
        print("📋 TODOS los servicios en la tabla Service:")
        print("="*80 + "\n")
        
        all_services = Service.query.order_by(Service.id).all()
        
        if not all_services:
            print("❌ No hay servicios en la tabla Service\n")
        else:
            for service in all_services:
                status = "✅ Activo" if service.is_active else "❌ Inactivo"
                print(f"\nID: {service.id} | {status}")
                print(f"Nombre: {service.name}")
                print(f"Descripción: {service.description or 'Sin descripción'}")
                print(f"Appointment Type ID: {service.appointment_type_id or 'Sin asociar'}")
                
                if service.appointment_type_id:
                    appt_type = AppointmentType.query.get(service.appointment_type_id)
                    if appt_type:
                        print(f"Tipo de cita: {appt_type.name} (Activo: {appt_type.is_active})")
                    else:
                        print(f"⚠️  Tipo de cita ID {service.appointment_type_id} NO EXISTE")
                print("-" * 80)
            
            print(f"\n📊 Total: {len(all_services)} servicio(s)")

if __name__ == '__main__':
    check_services_table()
