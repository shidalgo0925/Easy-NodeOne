#!/usr/bin/env python3
"""
Prueba directa de envío de email con la configuración actual
"""

import sys
import os

# Usar el venv del proyecto si está disponible
venv_python = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'venv', 'bin', 'python3')
if os.path.exists(venv_python) and __file__ != venv_python:
    # Si no estamos ejecutando desde el venv, sugerir usarlo
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, EmailConfig

# Intentar importar flask_mail, si no está disponible, usar el de app
try:
    from flask_mail import Mail, Message
except ImportError:
    # Si no está disponible, usar el del módulo app
    from app import Mail, Message
    if Mail is None:
        print("❌ flask_mail no está disponible. Usa el venv del proyecto:")
        print("   /home/relaticpanama2025/projects/membresia-relatic/venv/bin/python3 test_email_direct.py")
        sys.exit(1)

def test_email_direct():
    """Probar envío de email directamente"""
    print("=" * 60)
    print("PRUEBA DIRECTA DE ENVÍO DE EMAIL")
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
        print(f"   Longitud: {len(app.config.get('MAIL_PASSWORD', ''))} caracteres")
        
        # Email de prueba
        test_email = input("\n📬 Ingresa el email de prueba: ").strip()
        
        if not test_email:
            print("❌ No se ingresó email")
            return False
        
        try:
            print(f"\n📤 Enviando correo de prueba a {test_email}...")
            
            msg = Message(
                subject='[Prueba] Test Email - RelaticPanama',
                recipients=[test_email],
                html="""
                <h2>Correo de Prueba</h2>
                <p>Este es un correo de prueba para verificar que la configuración SMTP está funcionando correctamente.</p>
                <p>Si recibes este correo, significa que la configuración es correcta.</p>
                <p><strong>Remitente:</strong> relaticpanama2025@gmail.com</p>
                <p>Saludos,<br>Equipo RelaticPanama</p>
                """
            )
            
            mail.send(msg)
            print("\n✅ Correo enviado exitosamente")
            print(f"   Verifica tu bandeja de entrada (y spam) en: {test_email}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"\n❌ Error al enviar correo: {error_msg}")
            
            print("\n💡 ANÁLISIS DEL ERROR:")
            if '535' in error_msg and 'badcredentials' in error_msg.lower():
                print("   - Error 535: Usuario o contraseña incorrectos")
                print("   - Posibles causas:")
                print("     1. La contraseña de aplicación no es correcta")
                print("     2. La contraseña de aplicación fue revocada")
                print("     3. El usuario no es correcto")
                print("     4. La contraseña tiene espacios o caracteres incorrectos")
                print("\n   SOLUCIÓN:")
                print("   1. Verifica que la contraseña de aplicación sea correcta")
                print("   2. Genera una nueva contraseña de aplicación si es necesario")
                print("   3. Asegúrate de que no tenga espacios")
            elif 'application-specific password' in error_msg.lower():
                print("   - Gmail requiere contraseña de aplicación")
                print("   - Genera una en: https://myaccount.google.com/apppasswords")
            else:
                print(f"   - Error: {error_msg}")
            
            return False
        
        print("\n" + "=" * 60)

if __name__ == '__main__':
    test_email_direct()
