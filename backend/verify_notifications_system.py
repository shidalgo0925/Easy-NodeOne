#!/usr/bin/env python3
"""
Script de verificación del sistema de notificaciones
Verifica el estado, configuración y funcionamiento del sistema
"""

import sys
import os
from datetime import datetime, timedelta

# Agregar el directorio backend al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from app import Notification, NotificationSettings, User, EmailLog

def print_header(title):
    """Imprimir encabezado formateado"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def print_section(title):
    """Imprimir sección"""
    print(f"\n{'─'*70}")
    print(f"  {title}")
    print(f"{'─'*70}")

def verify_notification_settings():
    """Verificar configuraciones de notificaciones"""
    print_section("📋 CONFIGURACIÓN DE NOTIFICACIONES")
    
    settings = NotificationSettings.query.order_by(
        NotificationSettings.category,
        NotificationSettings.name
    ).all()
    
    if not settings:
        print("⚠️  No se encontraron configuraciones de notificaciones")
        print("   Ejecuta: python backend/migrate_notification_settings.py")
        return
    
    # Agrupar por categoría
    by_category = {}
    enabled_count = 0
    disabled_count = 0
    
    for setting in settings:
        category = setting.category or 'sin_categoria'
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(setting)
        
        if setting.enabled:
            enabled_count += 1
        else:
            disabled_count += 1
    
    print(f"✅ Total de configuraciones: {len(settings)}")
    print(f"   Habilitadas: {enabled_count} | Deshabilitadas: {disabled_count}\n")
    
    # Mostrar por categoría
    for category, category_settings in sorted(by_category.items()):
        print(f"  📁 {category.upper().replace('_', ' ')}")
        for setting in category_settings:
            status = "✅ HABILITADA" if setting.enabled else "❌ DESHABILITADA"
            print(f"     {status} - {setting.name} ({setting.notification_type})")
        print()

def verify_notifications_status():
    """Verificar estado de las notificaciones"""
    print_section("📊 ESTADO DE NOTIFICACIONES")
    
    # Totales
    total = Notification.query.count()
    unread = Notification.query.filter_by(is_read=False).count()
    read = Notification.query.filter_by(is_read=True).count()
    sent = Notification.query.filter_by(email_sent=True).count()
    not_sent = Notification.query.filter_by(email_sent=False).count()
    
    print(f"📈 Estadísticas Generales:")
    print(f"   Total de notificaciones: {total}")
    print(f"   No leídas: {unread}")
    print(f"   Leídas: {read}")
    print(f"   Emails enviados: {sent}")
    print(f"   Emails no enviados: {not_sent}")
    
    # Notificaciones recientes (últimas 24 horas)
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent = Notification.query.filter(
        Notification.created_at >= yesterday
    ).count()
    
    print(f"\n📅 Últimas 24 horas:")
    print(f"   Notificaciones creadas: {recent}")
    
    # Notificaciones por tipo
    print(f"\n📋 Por Tipo de Notificación:")
    from sqlalchemy import func
    by_type = db.session.query(
        Notification.notification_type,
        func.count(Notification.id).label('count')
    ).group_by(Notification.notification_type).all()
    
    for notif_type, count in sorted(by_type, key=lambda x: x[1], reverse=True):
        print(f"   {notif_type}: {count}")
    
    # Notificaciones pendientes de envío
    if not_sent > 0:
        print(f"\n⚠️  NOTIFICACIONES PENDIENTES DE ENVÍO:")
        pending = Notification.query.filter_by(email_sent=False).limit(10).all()
        for notif in pending:
            user = User.query.get(notif.user_id)
            user_email = user.email if user else "Usuario no encontrado"
            print(f"   - ID {notif.id}: {notif.notification_type} para {user_email}")
            print(f"     Creada: {notif.created_at}")
            print(f"     Título: {notif.title}")

def verify_email_logs():
    """Verificar logs de emails"""
    print_section("📧 LOGS DE EMAILS")
    
    if not hasattr(db.Model, 'metadata') or 'email_log' not in db.Model.metadata.tables:
        print("⚠️  Tabla EmailLog no encontrada en la base de datos")
        return
    
    try:
        # Totales
        total_emails = EmailLog.query.count()
        sent_emails = EmailLog.query.filter_by(status='sent').count()
        failed_emails = EmailLog.query.filter_by(status='failed').count()
        pending_emails = EmailLog.query.filter_by(status='pending').count()
        
        print(f"📈 Estadísticas de Emails:")
        print(f"   Total de emails registrados: {total_emails}")
        print(f"   Enviados exitosamente: {sent_emails}")
        print(f"   Fallidos: {failed_emails}")
        print(f"   Pendientes: {pending_emails}")
        
        # Emails recientes (últimas 24 horas)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_sent = EmailLog.query.filter(
            EmailLog.status == 'sent',
            EmailLog.sent_at >= yesterday
        ).count()
        
        recent_failed = EmailLog.query.filter(
            EmailLog.status == 'failed',
            EmailLog.sent_at >= yesterday
        ).count()
        
        print(f"\n📅 Últimas 24 horas:")
        print(f"   Emails enviados: {recent_sent}")
        print(f"   Emails fallidos: {recent_failed}")
        
        # Errores recientes
        if recent_failed > 0:
            print(f"\n❌ ERRORES RECIENTES:")
            failed = EmailLog.query.filter(
                EmailLog.status == 'failed',
                EmailLog.sent_at >= yesterday
            ).order_by(EmailLog.sent_at.desc()).limit(5).all()
            
            for email_log in failed:
                error_msg = email_log.error_message[:100] if email_log.error_message else "Sin mensaje de error"
                print(f"   - {email_log.recipient_email}: {email_log.email_type}")
                print(f"     Error: {error_msg}")
                print(f"     Fecha: {email_log.sent_at}")
        
    except Exception as e:
        print(f"⚠️  Error al consultar EmailLog: {e}")

def verify_notification_engine():
    """Verificar que el motor de notificaciones funciona correctamente"""
    print_section("🔧 VERIFICACIÓN DEL MOTOR DE NOTIFICACIONES")
    
    from app import NotificationEngine
    
    # Tipos de notificaciones esperados
    expected_types = [
        'welcome',
        'membership_payment',
        'membership_expiring',
        'membership_expired',
        'membership_renewed',
        'event_registration',
        'event_registration_user',
        'event_cancellation',
        'event_cancellation_user',
        'event_confirmation',
        'event_update',
        'appointment_confirmation',
        'appointment_reminder'
    ]
    
    print("🔍 Verificando tipos de notificaciones:")
    missing_types = []
    
    for notif_type in expected_types:
        # Verificar si existe configuración
        setting = NotificationSettings.query.filter_by(
            notification_type=notif_type
        ).first()
        
        if setting:
            status = "✅" if setting.enabled else "⚠️"
            print(f"   {status} {notif_type}: {'Habilitada' if setting.enabled else 'Deshabilitada'}")
        else:
            print(f"   ⚠️  {notif_type}: Sin configuración (se asume habilitada por defecto)")
            missing_types.append(notif_type)
    
    if missing_types:
        print(f"\n⚠️  Tipos sin configuración: {len(missing_types)}")
        print("   Ejecuta: python backend/migrate_notification_settings.py")
    
    # Verificar métodos del NotificationEngine
    print(f"\n🔍 Verificando métodos del NotificationEngine:")
    methods = [
        'notify_welcome',
        'notify_membership_payment',
        'notify_membership_expiring',
        'notify_membership_expired',
        'notify_membership_renewed',
        'notify_event_registration',
        'notify_event_registration_to_user',
        'notify_event_cancellation',
        'notify_event_cancellation_to_user',
        'notify_event_confirmation',
        'notify_event_update',
        'notify_appointment_confirmation',
        'notify_appointment_reminder'
    ]
    
    for method_name in methods:
        if hasattr(NotificationEngine, method_name):
            print(f"   ✅ {method_name}")
        else:
            print(f"   ❌ {method_name}: NO ENCONTRADO")

def verify_integration():
    """Verificar integración con otros sistemas"""
    print_section("🔗 VERIFICACIÓN DE INTEGRACIÓN")
    
    # Verificar EmailService
    try:
        from app import email_service, EMAIL_TEMPLATES_AVAILABLE
        
        if email_service:
            print("✅ EmailService: Disponible")
        else:
            print("⚠️  EmailService: No disponible")
        
        if EMAIL_TEMPLATES_AVAILABLE:
            print("✅ Email Templates: Disponibles")
        else:
            print("⚠️  Email Templates: No disponibles")
            
    except Exception as e:
        print(f"⚠️  Error verificando EmailService: {e}")
    
    # Verificar Flask-Mail
    try:
        from app import mail
        if mail:
            print("✅ Flask-Mail: Configurado")
        else:
            print("⚠️  Flask-Mail: No configurado")
    except Exception as e:
        print(f"⚠️  Error verificando Flask-Mail: {e}")

def generate_report():
    """Generar reporte completo"""
    print_header("🔍 VERIFICACIÓN DEL SISTEMA DE NOTIFICACIONES")
    print(f"Fecha: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
    
    try:
        verify_notification_settings()
        verify_notifications_status()
        verify_email_logs()
        verify_notification_engine()
        verify_integration()
        
        print_section("✅ VERIFICACIÓN COMPLETADA")
        print("El sistema de notificaciones ha sido verificado.")
        print("Revisa los resultados arriba para identificar posibles problemas.\n")
        
    except Exception as e:
        print(f"\n❌ ERROR DURANTE LA VERIFICACIÓN: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    with app.app_context():
        success = generate_report()
        sys.exit(0 if success else 1)
