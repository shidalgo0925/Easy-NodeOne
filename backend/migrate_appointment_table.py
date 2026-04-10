#!/usr/bin/env python3
"""
Script para migrar la tabla appointment agregando las columnas faltantes.
"""
import sqlite3
import os

# Define the path to your SQLite database
DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'membership_legacy.db')

def add_column_if_not_exists(cursor, table_name, column_name, column_type, default_value=None):
    """Agrega una columna a una tabla si no existe."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    if column_name not in columns:
        print(f"➕ Agregando columna '{column_name}' a la tabla '{table_name}'...")
        if default_value is not None:
            if isinstance(default_value, str):
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} DEFAULT '{default_value}'")
            else:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} DEFAULT {default_value}")
        else:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        return True
    else:
        print(f"✓ Columna '{column_name}' ya existe en '{table_name}'")
        return False

def migrate_appointment_table():
    """Migra la tabla appointment agregando columnas faltantes."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print(f"📦 Conectando a la base de datos: {DB_PATH}")
    print(f"🔧 Migrando tabla 'appointment'...\n")
    
    migrated_columns = []

    # Columnas básicas de cancelación
    if add_column_if_not_exists(cursor, 'appointment', 'cancelled_by', 'VARCHAR(20)'):
        migrated_columns.append("cancelled_by")
    
    if add_column_if_not_exists(cursor, 'appointment', 'cancelled_at', 'DATETIME'):
        migrated_columns.append("cancelled_at")
    
    # Columnas de pago
    if add_column_if_not_exists(cursor, 'appointment', 'payment_method', 'VARCHAR(50)'):
        migrated_columns.append("payment_method")
    
    if add_column_if_not_exists(cursor, 'appointment', 'payment_reference', 'VARCHAR(100)'):
        migrated_columns.append("payment_reference")
    
    # Columnas de sincronización de calendario
    if add_column_if_not_exists(cursor, 'appointment', 'calendar_sync_url', 'VARCHAR(500)'):
        migrated_columns.append("calendar_sync_url")
    
    if add_column_if_not_exists(cursor, 'appointment', 'calendar_event_id', 'VARCHAR(200)'):
        migrated_columns.append("calendar_event_id")
    
    # Columnas de notificaciones
    if add_column_if_not_exists(cursor, 'appointment', 'reminder_sent', 'BOOLEAN', 0):
        migrated_columns.append("reminder_sent")
    
    if add_column_if_not_exists(cursor, 'appointment', 'reminder_sent_at', 'DATETIME'):
        migrated_columns.append("reminder_sent_at")
    
    if add_column_if_not_exists(cursor, 'appointment', 'confirmation_sent', 'BOOLEAN', 0):
        migrated_columns.append("confirmation_sent")
    
    if add_column_if_not_exists(cursor, 'appointment', 'confirmation_sent_at', 'DATETIME'):
        migrated_columns.append("confirmation_sent_at")
    
    if add_column_if_not_exists(cursor, 'appointment', 'cancellation_sent', 'BOOLEAN', 0):
        migrated_columns.append("cancellation_sent")
    
    if add_column_if_not_exists(cursor, 'appointment', 'cancellation_sent_at', 'DATETIME'):
        migrated_columns.append("cancellation_sent_at")
    
    # Columnas de reunión
    if add_column_if_not_exists(cursor, 'appointment', 'meeting_url', 'VARCHAR(500)'):
        migrated_columns.append("meeting_url")
    
    if add_column_if_not_exists(cursor, 'appointment', 'meeting_password', 'VARCHAR(100)'):
        migrated_columns.append("meeting_password")
    
    # Columnas de check-in/check-out
    if add_column_if_not_exists(cursor, 'appointment', 'check_in_time', 'DATETIME'):
        migrated_columns.append("check_in_time")
    
    if add_column_if_not_exists(cursor, 'appointment', 'check_out_time', 'DATETIME'):
        migrated_columns.append("check_out_time")
    
    # Columnas de duración y calificación
    if add_column_if_not_exists(cursor, 'appointment', 'duration_actual', 'INTEGER'):
        migrated_columns.append("duration_actual")
    
    if add_column_if_not_exists(cursor, 'appointment', 'rating', 'INTEGER'):
        migrated_columns.append("rating")
    
    if add_column_if_not_exists(cursor, 'appointment', 'rating_comment', 'TEXT'):
        migrated_columns.append("rating_comment")
    
    conn.commit()
    conn.close()
    
    if migrated_columns:
        print(f"\n✅ Migraciones aplicadas exitosamente:")
        for col in migrated_columns:
            print(f"   - {col}")
        print(f"\n📊 Total de columnas agregadas: {len(migrated_columns)}")
    else:
        print("\n✅ No se encontraron columnas nuevas para migrar.")
    
    print("\n✨ Migración completada!")

if __name__ == '__main__':
    migrate_appointment_table()

















