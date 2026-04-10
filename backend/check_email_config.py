#!/usr/bin/env python3
"""
Script para verificar la configuración actual de SMTP.
Uso: python check_email_config.py [--org-id ID]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, EmailConfig


def check_email_config():
    parser = argparse.ArgumentParser(description='Verificación SMTP')
    parser.add_argument('--org-id', type=int, default=None, help='Tenant; sin flag = primera activa (legado)')
    args = parser.parse_args()

    print('=' * 60)
    print('VERIFICACIÓN DE CONFIGURACIÓN SMTP')
    if args.org_id is not None:
        print(f'  organization_id: {args.org_id}')
    print('=' * 60)

    with app.app_context():
        config = EmailConfig.get_active_config(organization_id=args.org_id)
        
        if not config:
            print("\n❌ No hay configuración de email activa en la base de datos")
            print("\n📝 Configuraciones disponibles:")
            all_configs = EmailConfig.query.all()
            if all_configs:
                for cfg in all_configs:
                    print(f"   - ID: {cfg.id}, Activa: {cfg.is_active}, Servidor: {cfg.mail_server}")
            else:
                print("   - No hay configuraciones en la base de datos")
            return
        
        print(f'\n✅ Configuración activa encontrada (ID: {config.id})')
        print(f'   organization_id (fila): {getattr(config, "organization_id", None)}')
        print("\n📧 CONFIGURACIÓN SMTP:")
        print(f"   Servidor:        {config.mail_server}")
        print(f"   Puerto:          {config.mail_port}")
        print(f"   TLS:             {config.mail_use_tls}")
        print(f"   SSL:             {config.mail_use_ssl}")
        print(f"   Usuario:         {config.mail_username or '(vacío)'}")
        print(f"   Contraseña:      {'*' * 16 if config.mail_password else '(vacía)'}")
        print(f"   Remitente:        {config.mail_default_sender}")
        print(f"   Usa vars. env.:   {config.use_environment_variables}")
        print(f"   Última actualización: {config.updated_at}")
        
        # Verificar variables de entorno si está configurado así
        if config.use_environment_variables:
            print("\n🔍 Variables de entorno:")
            import os
            mail_server = os.getenv('MAIL_SERVER', 'No configurada')
            mail_port = os.getenv('MAIL_PORT', 'No configurada')
            mail_username = os.getenv('MAIL_USERNAME', 'No configurada')
            mail_password = os.getenv('MAIL_PASSWORD', 'No configurada')
            
            print(f"   MAIL_SERVER:     {mail_server}")
            print(f"   MAIL_PORT:       {mail_port}")
            print(f"   MAIL_USERNAME:   {mail_username}")
            print(f"   MAIL_PASSWORD:   {'*' * 16 if mail_password != 'No configurada' else 'No configurada'}")
        
        # Verificar configuración actual de Flask
        print("\n⚙️  CONFIGURACIÓN ACTUAL DE FLASK:")
        print(f"   MAIL_SERVER:     {app.config.get('MAIL_SERVER', 'No configurada')}")
        print(f"   MAIL_PORT:       {app.config.get('MAIL_PORT', 'No configurada')}")
        print(f"   MAIL_USE_TLS:    {app.config.get('MAIL_USE_TLS', 'No configurada')}")
        print(f"   MAIL_USE_SSL:    {app.config.get('MAIL_USE_SSL', 'No configurada')}")
        print(f"   MAIL_USERNAME:   {app.config.get('MAIL_USERNAME', 'No configurada')}")
        print(f"   MAIL_PASSWORD:   {'*' * 16 if app.config.get('MAIL_PASSWORD') else 'No configurada'}")
        print(f"   MAIL_DEFAULT_SENDER: {app.config.get('MAIL_DEFAULT_SENDER', 'No configurada')}")
        
        # Análisis de los correos mencionados
        print("\n📬 ANÁLISIS DE CORREOS DISPONIBLES:")
        
        email1 = "info@example.com"
        email2 = "easytechservices25@gmail.com"
        
        current_username = config.mail_username or app.config.get('MAIL_USERNAME', '')
        current_sender = config.mail_default_sender or app.config.get('MAIL_DEFAULT_SENDER', '')
        
        print(f"\n   1. {email1}")
        if email1 in current_username or email1 in current_sender:
            print(f"      ✅ Está configurado como usuario o remitente")
        else:
            print(f"      ⚠️  No está configurado actualmente")
        
        print(f"\n   2. {email2}")
        if email2 in current_username or email2 in current_sender:
            print(f"      ✅ Está configurado como usuario o remitente")
        else:
            print(f"      ⚠️  No está configurado actualmente")
        
        # Recomendaciones
        print("\n💡 RECOMENDACIONES:")
        
        if "gmail.com" in config.mail_server.lower():
            print("   - Servidor Gmail detectado")
            if not config.mail_password or len(config.mail_password) < 16:
                print("   ⚠️  Para Gmail necesitas una CONTRASEÑA DE APLICACIÓN (16 caracteres)")
                print("      Genera una en: https://myaccount.google.com/apppasswords")
            else:
                print("   ✅ Contraseña configurada (verifica que sea contraseña de aplicación)")
        
        if "example.com" in email1:
            print(f"   - Para {email1}:")
            print("     * Verifica el servidor SMTP (puede ser Office 365, Gmail, o otro)")
            print("     * Si es Office 365: smtp.office365.com, puerto 587, TLS=True")
            print("     * Si es Gmail: smtp.gmail.com, puerto 587, TLS=True")
        
        if "gmail.com" in email2:
            print(f"   - Para {email2}:")
            print("     * Servidor: smtp.gmail.com")
            print("     * Puerto: 587")
            print("     * TLS: True")
            print("     * Requiere contraseña de aplicación (16 caracteres)")
        
        print("\n" + "=" * 60)

if __name__ == '__main__':
    check_email_config()

