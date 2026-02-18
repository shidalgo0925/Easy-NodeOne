#!/usr/bin/env python3
"""
Script para analizar el flujo completo de "Talleres especializados"
"""
import sys
import os
from datetime import datetime, timezone, timedelta

# Agregar el directorio backend al path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from app import app, db, Service, AppointmentType, AppointmentSlot, Advisor

def analyze_talleres_flow():
    """Analiza el flujo completo del servicio Talleres especializados"""
    with app.app_context():
        print("\n" + "="*80)
        print("🔍 ANÁLISIS COMPLETO DEL FLUJO: Talleres especializados")
        print("="*80 + "\n")
        
        # 1. Buscar el servicio
        service = Service.query.filter_by(name='Talleres especializados').first()
        if not service:
            print("❌ ERROR: No se encontró el servicio 'Talleres especializados'")
            return
        
        print("✅ 1. SERVICIO ENCONTRADO:")
        print(f"   ID: {service.id}")
        print(f"   Nombre: {service.name}")
        print(f"   Activo: {service.is_active}")
        print(f"   Appointment Type ID: {service.appointment_type_id}")
        print()
        
        # 2. Verificar el tipo de cita asociado
        if not service.appointment_type_id:
            print("❌ ERROR: El servicio NO tiene appointment_type_id asociado")
            print("   Esto significa que NO se puede solicitar cita desde services.html")
            return
        
        appointment_type = AppointmentType.query.get(service.appointment_type_id)
        if not appointment_type:
            print(f"❌ ERROR: El appointment_type_id {service.appointment_type_id} NO EXISTE")
            return
        
        print("✅ 2. TIPO DE CITA ASOCIADO:")
        print(f"   ID: {appointment_type.id}")
        print(f"   Nombre: {appointment_type.name}")
        print(f"   Activo: {appointment_type.is_active}")
        print()
        
        # 3. Verificar slots disponibles para este tipo de cita
        now = datetime.now(timezone.utc)
        future_date = now + timedelta(days=30)
        
        available_slots = AppointmentSlot.query.filter(
            AppointmentSlot.appointment_type_id == appointment_type.id,
            AppointmentSlot.is_available == True,
            AppointmentSlot.start_datetime >= now,
            AppointmentSlot.start_datetime <= future_date
        ).order_by(AppointmentSlot.start_datetime.asc()).all()
        
        print(f"✅ 3. SLOTS DISPONIBLES (próximos 30 días):")
        print(f"   Total: {len(available_slots)} slots")
        print()
        
        if available_slots:
            print("   Próximos 10 slots:")
            for i, slot in enumerate(available_slots[:10], 1):
                advisor_name = "Sin asesor"
                if slot.advisor and slot.advisor.user:
                    advisor_name = f"{slot.advisor.user.first_name} {slot.advisor.user.last_name}"
                
                remaining = slot.remaining_seats()
                print(f"      {i}. {slot.start_datetime.strftime('%Y-%m-%d %H:%M')} - {slot.end_datetime.strftime('%H:%M')}")
                print(f"         Cupos: {remaining}/{slot.capacity} | Asesor: {advisor_name}")
        else:
            print("   ⚠️  NO HAY SLOTS DISPONIBLES")
            print()
            print("   Verificando slots totales (incluyendo no disponibles):")
            all_slots = AppointmentSlot.query.filter(
                AppointmentSlot.appointment_type_id == appointment_type.id
            ).count()
            print(f"   Total slots registrados: {all_slots}")
            
            if all_slots == 0:
                print("\n   💡 PROBLEMA IDENTIFICADO:")
                print("      No hay slots creados para este tipo de cita.")
                print("      Necesitas crear slots desde el panel administrativo.")
        
        # 4. Verificar asesores asignados
        print("\n✅ 4. ASESORES ASIGNADOS AL TIPO DE CITA:")
        advisors_assigned = []
        for assignment in appointment_type.advisor_assignments:
            if assignment.is_active and assignment.advisor.is_active:
                advisor = assignment.advisor
                advisors_assigned.append(advisor)
                print(f"   - {advisor.user.first_name} {advisor.user.last_name} (ID: {advisor.id})")
        
        if not advisors_assigned:
            print("   ⚠️  NO HAY ASESORES ASIGNADOS")
            print("   Esto puede causar que no se muestren slots en el calendario")
        
        # 5. Verificar si el servicio aparece en services.html
        print("\n✅ 5. VERIFICACIÓN DE VISIBILIDAD EN services.html:")
        print(f"   El servicio tiene appointment_type_id: {service.appointment_type_id is not None}")
        print(f"   El servicio está activo: {service.is_active}")
        
        # Verificar pricing
        pricing = service.pricing_for_membership('pro')  # Asumiendo membresía PRO
        print(f"   Precio base: ${service.base_price}")
        print(f"   Precio final (PRO): ${pricing['final_price']}")
        print(f"   Es gratuito: {pricing['final_price'] == 0}")
        
        if pricing['final_price'] == 0:
            print("   ⚠️  El servicio es GRATUITO")
            print("   En services.html, el botón 'Solicitar Cita' NO se muestra para servicios gratuitos")
        else:
            print("   ✅ El servicio NO es gratuito, el botón debería aparecer")
        
        # 6. Resumen y diagnóstico
        print("\n" + "="*80)
        print("📊 RESUMEN Y DIAGNÓSTICO:")
        print("="*80)
        
        issues = []
        if not service.appointment_type_id:
            issues.append("❌ El servicio no tiene appointment_type_id")
        elif not appointment_type:
            issues.append(f"❌ El appointment_type_id {service.appointment_type_id} no existe")
        elif not appointment_type.is_active:
            issues.append(f"❌ El tipo de cita {appointment_type.name} está INACTIVO")
        
        if not advisors_assigned:
            issues.append("❌ No hay asesores asignados al tipo de cita")
        
        if not available_slots:
            issues.append("❌ No hay slots disponibles (esto es el problema principal)")
        
        if pricing['final_price'] == 0:
            issues.append("⚠️  El servicio es gratuito (el botón no aparece en services.html)")
        
        if issues:
            print("\n   PROBLEMAS ENCONTRADOS:")
            for issue in issues:
                print(f"   {issue}")
        else:
            print("\n   ✅ Todo parece estar bien configurado")
            print("   Si aún no ves los slots, el problema puede estar en:")
            print("   1. La API /api/services/<service_id>/calendar")
            print("   2. El formato de datos que devuelve")
            print("   3. El JavaScript del calendario en request_appointment.html")
        
        print()

if __name__ == '__main__':
    analyze_talleres_flow()
