#!/usr/bin/env python3
"""
Alinea NotificationSettings.enabled → CommunicationRule.enabled donde el código de evento
coincide con notification_type (misma fila en communication_event).

Uso:
    python3 backend/migrate_sync_notification_settings_to_rules.py

Idempotente: solo actualiza reglas cuyo enabled difiere del legacy.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app  # noqa: E402


def main():
    with app.app_context():
        from nodeone.services.notification_settings_sync import sync_all_notification_settings_to_rules

        m = sync_all_notification_settings_to_rules()
        if not m:
            print('✅ sync notification_settings → communication_rule: nada que actualizar')
        else:
            print('✅ sync notification_settings → communication_rule:')
            for k, v in sorted(m.items()):
                print(f'   {k}: {v} regla(s)')


if __name__ == '__main__':
    main()
