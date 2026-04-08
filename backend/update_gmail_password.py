#!/usr/bin/env python3
"""
Actualizar contraseña de Gmail
"""

import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, EmailConfig


def update_gmail_password():
    """Actualizar contraseña de Gmail"""
    parser = argparse.ArgumentParser(description='Actualizar mail_password en EmailConfig')
    parser.add_argument('--org-id', type=int, default=None, help='Tenant de la fila EmailConfig')
    args = parser.parse_args()

    print('=' * 60)
    print('ACTUALIZAR CONTRASEÑA: relaticpanama2025@gmail.com')
    if args.org_id is not None:
        print(f'  (org: {args.org_id})')
    print('=' * 60)

    with app.app_context():
        config = EmailConfig.get_active_config(organization_id=args.org_id)
        
        if not config:
            print("\n❌ No hay configuración activa")
            return False
        
        if config.mail_username != 'relaticpanama2025@gmail.com':
            print(f"\n⚠️  La configuración es para: {config.mail_username}")
            return False
        
        print(f"\n📧 Configuración actual:")
        print(f"   Usuario: {config.mail_username}")
        print(f"   Contraseña actual: {'*' * 16 if config.mail_password else '(no configurada)'}")
        print(f"   Longitud actual: {len(config.mail_password) if config.mail_password else 0} caracteres")
        
        # Actualizar contraseña
        new_password = "Relatic2025"
        config.mail_password = new_password
        config.updated_at = datetime.utcnow()
        
        print(f"\n🔐 Actualizando contraseña...")
        print(f"   Nueva contraseña: {'*' * len(new_password)}")
        print(f"   Longitud: {len(new_password)} caracteres")
        
        if len(new_password) != 16:
            print(f"\n⚠️  ADVERTENCIA: La contraseña tiene {len(new_password)} caracteres")
            print("   Para Gmail necesitas una CONTRASEÑA DE APLICACIÓN de 16 caracteres")
            print("   Esta contraseña probablemente NO funcionará con Gmail")
            print("\n📝 Para generar contraseña de aplicación:")
            print("   1. Ve a: https://myaccount.google.com/apppasswords")
            print("   2. Selecciona 'Correo' → 'Otro (nombre personalizado)'")
            print("   3. Escribe: 'RelaticPanama'")
            print("   4. Copia la contraseña de 16 caracteres")
            print("   5. Actualiza desde /admin/email")
        
        try:
            db.session.commit()
            print(f"\n✅ Contraseña actualizada en la base de datos")
            
            print("\n💡 PRÓXIMOS PASOS:")
            print("   1. Reinicia el servicio: sudo systemctl restart membresia-relatic.service")
            print("   2. Prueba el envío desde /admin/email")
            print("   3. Si falla, genera una contraseña de aplicación de 16 caracteres")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error: {e}")
            return False
        
        print("\n" + "=" * 60)
        return True

if __name__ == '__main__':
    update_gmail_password()
