#!/usr/bin/env python3
"""
Verificar y mostrar configuración de Office 365 para info@example.com
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, EmailConfig


def verify_o365_config():
    """Verificar configuración de Office 365"""
    parser = argparse.ArgumentParser(description='Verificación O365 vs BD')
    parser.add_argument('--org-id', type=int, default=None, help='Tenant para EmailConfig')
    args = parser.parse_args()

    print('=' * 60)
    print('VERIFICACIÓN: info@example.com (Office 365)')
    if args.org_id is not None:
        print(f'  (org: {args.org_id})')
    print('=' * 60)

    with app.app_context():
        config = EmailConfig.get_active_config(organization_id=args.org_id)
        
        if not config:
            print("\n❌ No hay configuración activa")
            return
        
        print("\n✅ CONFIGURACIÓN ACTUAL:")
        print(f"   Servidor:        {config.mail_server}")
        print(f"   Puerto:          {config.mail_port}")
        print(f"   TLS:             {config.mail_use_tls}")
        print(f"   Usuario:         {config.mail_username}")
        print(f"   Remitente:       {config.mail_default_sender}")
        print(f"   Contraseña:      {'*' * 16 if config.mail_password else '(NO CONFIGURADA)'}")
        print(f"   Longitud pwd:    {len(config.mail_password) if config.mail_password else 0} caracteres")
        
        # Verificar que todo esté correcto para Office 365
        print("\n🔍 VERIFICACIÓN DE CONFIGURACIÓN:")
        
        checks = []
        
        if config.mail_server == 'smtp.office365.com':
            checks.append(("✅ Servidor correcto (smtp.office365.com)", True))
        else:
            checks.append((f"❌ Servidor incorrecto: {config.mail_server}", False))
        
        if config.mail_port == 587:
            checks.append(("✅ Puerto correcto (587)", True))
        else:
            checks.append((f"❌ Puerto incorrecto: {config.mail_port}", False))
        
        if config.mail_use_tls:
            checks.append(("✅ TLS habilitado", True))
        else:
            checks.append(("❌ TLS no habilitado", False))
        
        if config.mail_username == 'info@example.com':
            checks.append(("✅ Usuario correcto", True))
        else:
            checks.append((f"❌ Usuario incorrecto: {config.mail_username}", False))
        
        if config.mail_default_sender == 'info@example.com':
            checks.append(("✅ Remitente correcto", True))
        else:
            checks.append((f"❌ Remitente incorrecto: {config.mail_default_sender}", False))
        
        if config.mail_password:
            if len(config.mail_password) >= 8:
                checks.append(("✅ Contraseña configurada", True))
            else:
                checks.append(("⚠️  Contraseña muy corta (mínimo 8 caracteres)", False))
        else:
            checks.append(("❌ Contraseña NO configurada", False))
        
        for check, status in checks:
            print(f"   {check}")
        
        all_ok = all(status for _, status in checks)
        
        if all_ok:
            print("\n✅ CONFIGURACIÓN COMPLETA Y CORRECTA")
            print("\n💡 PRÓXIMOS PASOS:")
            print("   1. Reinicia el servicio: sudo systemctl restart nodeone.service")
            print("   2. Prueba el envío desde /admin/email")
            print("   3. Si falla con error 535, actualiza la contraseña en /admin/email")
        else:
            print("\n⚠️  HAY PROBLEMAS EN LA CONFIGURACIÓN")
            print("\n💡 SOLUCIÓN:")
            print("   1. Ve a /admin/email")
            print("   2. Verifica/actualiza la configuración")
            print("   3. Asegúrate de usar la contraseña correcta de Office 365")
            print("   4. Guarda y reinicia el servicio")
        
        print("\n📝 NOTAS IMPORTANTES:")
        print("   - Office 365 usa tu contraseña normal (no requiere App Password como Gmail)")
        print("   - Si tienes MFA (Multi-Factor Authentication) activado, puede que necesites")
        print("     una contraseña de aplicación (configurar en Azure AD)")
        print("   - La contraseña debe ser la misma que usas para iniciar sesión en")
        print("     https://outlook.office.com")
        
        print("\n" + "=" * 60)

if __name__ == '__main__':
    verify_o365_config()
