#!/usr/bin/env python3
"""
Probar envío de email con la configuración actual
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, EmailConfig
from flask_mail import Mail, Message

def test_send_email():
    """Probar envío de email"""
    print("=" * 60)
    print("PRUEBA DE ENVÍO DE EMAIL")
    print("=" * 60)
    
    with app.app_context():
        # Aplicar configuración desde BD
        config = EmailConfig.get_active_config()
        if config:
            config.apply_to_app(app)
            print("\n✅ Configuración aplicada desde BD")
        else:
            print("\n❌ No hay configuración activa")
            return False
        
        # Inicializar Mail
        mail = Mail(app)
        
        print("\n📧 CONFIGURACIÓN ACTUAL:")
        print(f"   Servidor: {app.config.get('MAIL_SERVER')}")
        print(f"   Puerto: {app.config.get('MAIL_PORT')}")
        print(f"   TLS: {app.config.get('MAIL_USE_TLS')}")
        print(f"   Usuario: {app.config.get('MAIL_USERNAME')}")
        print(f"   Remitente: {app.config.get('MAIL_DEFAULT_SENDER')}")
        print(f"   Contraseña: {'*' * 16 if app.config.get('MAIL_PASSWORD') else '(NO CONFIGURADA)'}")
        
        # Pedir email de prueba
        test_email = input("\n📬 Ingresa el email de prueba: ").strip()
        
        if not test_email:
            print("❌ No se ingresó email")
            return False
        
        try:
            print(f"\n📤 Enviando correo de prueba a {test_email}...")
            
            msg = Message(
                subject='[Prueba] Configuración de Email - RelaticPanama',
                recipients=[test_email],
                html="""
                <h2>Correo de Prueba</h2>
                <p>Este es un correo de prueba para verificar que la configuración SMTP está funcionando correctamente.</p>
                <p>Si recibes este correo, significa que la configuración es correcta.</p>
                <p><strong>Remitente:</strong> info@relaticpanama.org</p>
                <p>Saludos,<br>Equipo RelaticPanama</p>
                """
            )
            
            mail.send(msg)
            print("\n✅ Correo enviado exitosamente")
            print(f"   Verifica tu bandeja de entrada (y spam) en: {test_email}")
            return True
            
        except Exception as e:
            print(f"\n❌ Error al enviar correo: {e}")
            print("\n💡 POSIBLES CAUSAS:")
            if "535" in str(e) or "authentication" in str(e).lower():
                print("   - Usuario o contraseña incorrectos")
                print("   - Verifica la contraseña en /admin/email")
            elif "connection" in str(e).lower() or "timeout" in str(e).lower():
                print("   - Problema de conexión al servidor SMTP")
                print("   - Verifica que el puerto 587 esté abierto")
            else:
                print(f"   - Error: {e}")
            return False
        
        print("\n" + "=" * 60)

if __name__ == '__main__':
    test_send_email()
