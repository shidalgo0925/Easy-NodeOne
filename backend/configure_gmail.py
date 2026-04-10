#!/usr/bin/env python3
"""
Script para configurar Gmail con contraseña de aplicación en la base de datos
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, EmailConfig
from datetime import datetime

def configure_gmail(gmail_email, app_password):
    """Configurar Gmail en la base de datos"""
    with app.app_context():
        # Desactivar todas las configuraciones anteriores
        EmailConfig.query.update({'is_active': False})
        
        # Buscar si existe una configuración
        config = EmailConfig.query.first()
        
        if not config:
            # Crear nueva configuración
            config = EmailConfig(
                mail_server='smtp.gmail.com',
                mail_port=587,
                mail_use_tls=True,
                mail_use_ssl=False,
                mail_username=gmail_email,
                mail_password=app_password,
                mail_default_sender=gmail_email,
                use_environment_variables=False,
                is_active=True
            )
            db.session.add(config)
            print("✅ Nueva configuración de Gmail creada")
        else:
            # Actualizar configuración existente
            config.mail_server = 'smtp.gmail.com'
            config.mail_port = 587
            config.mail_use_tls = True
            config.mail_use_ssl = False
            config.mail_username = gmail_email
            config.mail_password = app_password
            config.mail_default_sender = gmail_email
            config.use_environment_variables = False
            config.is_active = True
            config.updated_at = datetime.utcnow()
            print("✅ Configuración de Gmail actualizada")
        
        try:
            db.session.commit()
            print("\n📧 Configuración de Gmail:")
            print(f"   Servidor: {config.mail_server}")
            print(f"   Puerto: {config.mail_port}")
            print(f"   TLS: {config.mail_use_tls}")
            print(f"   Usuario: {config.mail_username}")
            print(f"   Remitente: {config.mail_default_sender}")
            print("\n✅ Configuración guardada exitosamente")
            print("\n⚠️  IMPORTANTE: Reinicia el servidor para aplicar los cambios:")
            print("   sudo systemctl restart nodeone.service")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error al guardar configuración: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    import getpass
    
    print("="*70)
    print("CONFIGURACIÓN DE GMAIL CON CONTRASEÑA DE APLICACIÓN")
    print("="*70)
    print("\n📝 Necesitas:")
    print("   1. Una cuenta de Gmail")
    print("   2. Verificación en 2 pasos habilitada")
    print("   3. Una contraseña de aplicación generada")
    print("\n💡 Para generar una contraseña de aplicación:")
    print("   https://myaccount.google.com/apppasswords")
    print("\n" + "="*70 + "\n")
    
    gmail_email = input("Ingresa el email de Gmail (ej: tuemail@gmail.com): ").strip()
    if not gmail_email:
        print("❌ Email requerido")
        sys.exit(1)
    
    app_password = getpass.getpass("Ingresa la contraseña de aplicación (16 caracteres): ").strip()
    if not app_password:
        print("❌ Contraseña de aplicación requerida")
        sys.exit(1)
    
    if len(app_password) != 16 and len(app_password.replace(' ', '')) != 16:
        print("⚠️  Advertencia: La contraseña de aplicación debería tener 16 caracteres")
        respuesta = input("¿Continuar de todas formas? (s/n): ").strip().lower()
        if respuesta != 's':
            sys.exit(0)
    
    print("\n📧 Configurando Gmail...")
    if configure_gmail(gmail_email, app_password):
        print("\n✅ Configuración completada exitosamente!")
    else:
        print("\n❌ Error al configurar Gmail")
        sys.exit(1)

