#!/usr/bin/env python3
"""
Script de diagnóstico para verificar el sistema de mensajería.
Uso: python diagnostico_mensajeria.py [--org-id ID]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app import app, db, EmailLog, Notification, NotificationSettings, EmailConfig


def main():
    parser = argparse.ArgumentParser(description='Diagnóstico mensajería')
    parser.add_argument('--org-id', type=int, default=None, help='Tenant para EmailConfig mostrada')
    args = parser.parse_args()

    with app.app_context():
        print('=' * 60)
        print('DIAGNÓSTICO DEL SISTEMA DE MENSAJERÍA')
        if args.org_id is not None:
            print(f'  (EmailConfig org: {args.org_id})')
        print('=' * 60)

        print('\n1. REGISTROS EN EMAILLOG:')
        total_emails = EmailLog.query.count()
        print(f'   Total de emails registrados: {total_emails}')

        if total_emails > 0:
            sent = EmailLog.query.filter_by(status='sent').count()
            failed = EmailLog.query.filter_by(status='failed').count()
            print(f'   - Enviados: {sent}')
            print(f'   - Fallidos: {failed}')

            print('\n   Últimos 5 emails:')
            for email in EmailLog.query.order_by(EmailLog.created_at.desc()).limit(5).all():
                print(f'   - [{email.created_at}] {email.email_type} → {email.recipient_email} ({email.status})')
        else:
            print('   ⚠️  No hay registros en EmailLog')

        print('\n2. REGISTROS EN NOTIFICATION:')
        total_notifications = Notification.query.count()
        print(f'   Total de notificaciones: {total_notifications}')

        if total_notifications > 0:
            sent_notifications = Notification.query.filter_by(email_sent=True).count()
            not_sent = Notification.query.filter_by(email_sent=False).count()
            print(f'   - Con email enviado: {sent_notifications}')
            print(f'   - Sin email enviado: {not_sent}')

            print('\n   Últimas 5 notificaciones:')
            for notif in Notification.query.order_by(Notification.created_at.desc()).limit(5).all():
                email_status = '✅ Enviado' if notif.email_sent else '❌ No enviado'
                print(f'   - [{notif.created_at}] {notif.notification_type}: {notif.title} ({email_status})')
        else:
            print('   ⚠️  No hay notificaciones')

        print('\n3. CONFIGURACIÓN DE EMAIL:')
        email_config = EmailConfig.get_active_config(organization_id=args.org_id)
        if email_config:
            print(f'   ✅ Configuración encontrada (ID: {email_config.id})')
            print(f'   - organization_id: {getattr(email_config, "organization_id", None)}')
            print(f'   - Servidor: {email_config.mail_server}')
            print(f'   - Puerto: {email_config.mail_port}')
            print(f'   - Usa variables de entorno: {email_config.use_environment_variables}')
            print(f'   - Activo: {email_config.is_active}')
        else:
            print('   ⚠️  No hay configuración de email activa (para este criterio)')

        print('\n4. CONFIGURACIÓN DE NOTIFICACIONES:')
        event_reg = NotificationSettings.query.filter_by(notification_type='event_registration').first()
        event_conf = NotificationSettings.query.filter_by(notification_type='event_confirmation').first()

        if event_reg:
            print(f"   - event_registration: {'✅ Habilitada' if event_reg.enabled else '❌ Deshabilitada'}")
        else:
            print('   - event_registration: ⚠️  No configurada (por defecto habilitada)')

        if event_conf:
            print(f"   - event_confirmation: {'✅ Habilitada' if event_conf.enabled else '❌ Deshabilitada'}")
        else:
            print('   - event_confirmation: ⚠️  No configurada (por defecto habilitada)')

        print('\n5. CONFIGURACIÓN DE FLASK-MAIL (app.mail):')
        try:
            from app import mail as app_mail

            if app_mail is not None and hasattr(app_mail, 'app') and app_mail.app:
                print('   ✅ Flask-Mail está inicializado en app')
                print(f"   - MAIL_SERVER: {app.config.get('MAIL_SERVER', 'No configurado')}")
                print(f"   - MAIL_PORT: {app.config.get('MAIL_PORT', 'No configurado')}")
                print(f"   - MAIL_USERNAME: {app.config.get('MAIL_USERNAME', 'No configurado')}")
            else:
                print('   ⚠️  app.mail no está inicializado (normal fuera de request con SMTP por org)')
        except Exception as e:
            print(f'   ❌ Error verificando Flask-Mail: {e}')

        print('\n6. ANÁLISIS:')
        if total_notifications > 0 and total_emails == 0:
            print('   ⚠️  PROBLEMA DETECTADO:')
            print('   - Hay notificaciones creadas pero NO hay registros en EmailLog')
            print('   - Esto indica que los emails no se están enviando o no se están registrando')
            print('\n   Posibles causas:')
            print('   1. El sistema de email no está configurado correctamente')
            print('   2. Hay errores al enviar emails que no se están capturando')
            print('   3. La función log_email_sent() no se está llamando')
            print('   4. Hay un problema con el commit de la base de datos')
        elif total_notifications == 0:
            print('   ⚠️  No hay notificaciones creadas')
            print('   - Verifica que los eventos se estén registrando correctamente')
        elif total_emails > 0:
            print('   ✅ El sistema parece estar funcionando')
            print('   - Hay registros en EmailLog')

        print('\n' + '=' * 60)


if __name__ == '__main__':
    main()
