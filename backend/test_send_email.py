#!/usr/bin/env python3
"""
Probar envío de email con la configuración transaccional del tenant.
Uso: python test_send_email.py [--org-id ID]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as ap
from flask_mail import Message


def main():
    parser = argparse.ArgumentParser(description='Prueba de envío SMTP')
    parser.add_argument(
        '--org-id',
        type=int,
        default=None,
        help='ID organización (get_active_config con fallback); por defecto org del runtime',
    )
    args = parser.parse_args()
    oid = int(args.org_id) if args.org_id is not None else int(ap.default_organization_id())

    print('=' * 60)
    print('PRUEBA DE ENVÍO DE EMAIL')
    print(f'  organization_id: {oid}')
    print('=' * 60)

    with ap.app.app_context():
        try:
            ok_smtp, _ = ap.apply_transactional_smtp_for_organization(oid)
            if not ok_smtp or not ap.mail:
                print('\n❌ No hay SMTP transaccional para esta organización')
                return False

            print('\n✅ SMTP aplicado para la organización')

            print('\n📧 CONFIGURACIÓN ACTUAL:')
            print(f"   Servidor: {ap.app.config.get('MAIL_SERVER')}")
            print(f"   Puerto: {ap.app.config.get('MAIL_PORT')}")
            print(f"   TLS: {ap.app.config.get('MAIL_USE_TLS')}")
            print(f"   Usuario: {ap.app.config.get('MAIL_USERNAME')}")
            print(f"   Remitente: {ap.app.config.get('MAIL_DEFAULT_SENDER')}")
            print(
                "   Contraseña: "
                f"{'*' * 16 if ap.app.config.get('MAIL_PASSWORD') else '(NO CONFIGURADA)'}"
            )

            test_email = input('\n📬 Ingresa el email de prueba: ').strip()
            if not test_email:
                print('❌ No se ingresó email')
                return False

            print(f'\n📤 Enviando correo de prueba a {test_email}...')

            msg = Message(
                subject='[Prueba] Configuración de Email - RelaticPanama',
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
            print(f'\n❌ Error al enviar correo: {e}')
            print('\n💡 POSIBLES CAUSAS:')
            err = str(e).lower()
            if '535' in str(e) or 'authentication' in err:
                print('   - Usuario o contraseña incorrectos')
                print('   - Verifica la contraseña en /admin/email')
            elif 'connection' in err or 'timeout' in err:
                print('   - Problema de conexión al servidor SMTP')
                print('   - Verifica que el puerto 587 esté abierto')
            else:
                print(f'   - Error: {e}')
            return False
        finally:
            ap.apply_email_config_from_db()


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
