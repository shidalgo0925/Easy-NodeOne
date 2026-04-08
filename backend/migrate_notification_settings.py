#!/usr/bin/env python3
"""
Script de migración para inicializar configuraciones de notificaciones
Crea todas las configuraciones con valor por defecto (habilitadas)

Este script:
1. Verifica que el modelo NotificationSettings existe en la BD
2. Crea todas las configuraciones de notificaciones si no existen
3. Actualiza las existentes con información actualizada
4. Valida que todos los tipos estén correctamente configurados
5. Verifica la integridad después de la migración

Uso:
    python backend/migrate_notification_settings.py
"""

import sys
import os

# Agregar el directorio backend al path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, NotificationSettings
from datetime import datetime

# ============================================================================
# DEFINICIÓN DE TODAS LAS NOTIFICACIONES DEL SISTEMA
# ============================================================================
# IMPORTANTE: Estos tipos deben coincidir exactamente con los usados en
# NotificationEngine. Si agregas un nuevo tipo, debes:
# 1. Agregarlo aquí
# 2. Implementar el método correspondiente en NotificationEngine
# 3. Agregar la verificación en NotificationEngine._is_notification_enabled()
# ============================================================================

NOTIFICATION_TYPES = [
    # ========================================================================
    # SISTEMA - Notificaciones generales del sistema
    # ========================================================================
    {
        'notification_type': 'welcome',
        'name': 'Email de Bienvenida',
        'description': 'Se envía cuando un nuevo usuario se registra en el sistema',
        'category': 'system',
        'enabled': True  # Por defecto habilitada
    },
    # ========================================================================
    # MEMBRESÍAS - Notificaciones relacionadas con membresías y pagos
    # ========================================================================
    {
        'notification_type': 'membership_payment',
        'name': 'Confirmación de Pago de Membresía',
        'description': 'Se envía cuando se confirma un pago de membresía exitosamente',
        'category': 'membership',
        'enabled': True
    },
    {
        'notification_type': 'membership_expiring',
        'name': 'Membresía por Expirar',
        'description': 'Se envía cuando una membresía está por expirar (30, 15, 7 y 1 día antes). Se ejecuta automáticamente por notification_scheduler.py',
        'category': 'membership',
        'enabled': True
    },
    {
        'notification_type': 'membership_expired',
        'name': 'Membresía Expirada',
        'description': 'Se envía cuando una membresía ha expirado. Se ejecuta automáticamente por notification_scheduler.py',
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
    # ========================================================================
    # EVENTOS - Notificaciones relacionadas con eventos
    # ========================================================================
    {
        'notification_type': 'event_registration',
        'name': 'Notificación de Registro a Evento (Responsables)',
        'description': 'Se envía a moderadores, administradores y expositores cuando alguien se registra a un evento. Llamado desde NotificationEngine.notify_event_registration()',
        'category': 'event',
        'enabled': True
    },
    {
        'notification_type': 'event_registration_user',
        'name': 'Confirmación de Registro a Evento (Usuario)',
        'description': 'Se envía al usuario cuando se registra a un evento. Llamado desde NotificationEngine.notify_event_registration_to_user()',
        'category': 'event',
        'enabled': True
    },
    {
        'notification_type': 'event_cancellation',
        'name': 'Notificación de Cancelación (Responsables)',
        'description': 'Se envía a responsables cuando alguien cancela su registro a un evento. Llamado desde NotificationEngine.notify_event_cancellation()',
        'category': 'event',
        'enabled': True
    },
    {
        'notification_type': 'event_cancellation_user',
        'name': 'Cancelación de Registro (Usuario)',
        'description': 'Se envía al usuario cuando cancela su registro a un evento. Llamado desde NotificationEngine.notify_event_cancellation_to_user()',
        'category': 'event',
        'enabled': True
    },
    {
        'notification_type': 'event_confirmation',
        'name': 'Confirmación de Registro (Responsables)',
        'description': 'Se envía a responsables cuando se confirma un registro a evento. Llamado desde NotificationEngine.notify_event_confirmation()',
        'category': 'event',
        'enabled': True
    },
    {
        'notification_type': 'event_update',
        'name': 'Actualización de Evento',
        'description': 'Se envía a usuarios registrados cuando se actualiza un evento. Llamado desde NotificationEngine.notify_event_update()',
        'category': 'event',
        'enabled': True
    },
    # ========================================================================
    # CITAS - Notificaciones relacionadas con citas y asesorías
    # ========================================================================
    {
        'notification_type': 'appointment_confirmation',
        'name': 'Confirmación de Cita',
        'description': 'Se envía cuando se confirma una cita con un asesor. Llamado desde NotificationEngine.notify_appointment_confirmation()',
        'category': 'appointment',
        'enabled': True
    },
    {
        'notification_type': 'appointment_reminder',
        'name': 'Recordatorio de Cita',
        'description': 'Se envía como recordatorio antes de una cita (24h y 1h antes). Se ejecuta automáticamente por notification_scheduler.py',
        'category': 'appointment',
        'enabled': True
    },
    {
        'notification_type': 'appointment_cancellation',
        'name': 'Cancelación de Cita (miembro)',
        'description': 'Se envía al miembro cuando se cancela una cita. Llamado desde NotificationEngine.notify_appointment_cancelled()',
        'category': 'appointment',
        'enabled': True
    }
]


# ============================================================================
# FUNCIONES DE VALIDACIÓN Y MIGRACIÓN
# ============================================================================

def verify_model_exists():
    """
    Verificar que el modelo NotificationSettings existe en la base de datos
    Retorna True si existe, False si no
    """
    try:
        # Intentar hacer una consulta simple para verificar que la tabla existe
        count = NotificationSettings.query.count()
        print("✅ Modelo NotificationSettings verificado en la base de datos")
        return True
    except Exception as e:
        print(f"❌ Error verificando modelo NotificationSettings: {e}")
        print("   Asegúrate de que la tabla existe en la base de datos")
        return False


def validate_notification_types():
    """
    Validar que todos los tipos de notificación estén correctamente definidos
    Retorna (True, []) si todo está bien, (False, [errores]) si hay problemas
    """
    errors = []
    
    # Verificar que todos tienen los campos requeridos
    required_fields = ['notification_type', 'name', 'category', 'enabled']
    
    for idx, notif_data in enumerate(NOTIFICATION_TYPES, 1):
        # Verificar campos requeridos
        for field in required_fields:
            if field not in notif_data:
                errors.append(f"Notificación #{idx}: Falta el campo '{field}'")
        
        # Verificar que notification_type no esté vacío
        if not notif_data.get('notification_type'):
            errors.append(f"Notificación #{idx}: notification_type no puede estar vacío")
        
        # Verificar que category sea válida
        valid_categories = ['system', 'membership', 'event', 'appointment']
        if notif_data.get('category') not in valid_categories:
            errors.append(f"Notificación #{idx}: Categoría '{notif_data.get('category')}' no es válida. Debe ser una de: {valid_categories}")
    
    # Verificar que no haya duplicados
    notification_types = [n['notification_type'] for n in NOTIFICATION_TYPES]
    duplicates = [nt for nt in notification_types if notification_types.count(nt) > 1]
    if duplicates:
        errors.append(f"Tipos duplicados encontrados: {set(duplicates)}")
    
    if errors:
        return False, errors
    return True, []


def initialize_notification_settings():
    """
    Inicializar todas las configuraciones de notificaciones
    
    Proceso:
    1. Verifica que el modelo existe
    2. Valida los tipos de notificación
    3. Para cada tipo:
       - Si existe: actualiza nombre, descripción y categoría (preserva enabled)
       - Si no existe: crea nueva configuración con enabled=True por defecto
    4. Hace commit de todos los cambios
    5. Verifica la integridad después de la migración
    
    Retorna True si la migración fue exitosa, False si hubo errores
    """
    with app.app_context():
        try:
            # Paso 1: Verificar que el modelo existe
            print("🔍 Verificando modelo NotificationSettings...")
            if not verify_model_exists():
                return False
            
            # Paso 2: Validar tipos de notificación
            print("\n🔍 Validando tipos de notificación...")
            is_valid, errors = validate_notification_types()
            if not is_valid:
                print("❌ Errores de validación encontrados:")
                for error in errors:
                    print(f"   - {error}")
                return False
            print(f"✅ Validación exitosa: {len(NOTIFICATION_TYPES)} tipos de notificación válidos")
            
            # Paso 3: Inicializar/actualizar configuraciones
            print(f"\n📝 Inicializando configuraciones...")
            created_count = 0
            updated_count = 0
            skipped_count = 0
            
            for notification_data in NOTIFICATION_TYPES:
                notification_type = notification_data['notification_type']
                
                # Buscar si ya existe esta configuración
                existing = NotificationSettings.query.filter_by(
                    notification_type=notification_type
                ).first()
                
                if existing:
                    # Actualizar información (pero preservar el estado enabled actual)
                    # Solo actualizamos si hay cambios en nombre, descripción o categoría
                    needs_update = (
                        existing.name != notification_data['name'] or
                        existing.description != notification_data['description'] or
                        existing.category != notification_data['category']
                    )
                    
                    if needs_update:
                        existing.name = notification_data['name']
                        existing.description = notification_data['description']
                        existing.category = notification_data['category']
                        existing.updated_at = datetime.utcnow()
                        updated_count += 1
                        print(f"   ✓ Actualizada: {notification_data['name']} ({notification_type})")
                    else:
                        skipped_count += 1
                        print(f"   ⊘ Sin cambios: {notification_data['name']} ({notification_type})")
                else:
                    # Crear nueva configuración
                    setting = NotificationSettings(
                        notification_type=notification_type,
                        name=notification_data['name'],
                        description=notification_data['description'],
                        category=notification_data['category'],
                        enabled=notification_data['enabled']  # Por defecto True
                    )
                    db.session.add(setting)
                    created_count += 1
                    print(f"   ✓ Creada: {notification_data['name']} ({notification_type})")
            
            # Paso 4: Commit de todos los cambios
            print(f"\n💾 Guardando cambios en la base de datos...")
            db.session.commit()
            print("✅ Cambios guardados exitosamente")
            
            # Paso 5: Verificar integridad después de la migración
            print(f"\n🔍 Verificando integridad después de la migración...")
            total_in_db = NotificationSettings.query.count()
            
            if total_in_db != len(NOTIFICATION_TYPES):
                print(f"⚠️  Advertencia: Se esperaban {len(NOTIFICATION_TYPES)} configuraciones, pero hay {total_in_db} en la BD")
            
            # Verificar que todos los tipos estén presentes
            missing_types = []
            for notification_data in NOTIFICATION_TYPES:
                exists = NotificationSettings.query.filter_by(
                    notification_type=notification_data['notification_type']
                ).first()
                if not exists:
                    missing_types.append(notification_data['notification_type'])
            
            if missing_types:
                print(f"❌ Tipos faltantes en la BD: {missing_types}")
                return False
            
            # Resumen final
            print(f"\n{'='*70}")
            print(f"✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
            print(f"{'='*70}")
            print(f"   📊 Resumen:")
            print(f"      - Configuraciones creadas: {created_count}")
            print(f"      - Configuraciones actualizadas: {updated_count}")
            print(f"      - Configuraciones sin cambios: {skipped_count}")
            print(f"      - Total en base de datos: {total_in_db}")
            print(f"      - Total de tipos definidos: {len(NOTIFICATION_TYPES)}")
            print(f"\n   📍 Próximos pasos:")
            print(f"      1. Gestiona las notificaciones desde: /admin/notifications")
            print(f"      2. Verifica el estado con: python backend/verify_notifications_system.py")
            print(f"      3. Asegúrate de que el sistema de emails esté configurado")
            print(f"{'='*70}\n")
            
            return True
            
        except Exception as e:
            # Rollback en caso de error
            db.session.rollback()
            print(f"\n❌ Error durante la migración:")
            print(f"   {str(e)}")
            print(f"\n📋 Detalles del error:")
            import traceback
            traceback.print_exc()
            return False


# ============================================================================
# PUNTO DE ENTRADA DEL SCRIPT
# ============================================================================

if __name__ == '__main__':
    print(f"\n{'='*70}")
    print("  🔔 MIGRACIÓN DE CONFIGURACIONES DE NOTIFICACIONES")
    print(f"{'='*70}")
    print(f"\n📅 Fecha: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"📦 Total de tipos de notificación a configurar: {len(NOTIFICATION_TYPES)}\n")
    
    # Ejecutar migración
    success = initialize_notification_settings()
    
    # Resultado final
    if success:
        print("\n✅ MIGRACIÓN EXITOSA")
        print("   Las configuraciones de notificaciones están listas para usar.")
        print("   Puedes gestionarlas desde el panel de administración:")
        print("   → /admin/notifications\n")
        sys.exit(0)
    else:
        print("\n❌ MIGRACIÓN FALLIDA")
        print("   Revisa los errores arriba y corrige los problemas antes de reintentar.")
        print("   Verifica que:")
        print("   1. La base de datos esté accesible")
        print("   2. El modelo NotificationSettings esté correctamente definido")
        print("   3. Tengas permisos de escritura en la base de datos\n")
        sys.exit(1)










