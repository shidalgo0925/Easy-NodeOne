#!/usr/bin/env python3
"""
Configurar info@relaticpanama.org para Office 365
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, EmailConfig

def configure_o365_info():
    """Configurar info@relaticpanama.org para Office 365"""
    print("=" * 60)
    print("CONFIGURANDO: info@relaticpanama.org (Office 365)")
    print("=" * 60)
    
    with app.app_context():
        # Desactivar todas las configuraciones anteriores
        EmailConfig.query.update({'is_active': False})
        
        # Buscar o crear configuración
        config = EmailConfig.query.first()
        if not config:
            config = EmailConfig()
            db.session.add(config)
        
        # Configurar para Office 365
        print("\n📧 Configurando para Office 365...")
        
        config.mail_server = 'smtp.office365.com'
        config.mail_port = 587
        config.mail_use_tls = True
        config.mail_use_ssl = False
        config.mail_username = 'info@relaticpanama.org'
        config.mail_default_sender = 'info@relaticpanama.org'
        config.use_environment_variables = False  # Usar BD, no variables de entorno
        config.is_active = True
        config.updated_at = datetime.utcnow()
        
        # Mantener contraseña existente si hay una
        if config.mail_password:
            print(f"✅ Contraseña existente mantenida ({len(config.mail_password)} caracteres)")
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
            print(f"   Contraseña:      {'*' * 16 if app.config.get('MAIL_PASSWORD') else '(NO CONFIGURADA)'}")
            
            print("\n✅ CONFIGURACIÓN COMPLETA PARA OFFICE 365:")
            print("   ✅ Servidor: smtp.office365.com")
            print("   ✅ Puerto: 587")
            print("   ✅ TLS: True")
            print("   ✅ Usuario: info@relaticpanama.org")
            print("   ✅ Remitente: info@relaticpanama.org")
            
            if not app.config.get('MAIL_PASSWORD'):
                print("\n⚠️  IMPORTANTE: Verifica que la contraseña esté correcta")
                print("   Si no funciona, actualiza la contraseña desde /admin/email")
            
            print("\n💡 PRÓXIMOS PASOS:")
            print("   1. Reinicia el servicio: sudo systemctl restart membresia-relatic.service")
            print("   2. Prueba el envío desde /admin/email")
            print("   3. Si falla, verifica la contraseña en /admin/email")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error: {e}")
            return False
        
        print("\n" + "=" * 60)
        return True

if __name__ == '__main__':
    configure_o365_info()
