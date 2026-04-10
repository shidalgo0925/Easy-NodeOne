#!/usr/bin/env python3
"""
Configurar email con nodeone@gmail.com (Gmail)
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, EmailConfig

def setup_gmail_smtp():
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
        
        # Mantener contraseña existente si hay una
        if config.mail_password:
            print(f"✅ Contraseña existente mantenida ({len(config.mail_password)} caracteres)")
            if len(config.mail_password) != 16:
                print("⚠️  Para Gmail necesitas una contraseña de aplicación de 16 caracteres")
        else:
            print("⚠️  No hay contraseña configurada")
            print("   Debes configurarla desde /admin/email")
        
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
            print(f"   Contraseña:      {'*' * 16 if app.config.get('MAIL_PASSWORD') else '(NO CONFIGURADA - REQUERIDA)'}")
            
            print("\n✅ CONFIGURACIÓN COMPLETA PARA GMAIL:")
            print("   ✅ Servidor: smtp.gmail.com")
            print("   ✅ Puerto: 587")
            print("   ✅ TLS: True")
            print("   ✅ Usuario: nodeone@gmail.com")
            print("   ✅ Remitente: nodeone@gmail.com")
            
            print("\n🔐 IMPORTANTE: CONTRASEÑA DE APLICACIÓN REQUERIDA")
            print("   Para Gmail necesitas una contraseña de aplicación (16 caracteres)")
            print("   NO uses tu contraseña normal de Gmail")
            print("\n📝 Pasos para generar contraseña de aplicación:")
            print("   1. Ve a: https://myaccount.google.com/apppasswords")
            print("   2. Selecciona 'Correo' → 'Otro (nombre personalizado)'")
            print("   3. Escribe: 'Easy NodeOne'")
            print("   4. Copia la contraseña de 16 caracteres (sin espacios)")
            print("   5. Configúrala en /admin/email")
            
            print("\n💡 PRÓXIMOS PASOS:")
            print("   1. Genera la contraseña de aplicación en Google")
            print("   2. Ve a /admin/email y configura la contraseña (16 caracteres)")
            print("   3. Reinicia el servicio: sudo systemctl restart nodeone.service")
            print("   4. Prueba el envío desde /admin/email")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error: {e}")
            return False
        
        print("\n" + "=" * 60)
        return True

if __name__ == '__main__':
    setup_gmail_smtp()
