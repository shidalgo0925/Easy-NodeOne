#!/usr/bin/env python3
"""
Prueba directa de envío de email con SMTP transaccional por organización.
Uso: python test_email_direct.py [--org-id ID]
"""

import argparse
import os
import sys

venv_python = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'venv', 'bin', 'python3'
)
if os.path.exists(venv_python) and __file__ != venv_python:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as ap
from flask_mail import Message


def main():
    parser = argparse.ArgumentParser(description='Prueba directa SMTP')
    parser.add_argument('--org-id', type=int, default=None, help='ID organización; por defecto org del runtime')
    args = parser.parse_args()
    oid = int(args.org_id) if args.org_id is not None else int(ap.default_organization_id())

    print('=' * 60)
    print('PRUEBA DIRECTA DE ENVÍO DE EMAIL')
    print(f'  organization_id: {oid}')
    print('=' * 60)

    with ap.app.app_context():
        try:
            ok_smtp, _ = ap.apply_transactional_smtp_for_organization(oid)
            if not ok_smtp or not ap.mail:
                print('\n❌ No hay configuración activa / SMTP no disponible')
                return False

            print('\n✅ Configuración aplicada')
            print(f"   Servidor: {ap.app.config.get('MAIL_SERVER')}")
            print(f"   Puerto: {ap.app.config.get('MAIL_PORT')}")
            print(f"   TLS: {ap.app.config.get('MAIL_USE_TLS')}")
            print(f"   Usuario: {ap.app.config.get('MAIL_USERNAME')}")
            print(f"   Remitente: {ap.app.config.get('MAIL_DEFAULT_SENDER')}")
            pwd = ap.app.config.get('MAIL_PASSWORD') or ''
            print(f"   Contraseña: {'*' * 16 if pwd else '(NO CONFIGURADA)'}")
            print(f'   Longitud: {len(pwd)} caracteres')

            test_email = input('\n📬 Ingresa el email de prueba: ').strip()
            if not test_email:
                print('❌ No se ingresó email')
                return False

            print(f'\n📤 Enviando correo de prueba a {test_email}...')

            msg = Message(
                subject='[Prueba] Test Email - Easy NodeOne',
                recipients=[test_email],
                html="""
                <h2>Correo de Prueba</h2>
                <p>Este es un correo de prueba para verificar que la configuración SMTP está funcionando correctamente.</p>
                <p>Si recibes este correo, significa que la configuración es correcta.</p>
                <p>Saludos,<br>Equipo</p>
                """,
            )

            ap.mail.send(msg)
            print('\n✅ Correo enviado exitosamente')
            print(f'   Verifica tu bandeja de entrada (y spam) en: {test_email}')
            return True

        except Exception as e:
            error_msg = str(e)
            print(f'\n❌ Error al enviar correo: {error_msg}')

            print('\n💡 ANÁLISIS DEL ERROR:')
            if '535' in error_msg and 'badcredentials' in error_msg.lower():
                print('   - Error 535: Usuario o contraseña incorrectos')
                print('   - Posibles causas:')
                print('     1. La contraseña de aplicación no es correcta')
                print('     2. La contraseña de aplicación fue revocada')
                print('     3. El usuario no es correcto')
                print('     4. La contraseña tiene espacios o caracteres incorrectos')
                print('\n   SOLUCIÓN:')
                print('   1. Verifica que la contraseña de aplicación sea correcta')
                print('   2. Genera una nueva contraseña de aplicación si es necesario')
                print('   3. Asegúrate de que no tenga espacios')
            elif 'application-specific password' in error_msg.lower():
                print('   - Gmail requiere contraseña de aplicación')
                print('   - Genera una en: https://myaccount.google.com/apppasswords')
            else:
                print(f'   - Error: {error_msg}')

            return False
        finally:
            ap.apply_email_config_from_db()


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
