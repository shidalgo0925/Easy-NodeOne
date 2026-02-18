#!/usr/bin/env python3
"""
Script para probar la API del calendario directamente
"""
import sys
import os
from datetime import datetime, timezone, timedelta

# Agregar el directorio backend al path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from app import app, db, Service, AppointmentType, AppointmentSlot, AppointmentAdvisor, Advisor

def test_api_logic():
    """Prueba la lógica de la API del calendario"""
    with app.app_context():
        print("\n" + "="*80)
        print("🧪 PRUEBA DE LA LÓGICA DE LA API /api/services/<service_id>/calendar")
        print("="*80 + "\n")
        
        # 1. Obtener servicio
        service_id = 24  # Talleres especializados
        service = Service.query.get(service_id)
        if not service:
            print(f"❌ Servicio {service_id} no encontrado")
            return
        
        print(f"✅ Servicio: {service.name} (ID: {service.id})")
        print(f"   Appointment Type ID: {service.appointment_type_id}")
        
        if not service.appointment_type_id:
            print("❌ El servicio no tiene appointment_type_id")
            return
        
        appointment_type_id = service.appointment_type_id
        appointment_type = AppointmentType.query.get(appointment_type_id)
        print(f"✅ Tipo de cita: {appointment_type.name} (ID: {appointment_type.id})")
        print()
        
        # 2. Obtener asesores asignados (igual que en la API)
        print("🔍 Buscando asesores asignados...")
        advisor_assignments = AppointmentAdvisor.query.filter_by(
            appointment_type_id=appointment_type_id,
            is_active=True
        ).join(Advisor).filter(Advisor.is_active == True).all()
        
        print(f"   Encontrados {len(advisor_assignments)} asesores asignados")
        for aa in advisor_assignments:
            advisor = aa.advisor
            if advisor and advisor.user:
                print(f"   - {advisor.user.first_name} {advisor.user.last_name} (ID: {advisor.id})")
        
        if not advisor_assignments:
            print("   ⚠️  NO HAY ASESORES ASIGNADOS")
            print("   Esto causaría que la API devuelva events: []")
            return
        
        advisor_ids = [aa.advisor_id for aa in advisor_assignments]
        print(f"   Advisor IDs: {advisor_ids}")
        print()
        
        # 3. Verificar slots disponibles
        now = datetime.now(timezone.utc)
        future_date = now + timedelta(days=30)
        
        print(f"🔍 Buscando slots disponibles entre {now.strftime('%Y-%m-%d')} y {future_date.strftime('%Y-%m-%d')}...")
        
        from sqlalchemy.orm import joinedload
        slots = AppointmentSlot.query.options(
            joinedload(AppointmentSlot.advisor).joinedload(Advisor.user)
        ).filter(
            AppointmentSlot.appointment_type_id == appointment_type_id,
            AppointmentSlot.advisor_id.in_(advisor_ids),
            AppointmentSlot.start_datetime >= now,
            AppointmentSlot.start_datetime < future_date,
            AppointmentSlot.is_available == True
        ).order_by(AppointmentSlot.start_datetime.asc()).all()
        
        print(f"   Encontrados {len(slots)} slots disponibles")
        print()
        
        # 4. Formatear eventos como lo hace la API
        print("🔍 Formateando eventos para FullCalendar...")
        calendar_events = []
        for slot in slots[:5]:  # Solo primeros 5 para ejemplo
            try:
                advisor_name = 'Asesor'
                if slot.advisor:
                    if slot.advisor.user:
                        advisor_name = f"{slot.advisor.user.first_name} {slot.advisor.user.last_name}"
                    else:
                        advisor_name = f"Asesor #{slot.advisor.id}"
                
                if not slot.start_datetime or not slot.end_datetime:
                    print(f"   ⚠️  Slot {slot.id} no tiene fechas válidas")
                    continue
                
                remaining_seats = slot.remaining_seats() if hasattr(slot, 'remaining_seats') else (slot.capacity if slot.capacity else 1)
                
                event = {
                    'id': f'slot_{slot.id}',
                    'title': f'Disponible - {advisor_name}',
                    'start': slot.start_datetime.isoformat(),
                    'end': slot.end_datetime.isoformat(),
                    'backgroundColor': '#28a745',
                    'borderColor': '#28a745',
                    'textColor': '#fff',
                    'extendedProps': {
                        'type': 'slot',
                        'slot_id': slot.id,
                        'advisor_id': slot.advisor_id,
                        'advisor_name': advisor_name,
                        'service_id': service_id,
                        'service_name': service.name,
                        'remaining_seats': remaining_seats,
                        'capacity': slot.capacity if slot.capacity else 1,
                        'available': True
                    }
                }
                calendar_events.append(event)
                print(f"   ✅ Evento creado: {event['title']} - {event['start']}")
            except Exception as e:
                print(f"   ❌ Error procesando slot {slot.id}: {e}")
                import traceback
                traceback.print_exc()
        
        print()
        print(f"📊 Total eventos formateados: {len(calendar_events)} de {len(slots)} slots")
        print()
        
        # 5. Simular respuesta de la API
        api_response = {
            'success': True,
            'service': {'id': service.id, 'name': service.name},
            'events': calendar_events,
            'total_slots': len(slots)
        }
        
        print("📤 RESPUESTA SIMULADA DE LA API:")
        print(f"   success: {api_response['success']}")
        print(f"   total_slots: {api_response['total_slots']}")
        print(f"   events: {len(api_response['events'])} eventos")
        print()
        
        if len(api_response['events']) == 0:
            print("❌ PROBLEMA: La API devolvería 0 eventos aunque hay slots disponibles")
            print("   Posibles causas:")
            print("   1. Los slots no tienen advisor_id en la lista de advisor_ids")
            print("   2. Los slots están fuera del rango de fechas")
            print("   3. Los slots tienen is_available = False")
            print("   4. Error al formatear los eventos")
        else:
            print("✅ La API debería devolver eventos correctamente")
            print("   Si no se ven en el calendario, el problema está en el frontend")

if __name__ == '__main__':
    test_api_logic()
