#!/usr/bin/env python3
"""
Script para configurar email con info@relaticpanama.org (Office 365)
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, EmailConfig

def setup_info_email():
    """Configurar email con info@relaticpanama.org"""
    print("=" * 60)
    print("CONFIGURANDO: info@relaticpanama.org")
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
        print("   (Si es Gmail, cambia manualmente el servidor a smtp.gmail.com)")
        
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
        if not config.mail_password:
            print("\n⚠️  No hay contraseña configurada.")
            print("   Debes configurarla desde /admin/email o ejecutar:")
            print("   python3 configure_info_email.py")
        else:
            print(f"\n✅ Contraseña existente mantenida ({len(config.mail_password)} caracteres)")
        
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
            
            print("\n📝 PRÓXIMOS PASOS:")
            print("   1. Configura la contraseña desde /admin/email")
            print("   2. O ejecuta: python3 configure_info_email.py")
            print("   3. Reinicia el servicio: sudo systemctl restart membresia-relatic.service")
            print("   4. Prueba el envío desde /admin/email")
            
            print("\n💡 NOTAS:")
            print("   - Si info@relaticpanama.org es Gmail, cambia servidor a smtp.gmail.com")
            print("   - Office 365 usa tu contraseña normal (no requiere App Password)")
            print("   - Gmail requiere contraseña de aplicación (16 caracteres)")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error: {e}")
            return False
        
        print("\n" + "=" * 60)
        return True

if __name__ == '__main__':
    setup_info_email()
