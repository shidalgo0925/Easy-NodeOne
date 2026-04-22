#!/usr/bin/env python3
"""SQLite: display_name en appointment_type; recordatorios 24h/1h en appointment."""
import os
import sqlite3


def column_exists(cursor, table, col):
    cursor.execute(f'PRAGMA table_info({table})')
    return any(r[1] == col for r in cursor.fetchall())


def main():
    db_path = os.environ.get('NODEONE_SQLITE') or os.path.join(
        os.path.dirname(__file__), '..', 'instance', 'NodeOne.db'
    )
    db_path = os.path.abspath(db_path)
    if not os.path.isfile(db_path):
        print(f'Skip: no database at {db_path}')
        return
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        if not column_exists(cur, 'appointment_type', 'display_name'):
            cur.execute('ALTER TABLE appointment_type ADD COLUMN display_name VARCHAR(200)')
            print('OK: appointment_type.display_name')
        else:
            print('Skip: appointment_type.display_name exists')
        if not column_exists(cur, 'appointment', 'reminder_24h_sent_at'):
            cur.execute('ALTER TABLE appointment ADD COLUMN reminder_24h_sent_at DATETIME')
            print('OK: appointment.reminder_24h_sent_at')
        else:
            print('Skip: reminder_24h_sent_at exists')
        if not column_exists(cur, 'appointment', 'reminder_1h_sent_at'):
            cur.execute('ALTER TABLE appointment ADD COLUMN reminder_1h_sent_at DATETIME')
            print('OK: appointment.reminder_1h_sent_at')
        else:
            print('Skip: reminder_1h_sent_at exists')
        conn.commit()
    finally:
        conn.close()


if __name__ == '__main__':
    main()
