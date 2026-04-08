#!/usr/bin/env python3
"""
Aplicar configuración de email de BD a la app en memoria (útil en dev).
Uso: python apply_email_config.py [--org-id ID]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as ap
from flask_mail import Mail


def main():
    parser = argparse.ArgumentParser(description='Aplicar EmailConfig a Flask')
    parser.add_argument('--org-id', type=int, default=None, help='Tenant; sin flag = primera activa (legado)')
    args = parser.parse_args()

    print('=' * 60)
    print('APLICANDO CONFIGURACIÓN DE EMAIL')
    if args.org_id is not None:
        print(f'  organization_id: {args.org_id}')
    print('=' * 60)

    with ap.app.app_context():
        config = ap.EmailConfig.get_active_config(organization_id=args.org_id)

        if not config:
            print('\n❌ No hay configuración activa')
            return False

        print('\n📧 Configuración encontrada:')
        print(f'   organization_id (fila): {getattr(config, "organization_id", None)}')
        print(f'   Servidor: {config.mail_server}')
        print(f'   Usuario: {config.mail_username}')
        print(f'   Remitente: {config.mail_default_sender}')

        print('\n⚙️  Aplicando configuración a Flask...')
        config.apply_to_app(ap.app)

        if Mail:
            ap.mail = Mail()
            ap.mail.init_app(ap.app)
        if ap.EmailService and ap.mail:
            ap.email_service = ap.EmailService(ap.mail)

        print('\n✅ Configuración aplicada:')
        print(f"   MAIL_SERVER: {ap.app.config.get('MAIL_SERVER')}")
        print(f"   MAIL_PORT: {ap.app.config.get('MAIL_PORT')}")
        print(f"   MAIL_USE_TLS: {ap.app.config.get('MAIL_USE_TLS')}")
        print(f"   MAIL_USERNAME: {ap.app.config.get('MAIL_USERNAME')}")
        print(
            "   MAIL_PASSWORD: "
            f"{'*' * 16 if ap.app.config.get('MAIL_PASSWORD') else '(no configurada)'}"
        )
        print(f"   MAIL_DEFAULT_SENDER: {ap.app.config.get('MAIL_DEFAULT_SENDER')}")

        print('\n💡 En producción los workers/servicio cargan la config al arrancar; reinicia si aplica.')
        print('\n' + '=' * 60)
        return True


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
