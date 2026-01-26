#!/usr/bin/env python3
"""
Probar configuración de info@relaticpanama.org con Gmail y Office 365
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, EmailConfig

def test_both_configs():
    """Probar ambas configuraciones (Gmail y Office 365)"""
    print("=" * 60)
    print("PRUEBA DE CONFIGURACIÓN: info@relaticpanama.org")
    print("=" * 60)
    
    with app.app_context():
        config = EmailConfig.get_active_config()
        
        if not config:
            print("\n❌ No hay configuración activa")
            return
        
        current_password = config.mail_password
        
        print("\n📧 CONFIGURACIÓN ACTUAL:")
        print(f"   Servidor: {config.mail_server}")
        print(f"   Usuario: {config.mail_username}")
        print(f"   Contraseña: {'*' * 16 if current_password else '(no configurada)'}")
        
        print("\n💡 DADO QUE ANTES FUNCIONABA CON GMAIL:")
        print("   Es muy probable que info@relaticpanama.org también sea Gmail (Google Workspace)")
        print("   Si es así, necesitas:")
        print("   1. Servidor: smtp.gmail.com")
        print("   2. Contraseña de aplicación (16 caracteres)")
        print("   3. Generar en: https://myaccount.google.com/apppasswords")
        
        print("\n🔧 CONFIGURACIÓN RECOMENDADA PARA GMAIL:")
        print("   Si info@relaticpanama.org es Gmail, usa esta configuración:")
        print("   - Servidor: smtp.gmail.com")
        print("   - Puerto: 587")
        print("   - TLS: True")
        print("   - Usuario: info@relaticpanama.org")
        print("   - Contraseña: [Contraseña de aplicación de 16 caracteres]")
        print("   - Remitente: info@relaticpanama.org")
        
        print("\n📝 OPCIONES:")
        print("   1. Si es Gmail: Configurar con contraseña de aplicación")
        print("   2. Si es Office 365: Verificar contraseña actual")
        
        print("\n🔍 PARA VERIFICAR:")
        print("   - Intenta iniciar sesión en https://mail.google.com con info@relaticpanama.org")
        print("   - Si funciona: Es Gmail → Necesitas contraseña de aplicación")
        print("   - Si no funciona: Es Office 365 → Usa contraseña normal")
        
        print("\n" + "=" * 60)
        
        # Preguntar si quiere configurar para Gmail
        respuesta = input("\n¿Quieres configurar para Gmail ahora? (s/n): ").strip().lower()
        
        if respuesta == 's':
            print("\n📧 Configurando para Gmail...")
            
            # Desactivar todas
            EmailConfig.query.update({'is_active': False})
            
            # Actualizar configuración
            config.mail_server = 'smtp.gmail.com'
            config.mail_port = 587
            config.mail_use_tls = True
            config.mail_use_ssl = False
            config.mail_username = 'info@relaticpanama.org'
            config.mail_default_sender = 'info@relaticpanama.org'
            config.use_environment_variables = False
            config.is_active = True
            config.updated_at = datetime.utcnow()
            
            print("\n🔐 Ingresa la CONTRASEÑA DE APLICACIÓN (16 caracteres):")
            print("   (Genera una en: https://myaccount.google.com/apppasswords)")
            print("   (Debe ser exactamente 16 caracteres, sin espacios)")
            new_password = input("   Contraseña: ").strip().replace(' ', '')
            
            if new_password and len(new_password) == 16:
                config.mail_password = new_password
                try:
                    db.session.commit()
                    print("\n✅ Configuración actualizada para Gmail")
                    print("\n📋 CONFIGURACIÓN:")
                    print(f"   Servidor: {config.mail_server}")
                    print(f"   Usuario: {config.mail_username}")
                    print(f"   Remitente: {config.mail_default_sender}")
                    print(f"   Contraseña: {'*' * 16}")
                    print("\n💡 PRÓXIMOS PASOS:")
                    print("   1. Reinicia el servicio: sudo systemctl restart membresia-relatic.service")
                    print("   2. Prueba el envío desde /admin/email")
                except Exception as e:
                    db.session.rollback()
                    print(f"\n❌ Error: {e}")
            elif new_password:
                print(f"\n⚠️  La contraseña debe tener exactamente 16 caracteres (tiene {len(new_password)})")
                print("   Verifica que sea una contraseña de aplicación de Gmail")
            else:
                print("\n⚠️  No se ingresó contraseña. Configuración no actualizada.")
        else:
            print("\n💡 Puedes configurar manualmente desde /admin/email")

if __name__ == '__main__':
    test_both_configs()
