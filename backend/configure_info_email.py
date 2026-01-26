#!/usr/bin/env python3
"""
Script para configurar email con info@relaticpanama.org
"""

import sys
import os
from datetime import datetime

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, EmailConfig

def configure_info_email():
    """Configurar email con info@relaticpanama.org"""
    print("=" * 60)
    print("CONFIGURACIÓN DE EMAIL: info@relaticpanama.org")
    print("=" * 60)
    
    with app.app_context():
        # Desactivar todas las configuraciones anteriores
        EmailConfig.query.update({'is_active': False})
        
        # Buscar configuración existente
        config = EmailConfig.query.first()
        
        if not config:
            config = EmailConfig()
            db.session.add(config)
        
        # Configurar para Office 365 (más común para dominios personalizados)
        print("\n📧 Configurando para Office 365...")
        print("   Si info@relaticpanama.org es Gmail, cambia manualmente el servidor")
        
        config.mail_server = 'smtp.office365.com'
        config.mail_port = 587
        config.mail_use_tls = True
        config.mail_use_ssl = False
        config.mail_username = 'info@relaticpanama.org'
        config.mail_default_sender = 'info@relaticpanama.org'
        config.use_environment_variables = False  # Usar BD, no variables de entorno
        config.is_active = True
        config.updated_at = datetime.utcnow()
        
        # Pedir contraseña
        print("\n🔐 Ingresa la contraseña para info@relaticpanama.org")
        print("   (Si es Office 365, usa tu contraseña normal o contraseña de aplicación)")
        print("   (Si es Gmail, DEBES usar contraseña de aplicación de 16 caracteres)")
        password = input("   Contraseña: ").strip()
        
        if password:
            config.mail_password = password
        else:
            print("   ⚠️  No se ingresó contraseña. Debes configurarla manualmente.")
        
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
            print(f"   Contraseña:      {'*' * 16 if app.config.get('MAIL_PASSWORD') else '(no configurada)'}")
            
            print("\n💡 NOTAS:")
            print("   - Si info@relaticpanama.org es Gmail, cambia el servidor a smtp.gmail.com")
            print("   - Reinicia el servicio después de configurar: sudo systemctl restart membresia-relatic.service")
            print("   - Prueba el envío desde /admin/email")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error guardando configuración: {e}")
            return False
        
        print("\n" + "=" * 60)
        return True

if __name__ == '__main__':
    configure_info_email()
