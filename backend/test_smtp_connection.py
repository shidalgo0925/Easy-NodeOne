#!/usr/bin/env python3
"""
Probar conexión SMTP directamente con Office 365
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def test_smtp_connection():
    """Probar conexión SMTP con Office 365"""
    print("=" * 60)
    print("PRUEBA DE CONEXIÓN SMTP - Office 365")
    print("=" * 60)
    
    # Configuración
    smtp_server = 'smtp.office365.com'
    smtp_port = 587
    username = 'info@example.com'
    password = 'Mariachi@0925'
    from_email = 'info@example.com'
    to_email = input("\n📬 Ingresa el email de prueba: ").strip()
    
    if not to_email:
        print("❌ No se ingresó email")
        return
    
    print(f"\n📧 Configuración:")
    print(f"   Servidor: {smtp_server}")
    print(f"   Puerto: {smtp_port}")
    print(f"   Usuario: {username}")
    print(f"   Remitente: {from_email}")
    print(f"   Destinatario: {to_email}")
    
    try:
        print("\n🔌 Conectando al servidor SMTP...")
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
        server.set_debuglevel(1)  # Mostrar detalles de la conexión
        
        print("✅ Conectado")
        print("\n🔐 Iniciando TLS...")
        server.starttls()
        print("✅ TLS iniciado")
        
        print("\n🔑 Autenticando...")
        server.login(username, password)
        print("✅ Autenticación exitosa")
        
        print("\n📤 Creando mensaje...")
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = '[Prueba] Test SMTP - Easy NodeOne'
        
        body = """
        <h2>Correo de Prueba SMTP</h2>
        <p>Este es un correo de prueba enviado directamente vía SMTP.</p>
        <p>Si recibes este correo, significa que la conexión SMTP funciona correctamente.</p>
        <p><strong>Remitente:</strong> info@example.com</p>
        <p>Saludos,<br>Equipo Easy NodeOne</p>
        """
        msg.attach(MIMEText(body, 'html'))
        
        print("📨 Enviando correo...")
        server.sendmail(from_email, [to_email], msg.as_string())
        print("✅ Correo enviado exitosamente")
        
        server.quit()
        print(f"\n✅ PRUEBA EXITOSA")
        print(f"   Verifica tu bandeja de entrada (y spam) en: {to_email}")
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"\n❌ Error de autenticación: {e}")
        print("\n💡 POSIBLES CAUSAS:")
        print("   - Contraseña incorrecta")
        print("   - SMTP AUTH no está habilitado (aunque lo veas habilitado, puede tardar en propagarse)")
        print("   - MFA activado (necesitas contraseña de aplicación)")
    except smtplib.SMTPException as e:
        print(f"\n❌ Error SMTP: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    test_smtp_connection()
