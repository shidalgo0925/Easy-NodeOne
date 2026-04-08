#!/usr/bin/env python3
"""
Reenvía notificaciones pendientes (email_sent=False).
SMTP por organización del usuario (get_active_config con fallback).
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as ap


def retry_pending_notifications():
    with ap.app.app_context():
        try:
            pending = ap.Notification.query.filter_by(email_sent=False).all()

            if not pending:
                print('✅ No hay notificaciones pendientes de envío')
                return True

            print(f"\n{'='*70}")
            print('  🔄 REENVÍO DE NOTIFICACIONES PENDIENTES')
            print(f"{'='*70}")
            print(f'\n📊 Total: {len(pending)}\n')

            success_count = 0
            failed_count = 0
            skipped_count = 0
            last_cfg_id = None

            try:
                for notification in pending:
                    user = ap.User.query.get(notification.user_id)

                    if not user:
                        print(f'⚠️  Notificación {notification.id}: usuario no encontrado')
                        skipped_count += 1
                        continue

                    print(f'📧 {notification.id}: {notification.notification_type} → {user.email}')
                    print(f'   {notification.title}')

                    try:
                        if not ap.NotificationSettings.is_enabled(notification.notification_type):
                            print('   ⚠️  Tipo deshabilitado, omitiendo')
                            skipped_count += 1
                            continue

                        oid = int(getattr(user, 'organization_id', None) or ap.default_organization_id())
                        ok_smtp, cfg_id = ap.apply_transactional_smtp_for_organization(
                            oid, skip_if_config_id=last_cfg_id
                        )
                        if ok_smtp:
                            last_cfg_id = cfg_id

                        if not ok_smtp or not ap.email_service:
                            print('   ❌ Sin SMTP transaccional para esta organización')
                            failed_count += 1
                            continue

                        html_content = f"""
                            <h2>{notification.title}</h2>
                            <p>{notification.message}</p>
                            <p>Saludos,<br>Equipo</p>
                        """

                        sent = ap.email_service.send_email(
                            subject=notification.title,
                            recipients=[user.email],
                            html_content=html_content,
                            email_type=notification.notification_type,
                            related_entity_type='notification',
                            related_entity_id=notification.id,
                            recipient_id=user.id,
                            recipient_name=f'{user.first_name} {user.last_name}',
                        )

                        if sent:
                            notification.email_sent = True
                            notification.email_sent_at = datetime.utcnow()
                            ap.db.session.commit()
                            print('   ✅ Enviado')
                            success_count += 1
                        else:
                            print('   ❌ send_email devolvió False')
                            failed_count += 1

                    except Exception as e:
                        print(f'   ❌ Error: {e}')
                        ap.db.session.rollback()
                        failed_count += 1

                    print()

            finally:
                ap.apply_email_config_from_db()

            print(f"\n{'='*70}")
            print('  📊 RESUMEN')
            print(f"{'='*70}")
            print(f'   ✅ Enviadas: {success_count}')
            print(f'   ❌ Fallidas: {failed_count}')
            print(f'   ⚠️  Omitidas: {skipped_count}')
            print(f"{'='*70}\n")

        except Exception as e:
            ap.db.session.rollback()
            print(f'\n❌ Error: {e}')
            import traceback

            traceback.print_exc()
            return False

    return True


if __name__ == '__main__':
    print(f"\n{'='*70}")
    print('  🔄 REENVÍO DE NOTIFICACIONES PENDIENTES')
    print(f"{'='*70}")
    print(f"\n📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

    sys.exit(0 if retry_pending_notifications() else 1)
