#!/usr/bin/env python3
"""
Diagnóstico para info@relaticpanama.org
Verifica si es Gmail o Office 365 y configura correctamente
"""

import argparse
import os
import socket
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, EmailConfig

def test_smtp_connection(server, port, use_tls=True):
    """Probar conexión SMTP"""
    try:
        import smtplib
        print(f"   Probando conexión a {server}:{port}...")
        if use_tls:
            smtp = smtplib.SMTP(server, port, timeout=10)
            smtp.starttls()
        else:
            smtp = smtplib.SMTP_SSL(server, port, timeout=10)
        smtp.quit()
        print(f"   ✅ Conexión exitosa")
        return True
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
        return False

def diagnose_info_email():
    """Diagnosticar configuración de info@relaticpanama.org"""
    parser = argparse.ArgumentParser(description='Diagnóstico cuenta info / SMTP')
    parser.add_argument('--org-id', type=int, default=None, help='Tenant para EmailConfig')
    args = parser.parse_args()

    print('=' * 60)
    print('DIAGNÓSTICO: info@relaticpanama.org')
    if args.org_id is not None:
        print(f'  (EmailConfig org: {args.org_id})')
    print('=' * 60)

    with app.app_context():
        config = EmailConfig.get_active_config(organization_id=args.org_id)
        
        if not config:
            print("\n❌ No hay configuración activa")
            return
        
        print(f"\n📧 CONFIGURACIÓN ACTUAL:")
        print(f"   Servidor: {config.mail_server}")
        print(f"   Usuario: {config.mail_username}")
        print(f"   Remitente: {config.mail_default_sender}")
        print(f"   Contraseña: {'*' * 16 if config.mail_password else '(no configurada)'}")
        
        # Verificar qué tipo de cuenta es
        print("\n🔍 DETERMINANDO TIPO DE CUENTA...")
        print("\n   Para determinar si info@relaticpanama.org es Gmail o Office 365:")
        print("   1. ¿Puedes iniciar sesión en https://mail.google.com con info@relaticpanama.org?")
        print("      → Si SÍ: Es Gmail (Google Workspace)")
        print("      → Si NO: Probablemente es Office 365")
        print("\n   2. ¿Puedes iniciar sesión en https://outlook.office.com con info@relaticpanama.org?")
        print("      → Si SÍ: Es Office 365")
        
        # Probar conexiones
        print("\n🔌 PROBANDO CONEXIONES SMTP...")
        
        # Probar Office 365
        print("\n   1. Office 365 (smtp.office365.com:587):")
        o365_ok = test_smtp_connection('smtp.office365.com', 587, use_tls=True)
        
        # Probar Gmail
        print("\n   2. Gmail (smtp.gmail.com:587):")
        gmail_ok = test_smtp_connection('smtp.gmail.com', 587, use_tls=True)
        
        # Recomendaciones
        print("\n💡 RECOMENDACIONES:")
        
        if o365_ok and not gmail_ok:
            print("   ✅ Office 365 está accesible")
            print("   → Configuración recomendada:")
            print("     - Servidor: smtp.office365.com")
            print("     - Puerto: 587")
            print("     - TLS: True")
            print("     - Usa tu contraseña normal de Office 365")
        elif gmail_ok and not o365_ok:
            print("   ✅ Gmail está accesible")
            print("   → Configuración recomendada:")
            print("     - Servidor: smtp.gmail.com")
            print("     - Puerto: 587")
            print("     - TLS: True")
            print("     - REQUIERE contraseña de aplicación (16 caracteres)")
            print("     - Genera una en: https://myaccount.google.com/apppasswords")
        elif o365_ok and gmail_ok:
            print("   ⚠️  Ambos servidores están accesibles")
            print("   → Necesitas determinar cuál es el correcto según tu cuenta")
        else:
            print("   ⚠️  Problemas de conectividad")
            print("   → Verifica tu conexión a internet")
        
        # Verificar configuración actual
        print("\n📋 VERIFICACIÓN DE CONFIGURACIÓN:")
        if config.mail_server == 'smtp.office365.com':
            print("   ✅ Servidor configurado para Office 365")
            if not config.mail_password or len(config.mail_password) < 8:
                print("   ⚠️  Contraseña parece incorrecta o muy corta")
        elif config.mail_server == 'smtp.gmail.com':
            print("   ✅ Servidor configurado para Gmail")
            if not config.mail_password or len(config.mail_password) != 16:
                print("   ⚠️  Para Gmail necesitas contraseña de aplicación (exactamente 16 caracteres)")
        else:
            print(f"   ⚠️  Servidor inusual: {config.mail_server}")
        
        print("\n📝 PRÓXIMOS PASOS:")
        print("   1. Determina si es Gmail o Office 365 (prueba iniciar sesión)")
        print("   2. Si es Gmail:")
        print("      - Genera contraseña de aplicación")
        print("      - Actualiza en /admin/email")
        print("   3. Si es Office 365:")
        print("      - Verifica que la contraseña sea correcta")
        print("      - Actualiza en /admin/email si es necesario")
        print("   4. Reinicia el servicio: sudo systemctl restart membresia-relatic.service")
        print("   5. Prueba el envío desde /admin/email")
        
        print("\n" + "=" * 60)

if __name__ == '__main__':
    diagnose_info_email()
