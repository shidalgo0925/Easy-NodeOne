#!/usr/bin/env python3
"""
Configurar email con nodeone@gmail.com (Gmail)
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, EmailConfig

def configure_gmail_smtp():
    """Configurar email con nodeone@gmail.com"""
    print("=" * 60)
    print("CONFIGURANDO: nodeone@gmail.com (Gmail)")
    print("=" * 60)
    
    with app.app_context():
        # Desactivar todas las configuraciones anteriores
        EmailConfig.query.update({'is_active': False})
        
        # Buscar o crear configuración
        config = EmailConfig.query.first()
        if not config:
            config = EmailConfig()
            db.session.add(config)
        
        # Configurar para Gmail
        print("\n📧 Configurando para Gmail...")
        
        config.mail_server = 'smtp.gmail.com'
        config.mail_port = 587
        config.mail_use_tls = True
        config.mail_use_ssl = False
        config.mail_username = 'nodeone@gmail.com'
        config.mail_default_sender = 'nodeone@gmail.com'
        config.use_environment_variables = False  # Usar BD, no variables de entorno
        config.is_active = True
        config.updated_at = datetime.utcnow()
        
        print("\n🔐 IMPORTANTE: Para Gmail necesitas una CONTRASEÑA DE APLICACIÓN")
        print("   (No uses tu contraseña normal de Gmail)")
        print("\n📝 Pasos para generar contraseña de aplicación:")
        print("   1. Ve a: https://myaccount.google.com/apppasswords")
        print("   2. Selecciona 'Correo' → 'Otro (nombre personalizado)'")
        print("   3. Escribe: 'Easy NodeOne'")
        print("   4. Copia la contraseña de 16 caracteres (sin espacios)")
        print("\n🔑 Ingresa la contraseña de aplicación (16 caracteres):")
        password = input("   Contraseña: ").strip().replace(' ', '')
        
        if not password:
            print("\n⚠️  No se ingresó contraseña")
            print("   Puedes configurarla después desde /admin/email")
        elif len(password) != 16:
            print(f"\n⚠️  La contraseña debe tener exactamente 16 caracteres (tiene {len(password)})")
            print("   Verifica que sea una contraseña de aplicación de Gmail")
            respuesta = input("   ¿Continuar de todas formas? (s/n): ").strip().lower()
            if respuesta != 's':
                print("   Configuración cancelada")
                return False
            config.mail_password = password
        else:
            config.mail_password = password
            print(f"✅ Contraseña configurada ({len(password)} caracteres)")
        
        try:
            db.session.commit()
            print("\n✅ Configuración guardada en la base de datos")
            
            # Aplicar configuración a Flask
            config.apply_to_app(app)
            
            print("\n📋 CONFIGURACIÓN APLICADA:")
            print(f"   Servidor:        {app.config.get('MAIL_SERVER')}")
            print(f"   Puerto:          {app.config.get('MAIL_PORT')}")
            print(f"   TLS:             {app.config.get('MAIL_USE_TLS')}")
            print(f"   Usuario:         {app.config.get('MAIL_USERNAME')}")
            print(f"   Remitente:       {app.config.get('MAIL_DEFAULT_SENDER')}")
            print(f"   Contraseña:      {'*' * 16 if app.config.get('MAIL_PASSWORD') else '(NO CONFIGURADA)'}")
            
            print("\n✅ CONFIGURACIÓN COMPLETA PARA GMAIL:")
            print("   ✅ Servidor: smtp.gmail.com")
            print("   ✅ Puerto: 587")
            print("   ✅ TLS: True")
            print("   ✅ Usuario: nodeone@gmail.com")
            print("   ✅ Remitente: nodeone@gmail.com")
            
            if not app.config.get('MAIL_PASSWORD') or len(app.config.get('MAIL_PASSWORD', '')) != 16:
                print("\n⚠️  IMPORTANTE: Configura la contraseña de aplicación desde /admin/email")
                print("   Debe ser exactamente 16 caracteres (sin espacios)")
            
            print("\n💡 PRÓXIMOS PASOS:")
            print("   1. Si no ingresaste la contraseña, configúrala desde /admin/email")
            print("   2. Reinicia el servicio: sudo systemctl restart nodeone.service")
            print("   3. Prueba el envío desde /admin/email")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error: {e}")
            return False
        
        print("\n" + "=" * 60)
        return True

if __name__ == '__main__':
    configure_gmail_smtp()
