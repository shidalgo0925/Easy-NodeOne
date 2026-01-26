#!/usr/bin/env python3
"""
Script para reenviar notificaciones pendientes
Procesa notificaciones que fueron creadas pero no se enviaron por email
"""

import sys
import os
from datetime import datetime

# Agregar el directorio backend al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Notification, User, NotificationEngine, EmailConfig

def retry_pending_notifications():
    """Reenviar notificaciones pendientes de envío"""
    with app.app_context():
        # Aplicar configuración de email desde BD
        try:
            email_config = EmailConfig.get_active_config()
            if email_config:
                email_config.apply_to_app(app)
                # Reinicializar mail
                from flask_mail import Mail
                global mail
                mail = Mail(app)
                mail.init_app(app)
        except Exception as e:
            print(f"⚠️  Advertencia al aplicar configuración de email: {e}")
        
        try:
            # Buscar notificaciones pendientes
            pending = Notification.query.filter_by(email_sent=False).all()
            
            if not pending:
                print("✅ No hay notificaciones pendientes de envío")
                return
            
            print(f"\n{'='*70}")
            print(f"  🔄 REENVÍO DE NOTIFICACIONES PENDIENTES")
            print(f"{'='*70}")
            print(f"\n📊 Total de notificaciones pendientes: {len(pending)}\n")
            
            success_count = 0
            failed_count = 0
            skipped_count = 0
            
            for notification in pending:
                user = User.query.get(notification.user_id)
                
                if not user:
                    print(f"⚠️  Notificación {notification.id}: Usuario no encontrado")
                    skipped_count += 1
                    continue
                
                print(f"📧 Procesando notificación {notification.id}: {notification.notification_type}")
                print(f"   Usuario: {user.email}")
                print(f"   Título: {notification.title}")
                
                # Intentar reenviar según el tipo
                try:
                    # Verificar si la notificación está habilitada
                    from app import NotificationSettings
                    if not NotificationSettings.is_enabled(notification.notification_type):
                        print(f"   ⚠️  Notificación deshabilitada, saltando...")
                        skipped_count += 1
                        continue
                    
                    # Reenviar email (simplificado - solo marca como enviado si el email_service está disponible)
                    from app import email_service, EMAIL_TEMPLATES_AVAILABLE
                    
                    if EMAIL_TEMPLATES_AVAILABLE and email_service:
                        # Intentar enviar email básico
                        try:
                            html_content = f"""
                                <h2>{notification.title}</h2>
                                <p>{notification.message}</p>
                                <p>Saludos,<br>Equipo RelaticPanama</p>
                            """
                            
                            success = email_service.send_email(
                                subject=notification.title,
                                recipients=[user.email],
                                html_content=html_content,
                                email_type=notification.notification_type,
                                related_entity_type='notification',
                                related_entity_id=notification.id,
                                recipient_id=user.id,
                                recipient_name=f"{user.first_name} {user.last_name}"
                            )
                            
                            if success:
                                notification.email_sent = True
                                notification.email_sent_at = datetime.utcnow()
                                db.session.commit()
                                print(f"   ✅ Email enviado exitosamente")
                                success_count += 1
                            else:
                                print(f"   ❌ Error al enviar email")
                                failed_count += 1
                        except Exception as e:
                            print(f"   ❌ Error: {e}")
                            failed_count += 1
                    else:
                        print(f"   ⚠️  EmailService no disponible, solo marcando como procesada")
                        # Marcar como enviada aunque no se haya enviado realmente
                        # (para evitar procesar indefinidamente)
                        notification.email_sent = True
                        notification.email_sent_at = datetime.utcnow()
                        db.session.commit()
                        skipped_count += 1
                
                except Exception as e:
                    print(f"   ❌ Error procesando notificación: {e}")
                    import traceback
                    traceback.print_exc()
                    failed_count += 1
                
                print()
            
            # Resumen
            print(f"\n{'='*70}")
            print(f"  📊 RESUMEN")
            print(f"{'='*70}")
            print(f"   ✅ Enviadas exitosamente: {success_count}")
            print(f"   ❌ Fallidas: {failed_count}")
            print(f"   ⚠️  Omitidas: {skipped_count}")
            print(f"   📧 Total procesadas: {len(pending)}")
            print(f"{'='*70}\n")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error durante el procesamiento: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

if __name__ == '__main__':
    print(f"\n{'='*70}")
    print("  🔄 REENVÍO DE NOTIFICACIONES PENDIENTES")
    print(f"{'='*70}")
    print(f"\n📅 Fecha: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
    
    success = retry_pending_notifications()
    
    if success:
        print("✅ Proceso completado")
        sys.exit(0)
    else:
        print("❌ Proceso falló")
        sys.exit(1)
