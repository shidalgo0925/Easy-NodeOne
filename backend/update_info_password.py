#!/usr/bin/env python3
"""
Actualizar contraseña de info@example.com
"""

import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, EmailConfig


def update_info_password():
    """Actualizar contraseña de info@example.com"""
    parser = argparse.ArgumentParser(description='Actualizar contraseña en EmailConfig')
    parser.add_argument('--org-id', type=int, default=None, help='Tenant de la fila EmailConfig')
    args = parser.parse_args()

    print('=' * 60)
    print('ACTUALIZAR CONTRASEÑA: info@example.com')
    if args.org_id is not None:
        print(f'  (org: {args.org_id})')
    print('=' * 60)

    with app.app_context():
        config = EmailConfig.get_active_config(organization_id=args.org_id)
        
        if not config:
            print("\n❌ No hay configuración activa")
            return False
        
        if config.mail_username != 'info@example.com':
            print(f"\n⚠️  La configuración es para: {config.mail_username}")
            print("   ¿Quieres actualizar esta configuración?")
            respuesta = input("   (s/n): ").strip().lower()
            if respuesta != 's':
                return False
        
        print(f"\n📧 Configuración actual:")
        print(f"   Usuario: {config.mail_username}")
        print(f"   Contraseña actual: {'*' * 16 if config.mail_password else '(no configurada)'}")
        
        print("\n🔐 Ingresa la nueva contraseña para info@example.com:")
        print("   (La contraseña que usas para iniciar sesión en Outlook)")
        new_password = input("   Contraseña: ").strip()
        
        if not new_password:
            print("\n❌ No se ingresó contraseña")
            return False
        
        # Actualizar contraseña
        config.mail_password = new_password
        config.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            print(f"\n✅ Contraseña actualizada exitosamente")
            print(f"   Longitud: {len(new_password)} caracteres")
            
            print("\n💡 PRÓXIMOS PASOS:")
            print("   1. Reinicia el servicio: sudo systemctl restart nodeone.service")
            print("   2. Prueba el envío desde /admin/email")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error: {e}")
            return False
        
        print("\n" + "=" * 60)
        return True

if __name__ == '__main__':
    update_info_password()
