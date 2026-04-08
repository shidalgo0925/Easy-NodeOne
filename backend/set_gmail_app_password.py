#!/usr/bin/env python3
"""
Script para configurar contraseña de aplicación de Gmail
"""

import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, EmailConfig


def set_gmail_app_password():
    """Configurar contraseña de aplicación de Gmail"""
    parser = argparse.ArgumentParser(description='Guardar app password Gmail en EmailConfig')
    parser.add_argument('--org-id', type=int, default=None, help='Tenant de la fila EmailConfig')
    args = parser.parse_args()

    print('=' * 60)
    print('CONFIGURAR CONTRASEÑA DE APLICACIÓN - Gmail')
    if args.org_id is not None:
        print(f'  (org: {args.org_id})')
    print('=' * 60)
    
    print("\n📝 IMPORTANTE: No puedo generar la contraseña por ti")
    print("   Solo Google puede generar contraseñas de aplicación")
    print("   Debes generarla desde tu cuenta de Google")
    
    print("\n🔐 PASOS PARA GENERAR LA CONTRASEÑA:")
    print("   1. Ve a: https://myaccount.google.com/apppasswords")
    print("   2. Inicia sesión con: relaticpanama2025@gmail.com")
    print("   3. Si no tienes 2FA, actívalo primero (requerido)")
    print("   4. Selecciona:")
    print("      - App: 'Correo'")
    print("      - Device: 'Otro (nombre personalizado)'")
    print("      - Escribe: 'RelaticPanama'")
    print("   5. Haz clic en 'Generar'")
    print("   6. Copia la contraseña de 16 caracteres (sin espacios)")
    
    print("\n" + "=" * 60)
    print("Una vez que tengas la contraseña de 16 caracteres:")
    print("=" * 60)
    
    app_password = input("\n🔑 Pega la contraseña de aplicación (16 caracteres): ").strip().replace(' ', '')
    
    if not app_password:
        print("\n❌ No se ingresó contraseña")
        return False
    
    if len(app_password) != 16:
        print(f"\n⚠️  La contraseña debe tener exactamente 16 caracteres (tiene {len(app_password)})")
        print("   Verifica que copiaste correctamente la contraseña de aplicación")
        respuesta = input("   ¿Continuar de todas formas? (s/n): ").strip().lower()
        if respuesta != 's':
            return False
    
    with app.app_context():
        config = EmailConfig.get_active_config(organization_id=args.org_id)
        
        if not config:
            print("\n❌ No hay configuración activa")
            return False
        
        if config.mail_username != 'relaticpanama2025@gmail.com':
            print(f"\n⚠️  La configuración es para: {config.mail_username}")
            return False
        
        print(f"\n📧 Actualizando contraseña...")
        print(f"   Usuario: {config.mail_username}")
        print(f"   Contraseña anterior: {'*' * 16 if config.mail_password else '(no configurada)'}")
        
        config.mail_password = app_password
        config.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            print(f"\n✅ Contraseña de aplicación configurada exitosamente")
            print(f"   Longitud: {len(app_password)} caracteres")
            
            print("\n💡 PRÓXIMOS PASOS:")
            print("   1. Reinicia el servicio: sudo systemctl restart membresia-relatic.service")
            print("   2. Prueba el envío desde /admin/email")
            print("   3. Debería funcionar correctamente ahora")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error: {e}")
            return False
        
        print("\n" + "=" * 60)
        return True

if __name__ == '__main__':
    set_gmail_app_password()
