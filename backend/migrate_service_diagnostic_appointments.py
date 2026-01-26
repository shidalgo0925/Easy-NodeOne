#!/usr/bin/env python3
"""
Script de migración para agregar soporte de citas de diagnóstico a servicios.

Este script:
1. Crea el AppointmentType "Cita de Diagnóstico de Servicio" si no existe
2. Marca servicios que requieren cita diagnóstico (todos excepto plan básico)
3. Asigna el AppointmentType a todos los asesores activos
4. Actualiza la base de datos con los nuevos campos
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from app import Service, AppointmentType, AppointmentAdvisor, Advisor

def create_diagnostic_appointment_type():
    """Crear el tipo de cita de diagnóstico si no existe"""
    with app.app_context():
        print("1. Verificando/creando AppointmentType 'Cita de Diagnóstico de Servicio'...")
        
        diagnostic_type = AppointmentType.query.filter_by(
            name="Cita de Diagnóstico de Servicio"
        ).first()
        
        if not diagnostic_type:
            diagnostic_type = AppointmentType(
                name="Cita de Diagnóstico de Servicio",
                description="Cita de diagnóstico requerida antes de acceder al servicio. "
                           "Permite al asesor evaluar las necesidades del cliente y orientar "
                           "el uso adecuado del servicio.",
                service_category="diagnostico",
                duration_minutes=45,  # Duración por defecto: 45 minutos
                is_group_allowed=False,
                max_participants=1,
                base_price=0.0,  # El precio viene del servicio, no de la cita
                currency='USD',
                is_virtual=True,
                requires_confirmation=False,  # Se confirma automáticamente al pagar
                color_tag='#28a745',  # Verde para diferenciarlo
                icon='fa-stethoscope',
                display_order=1,
                is_active=True
            )
            db.session.add(diagnostic_type)
            db.session.commit()
            print(f"   ✓ Creado AppointmentType ID: {diagnostic_type.id}")
        else:
            print(f"   → AppointmentType ya existe (ID: {diagnostic_type.id})")
            # Asegurar que esté activo
            if not diagnostic_type.is_active:
                diagnostic_type.is_active = True
                db.session.commit()
                print(f"   ✓ AppointmentType activado")
        
        return diagnostic_type

def assign_advisors_to_diagnostic_type(diagnostic_type):
    """Asignar todos los asesores activos al tipo de cita de diagnóstico"""
    with app.app_context():
        print("\n2. Asignando asesores al tipo de cita de diagnóstico...")
        
        advisors = Advisor.query.filter_by(is_active=True).all()
        assigned = 0
        skipped = 0
        
        for advisor in advisors:
            # Verificar si ya está asignado
            existing = AppointmentAdvisor.query.filter_by(
                appointment_type_id=diagnostic_type.id,
                advisor_id=advisor.id
            ).first()
            
            if not existing:
                assignment = AppointmentAdvisor(
                    appointment_type_id=diagnostic_type.id,
                    advisor_id=advisor.id,
                    priority=1,
                    is_active=True
                )
                db.session.add(assignment)
                assigned += 1
                print(f"   ✓ Asignado: {advisor.user.email if advisor.user else 'N/A'}")
            else:
                skipped += 1
                # Asegurar que esté activo
                if not existing.is_active:
                    existing.is_active = True
                    db.session.commit()
        
        db.session.commit()
        print(f"\n   → {assigned} asesores asignados, {skipped} ya estaban asignados")
        return assigned

def mark_services_for_diagnostic(diagnostic_type):
    """Marcar servicios que requieren cita diagnóstico (todos excepto plan básico)"""
    with app.app_context():
        print("\n3. Marcando servicios que requieren cita diagnóstico...")
        
        services = Service.query.filter_by(is_active=True).all()
        marked = 0
        unmarked = 0
        already_marked = 0
        
        for service in services:
            # Regla: todos excepto plan básico requieren cita diagnóstico
            if service.membership_type != 'basic':
                if not service.requires_diagnostic_appointment:
                    service.requires_diagnostic_appointment = True
                    service.diagnostic_appointment_type_id = diagnostic_type.id
                    marked += 1
                    print(f"   ✓ Marcado: {service.name} ({service.membership_type})")
                else:
                    already_marked += 1
                    # Asegurar que tenga el tipo correcto asignado
                    if service.diagnostic_appointment_type_id != diagnostic_type.id:
                        service.diagnostic_appointment_type_id = diagnostic_type.id
                        print(f"   → Actualizado tipo: {service.name}")
            else:
                # Plan básico: asegurar que NO requiera cita
                if service.requires_diagnostic_appointment:
                    service.requires_diagnostic_appointment = False
                    service.diagnostic_appointment_type_id = None
                    unmarked += 1
                    print(f"   → Desmarcado (básico): {service.name}")
        
        db.session.commit()
        print(f"\n   → {marked} servicios marcados, {already_marked} ya estaban marcados, {unmarked} desmarcados (básico)")
        return marked

def verify_migration():
    """Verificar que la migración se aplicó correctamente"""
    with app.app_context():
        print("\n4. Verificando migración...")
        
        # Verificar AppointmentType
        diagnostic_type = AppointmentType.query.filter_by(
            name="Cita de Diagnóstico de Servicio"
        ).first()
        
        if not diagnostic_type:
            print("   ✗ ERROR: AppointmentType no encontrado")
            return False
        else:
            print(f"   ✓ AppointmentType existe (ID: {diagnostic_type.id})")
        
        # Verificar asignaciones de asesores
        advisor_count = AppointmentAdvisor.query.filter_by(
            appointment_type_id=diagnostic_type.id,
            is_active=True
        ).count()
        print(f"   ✓ {advisor_count} asesores asignados al tipo de cita")
        
        # Verificar servicios
        services_with_diagnostic = Service.query.filter_by(
            requires_diagnostic_appointment=True,
            is_active=True
        ).count()
        services_basic = Service.query.filter_by(
            membership_type='basic',
            is_active=True
        ).count()
        
        print(f"   ✓ {services_with_diagnostic} servicios requieren cita diagnóstico")
        print(f"   ✓ {services_basic} servicios del plan básico (no requieren cita)")
        
        # Verificar que servicios no-básicos tienen el campo marcado
        non_basic_services = Service.query.filter(
            Service.membership_type != 'basic',
            Service.is_active == True
        ).all()
        
        issues = []
        for service in non_basic_services:
            if not service.requires_diagnostic_appointment:
                issues.append(f"   ⚠️  {service.name} ({service.membership_type}) no está marcado")
        
        if issues:
            print(f"\n   ⚠️  ADVERTENCIAS:")
            for issue in issues[:5]:
                print(issue)
            if len(issues) > 5:
                print(f"   ... y {len(issues) - 5} más")
        else:
            print(f"   ✓ Todos los servicios no-básicos están correctamente marcados")
        
        return True

def main():
    print("=" * 80)
    print("MIGRACIÓN: Citas de Diagnóstico para Servicios")
    print("=" * 80)
    print()
    print("Este script:")
    print("  1. Crea el AppointmentType 'Cita de Diagnóstico de Servicio'")
    print("  2. Asigna todos los asesores activos a este tipo de cita")
    print("  3. Marca servicios que requieren cita (todos excepto plan básico)")
    print("  4. Verifica que la migración se aplicó correctamente")
    print()
    
    try:
        # Paso 1: Crear AppointmentType
        diagnostic_type = create_diagnostic_appointment_type()
        
        # Paso 2: Asignar asesores
        assign_advisors_to_diagnostic_type(diagnostic_type)
        
        # Paso 3: Marcar servicios
        marked = mark_services_for_diagnostic(diagnostic_type)
        
        # Paso 4: Verificar
        if verify_migration():
            print()
            print("=" * 80)
            print("✅ Migración completada exitosamente")
            print("=" * 80)
            print()
            print("PRÓXIMOS PASOS:")
            print("  1. Los asesores deben crear slots disponibles para citas de diagnóstico")
            print("  2. Los usuarios verán 'Ver espacios disponibles' en servicios que requieren diagnóstico")
            print("  3. Al seleccionar un slot y pagar, se creará automáticamente la cita confirmada")
            print("  4. Se enviarán emails de confirmación a cliente y asesor")
            print()
        else:
            print()
            print("=" * 80)
            print("⚠️  Migración completada con advertencias")
            print("=" * 80)
            print("Revisa los mensajes anteriores para más detalles.")
            print()
    
    except Exception as e:
        print()
        print("=" * 80)
        print("✗ ERROR durante la migración")
        print("=" * 80)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
