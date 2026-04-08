#!/usr/bin/env python3
"""
Envío de prueba del correo de bienvenida (SMTP transaccional por org).
Uso: python send_welcome_test.py [--org-id ID] [--email DESTINO]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as ap


class MockUser:
    """Usuario de prueba para el email de bienvenida"""

    def __init__(self, email, first_name='Usuario', last_name='Prueba', organization_id=None):
        self.id = 1
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.organization_id = organization_id


def main():
    parser = argparse.ArgumentParser(description='Prueba email de bienvenida')
    parser.add_argument('--org-id', type=int, default=None, help='ID organización SMTP')
    parser.add_argument('--email', default='shidalgo0925@gmail.com', help='Destinatario de prueba')
    args = parser.parse_args()

    oid = int(args.org_id) if args.org_id is not None else int(ap.default_organization_id())

    print('=' * 70)
    print('ENVÍO DE CORREO DE BIENVENIDA DE PRUEBA')
    print(f'  organization_id: {oid}')
    print(f'  destino: {args.email}')
    print('=' * 70)

    with ap.app.app_context():
        try:
            ok_smtp, _ = ap.apply_transactional_smtp_for_organization(oid)
            if not ok_smtp or not ap.email_service:
                print('\n❌ No hay SMTP transaccional o EmailService')
                return 1

            print('\n✅ SMTP aplicado')
            print(f"   Servidor: {ap.app.config.get('MAIL_SERVER')}")
            print(f"   Usuario: {ap.app.config.get('MAIL_USERNAME')}")
            print(f"   Remitente: {ap.app.config.get('MAIL_DEFAULT_SENDER')}")

            user = MockUser(args.email, 'Usuario', 'Prueba', organization_id=oid)

            print(f'\n📧 Generando email de bienvenida para: {args.email}')

            html_content = ap.get_welcome_email(user)
            print('✅ Template de bienvenida generado correctamente')

            print('\n📤 Enviando email de bienvenida...')
            success = ap.email_service.send_email(
                subject='Bienvenido a RelaticPanama',
                recipients=[args.email],
                html_content=html_content,
                email_type='welcome',
                related_entity_type='user',
                related_entity_id=user.id,
                recipient_id=user.id,
                recipient_name=f'{user.first_name} {user.last_name}',
            )

            if success:
                print(f'\n✅ Email de bienvenida enviado exitosamente a {args.email}')
                print('\n📬 Revisa tu bandeja de entrada (y spam si no lo ves)')
            else:
                print('\n❌ Error al enviar email de bienvenida')
            return 0 if success else 1

        except Exception as e:
            print(f'\n❌ Excepción al enviar email: {e}')
            import traceback

            traceback.print_exc()
            return 1
        finally:
            ap.apply_email_config_from_db()


if __name__ == '__main__':
    sys.exit(main())
