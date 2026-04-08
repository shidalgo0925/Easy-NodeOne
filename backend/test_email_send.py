#!/usr/bin/env python3
"""
Script para probar el envío de email directamente (EmailService).
Uso: python test_email_send.py [--org-id ID]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as ap


def main():
    parser = argparse.ArgumentParser(description='Prueba EmailService + SMTP por org')
    parser.add_argument('--org-id', type=int, default=None, help='ID organización; por defecto org del runtime')
    args = parser.parse_args()
    oid = int(args.org_id) if args.org_id is not None else int(ap.default_organization_id())

    print('=' * 70)
    print('PRUEBA DE ENVÍO DE EMAIL')
    print(f'  organization_id: {oid}')
    print('=' * 70)

    with ap.app.app_context():
        try:
            ok_smtp, _ = ap.apply_transactional_smtp_for_organization(oid)
            if not ok_smtp or not ap.email_service:
                print('\n❌ No hay SMTP transaccional o EmailService no disponible')
                sys.exit(1)

            print('\n✅ SMTP aplicado')
            print(f"   Servidor: {ap.app.config.get('MAIL_SERVER')}")
            print(f"   Usuario: {ap.app.config.get('MAIL_USERNAME')}")
            print(f"   Remitente: {ap.app.config.get('MAIL_DEFAULT_SENDER')}")

            print('\n📧 Intentando enviar email de prueba...')
            print('   Destinatario: info@relaticpanama.org')

            success = ap.email_service.send_email(
                subject='[PRUEBA] Test de Email - RelaticPanama',
                recipients=['info@relaticpanama.org'],
                html_content='<h1>Email de Prueba</h1><p>Este es un email de prueba para verificar la configuración SMTP.</p>',
                email_type='test',
                recipient_name='Prueba',
            )

            if success:
                print('\n✅ Email enviado exitosamente')
            else:
                print('\n❌ Error al enviar email (ver logs)')

            print('\n📋 Verificando logs de email...')
            from app import EmailLog

            recent_logs = EmailLog.query.order_by(EmailLog.created_at.desc()).limit(3).all()
            if recent_logs:
                for log in recent_logs:
                    status_icon = '✅' if log.status == 'sent' else '❌'
                    print(
                        f'   {status_icon} [{log.created_at.strftime("%H:%M:%S")}] '
                        f'{log.recipient_email} - {log.status}'
                    )
                    if log.error_message:
                        print(f'      Error: {log.error_message}')
            else:
                print('   ⚠️  No hay logs recientes')

            print('\n' + '=' * 70)
            sys.exit(0 if success else 1)
        finally:
            ap.apply_email_config_from_db()


if __name__ == '__main__':
    main()
