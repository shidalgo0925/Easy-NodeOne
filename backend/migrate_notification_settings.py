#!/usr/bin/env python3
"""
Script de migración para inicializar configuraciones de notificaciones
Crea todas las configuraciones con valor por defecto (habilitadas)
"""

import sys
import os

# Agregar el directorio backend al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, NotificationSettings
from datetime import datetime

# Definición de todas las notificaciones del sistema
NOTIFICATION_TYPES = [
    {
        'notification_type': 'welcome',
        'name': 'Email de Bienvenida',
        'description': 'Se envía cuando un nuevo usuario se registra en el sistema',
        'category': 'system',
        'enabled': True
    },
    {
        'notification_type': 'membership_payment',
        'name': 'Confirmación de Pago de Membresía',
        'description': 'Se envía cuando se confirma un pago de membresía',
        'category': 'membership',
        'enabled': True
    },
    {
        'notification_type': 'membership_expiring',
        'name': 'Membresía por Expirar',
        'description': 'Se envía cuando una membresía está por expirar (30, 15, 7 y 1 día antes)',
        'category': 'membership',
        'enabled': True
    },
    {
        'notification_type': 'membership_expired',
        'name': 'Membresía Expirada',
        'description': 'Se envía cuando una membresía ha expirado',
        'category': 'membership',
        'enabled': True
    },
    {
        'notification_type': 'membership_renewed',
        'name': 'Membresía Renovada',
        'description': 'Se envía cuando una membresía es renovada exitosamente',
        'category': 'membership',
        'enabled': True
    },
    {
        'notification_type': 'event_registration',
        'name': 'Notificación de Registro a Evento (Responsables)',
        'description': 'Se envía a moderadores, administradores y expositores cuando alguien se registra a un evento',
        'category': 'event',
        'enabled': True
    },
    {
        'notification_type': 'event_registration_user',
        'name': 'Confirmación de Registro a Evento (Usuario)',
        'description': 'Se envía al usuario cuando se registra a un evento',
        'category': 'event',
        'enabled': True
    },
    {
        'notification_type': 'event_cancellation',
        'name': 'Notificación de Cancelación (Responsables)',
        'description': 'Se envía a responsables cuando alguien cancela su registro a un evento',
        'category': 'event',
        'enabled': True
    },
    {
        'notification_type': 'event_cancellation_user',
        'name': 'Cancelación de Registro (Usuario)',
        'description': 'Se envía al usuario cuando cancela su registro a un evento',
        'category': 'event',
        'enabled': True
    },
    {
        'notification_type': 'event_confirmation',
        'name': 'Confirmación de Registro (Responsables)',
        'description': 'Se envía a responsables cuando se confirma un registro a evento',
        'category': 'event',
        'enabled': True
    },
    {
        'notification_type': 'event_update',
        'name': 'Actualización de Evento',
        'description': 'Se envía a usuarios registrados cuando se actualiza un evento',
        'category': 'event',
        'enabled': True
    },
    {
        'notification_type': 'appointment_confirmation',
        'name': 'Confirmación de Cita',
        'description': 'Se envía cuando se confirma una cita con un asesor',
        'category': 'appointment',
        'enabled': True
    },
    {
        'notification_type': 'appointment_reminder',
        'name': 'Recordatorio de Cita',
        'description': 'Se envía como recordatorio antes de una cita (24 y 48 horas antes)',
        'category': 'appointment',
        'enabled': True
    }
]


def initialize_notification_settings():
    """Inicializar todas las configuraciones de notificaciones"""
    with app.app_context():
        try:
            created_count = 0
            updated_count = 0
            
            for notification_data in NOTIFICATION_TYPES:
                # Verificar si ya existe
                existing = NotificationSettings.query.filter_by(
                    notification_type=notification_data['notification_type']
                ).first()
                
                if existing:
                    # Actualizar si es necesario
                    existing.name = notification_data['name']
                    existing.description = notification_data['description']
                    existing.category = notification_data['category']
                    updated_count += 1
                    print(f"✓ Actualizada: {notification_data['name']}")
                else:
                    # Crear nueva configuración
                    setting = NotificationSettings(
                        notification_type=notification_data['notification_type'],
                        name=notification_data['name'],
                        description=notification_data['description'],
                        category=notification_data['category'],
                        enabled=notification_data['enabled']
                    )
                    db.session.add(setting)
                    created_count += 1
                    print(f"✓ Creada: {notification_data['name']}")
            
            db.session.commit()
            
            print(f"\n{'='*60}")
            print(f"✅ Migración completada:")
            print(f"   - Configuraciones creadas: {created_count}")
            print(f"   - Configuraciones actualizadas: {updated_count}")
            print(f"   - Total de tipos de notificación: {len(NOTIFICATION_TYPES)}")
            print(f"{'='*60}\n")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error en la migración: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == '__main__':
    print(f"\n{'='*60}")
    print("Inicializando configuraciones de notificaciones...")
    print(f"{'='*60}\n")
    
    success = initialize_notification_settings()
    
    if success:
        print("✅ Migración exitosa. Las notificaciones están configuradas.")
        print("   Puedes gestionarlas desde: /admin/notifications")
    else:
        print("❌ Error en la migración. Revisa los logs.")
        sys.exit(1)









