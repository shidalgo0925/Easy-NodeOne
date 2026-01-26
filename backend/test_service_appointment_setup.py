#!/usr/bin/env python3
"""
Script para configurar un servicio de prueba con citas y verificar el flujo.
Ejecutar con: python backend/test_service_appointment_setup.py
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Service, AppointmentType, Advisor, AppointmentSlot, AppointmentAdvisor, User

def setup_test_service():
    """Configura un servicio de prueba con citas."""
    
    with app.app_context():
        print("=" * 60)
        print("CONFIGURACIÓN DE SERVICIO DE PRUEBA PARA CITAS")
        print("=" * 60)
        print()
        
        # 1. Verificar tipos de cita disponibles
        appointment_types = AppointmentType.query.filter_by(is_active=True).all()
        if not appointment_types:
            print("❌ No hay tipos de cita activos. Creando uno de prueba...")
            appointment_type = AppointmentType(
                name="Consulta General",
                description="Consulta general para servicios",
                duration_minutes=60,
                base_price=50.0,
                is_active=True
            )
            db.session.add(appointment_type)
            db.session.commit()
            print(f"✅ Tipo de cita creado: {appointment_type.name} (ID: {appointment_type.id})")
        else:
            appointment_type = appointment_types[0]
            print(f"✅ Usando tipo de cita: {appointment_type.name} (ID: {appointment_type.id})")
        
        # 2. Verificar asesores
        advisors = Advisor.query.filter_by(is_active=True).all()
        if not advisors:
            print("❌ No hay asesores activos. Necesitas crear al menos uno.")
            return False
        
        advisor = advisors[0]
        print(f"✅ Usando asesor: {advisor.user.first_name} {advisor.user.last_name} (ID: {advisor.id})")
        
        # 3. Verificar asignación de asesor al tipo de cita
        assignment = AppointmentAdvisor.query.filter_by(
            appointment_type_id=appointment_type.id,
            advisor_id=advisor.id,
            is_active=True
        ).first()
        
        if not assignment:
            print("📝 Asignando asesor al tipo de cita...")
            assignment = AppointmentAdvisor(
                appointment_type_id=appointment_type.id,
                advisor_id=advisor.id,
                priority=1,
                is_active=True
            )
            db.session.add(assignment)
            db.session.commit()
            print("✅ Asesor asignado correctamente")
        else:
            print("✅ Asesor ya está asignado al tipo de cita")
        
        # 4. Verificar slots disponibles
        slots = AppointmentSlot.query.filter(
            AppointmentSlot.appointment_type_id == appointment_type.id,
            AppointmentSlot.start_datetime >= datetime.utcnow(),
            AppointmentSlot.is_available == True
        ).count()
        
        if slots == 0:
            print("⚠️  No hay slots disponibles. Creando slots de prueba...")
            # Crear 5 slots para los próximos días
            for i in range(1, 6):
                start_time = datetime.utcnow() + timedelta(days=i, hours=10)
                end_time = start_time + timedelta(minutes=appointment_type.duration_minutes)
                
                slot = AppointmentSlot(
                    appointment_type_id=appointment_type.id,
                    advisor_id=advisor.id,
                    start_datetime=start_time,
                    end_datetime=end_time,
                    capacity=1,
                    is_available=True,
                    is_auto_generated=False
                )
                db.session.add(slot)
            
            db.session.commit()
            print("✅ 5 slots de prueba creados")
        else:
            print(f"✅ Hay {slots} slots disponibles")
        
        # 5. Buscar un servicio de pago para configurar
        services = Service.query.filter_by(is_active=True).all()
        paid_services = [s for s in services if s.base_price > 0]
        
        if not paid_services:
            print("❌ No hay servicios de pago disponibles.")
            return False
        
        # Seleccionar el primer servicio de pago que no tenga appointment_type_id
        test_service = None
        for service in paid_services:
            if not service.appointment_type_id:
                test_service = service
                break
        
        if not test_service:
            # Si todos tienen appointment_type_id, usar el primero
            test_service = paid_services[0]
            print(f"⚠️  Todos los servicios ya tienen appointment_type_id. Usando: {test_service.name}")
        else:
            print(f"✅ Servicio seleccionado: {test_service.name} (ID: {test_service.id})")
        
        # 6. Configurar el servicio con appointment_type_id y abono
        test_service.appointment_type_id = appointment_type.id
        test_service.requires_payment_before_appointment = True
        # Configurar abono del 50% como ejemplo
        test_service.deposit_percentage = 0.5  # 50% de abono
        
        db.session.commit()
        
        print()
        print("=" * 60)
        print("✅ CONFIGURACIÓN COMPLETADA")
        print("=" * 60)
        print()
        print(f"📋 Servicio configurado: {test_service.name}")
        print(f"   - ID: {test_service.id}")
        print(f"   - Precio base: ${test_service.base_price}")
        print(f"   - Tipo de cita: {appointment_type.name}")
        print(f"   - Abono: {test_service.deposit_percentage * 100}% del precio final")
        print()
        print(f"📅 Slots disponibles: {AppointmentSlot.query.filter(AppointmentSlot.appointment_type_id == appointment_type.id, AppointmentSlot.start_datetime >= datetime.utcnow(), AppointmentSlot.is_available == True).count()}")
        print()
        print("🔗 Para probar:")
        print(f"   1. Inicia sesión en la aplicación")
        print(f"   2. Ve a /services")
        print(f"   3. Busca el servicio: {test_service.name}")
        print(f"   4. Haz clic en 'Solicitar Cita'")
        print()
        
        return True

if __name__ == '__main__':
    try:
        if setup_test_service():
            print("✅ Configuración exitosa. Puedes probar el sistema ahora.")
            sys.exit(0)
        else:
            print("❌ La configuración falló. Revisa los errores arriba.")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
