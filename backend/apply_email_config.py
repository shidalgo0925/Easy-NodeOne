#!/usr/bin/env python3
"""
Script para aplicar la configuración de email y reiniciar el servicio
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, EmailConfig
from flask_mail import Mail

def apply_email_config():
    """Aplicar configuración de email"""
    print("=" * 60)
    print("APLICANDO CONFIGURACIÓN DE EMAIL")
    print("=" * 60)
    
    with app.app_context():
        config = EmailConfig.get_active_config()
        
        if not config:
            print("\n❌ No hay configuración activa")
            return False
        
        print(f"\n📧 Configuración encontrada:")
        print(f"   Servidor: {config.mail_server}")
        print(f"   Usuario: {config.mail_username}")
        print(f"   Remitente: {config.mail_default_sender}")
        
        # Aplicar configuración
        print("\n⚙️  Aplicando configuración a Flask...")
        config.apply_to_app(app)
        
        # Recrear instancia de Mail
        global mail
        mail = Mail(app)
        
        print("\n✅ Configuración aplicada:")
        print(f"   MAIL_SERVER: {app.config.get('MAIL_SERVER')}")
        print(f"   MAIL_PORT: {app.config.get('MAIL_PORT')}")
        print(f"   MAIL_USE_TLS: {app.config.get('MAIL_USE_TLS')}")
        print(f"   MAIL_USERNAME: {app.config.get('MAIL_USERNAME')}")
        print(f"   MAIL_PASSWORD: {'*' * 16 if app.config.get('MAIL_PASSWORD') else '(no configurada)'}")
        print(f"   MAIL_DEFAULT_SENDER: {app.config.get('MAIL_DEFAULT_SENDER')}")
        
        print("\n💡 Para que los cambios surtan efecto en producción:")
        print("   sudo systemctl restart membresia-relatic.service")
        
        print("\n" + "=" * 60)
        return True

if __name__ == '__main__':
    apply_email_config()
