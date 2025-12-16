#!/usr/bin/env python3
"""
Script para crear la tabla de notificaciones en la base de datos
"""

import sqlite3
import os
from datetime import datetime

db_path = 'relaticpanama.db'

if not os.path.exists(db_path):
    print(f"❌ No se encontró la base de datos: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Verificar si la tabla ya existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notification'")
    if cursor.fetchone():
        print("✅ La tabla 'notification' ya existe")
    else:
        print("➕ Creando tabla 'notification'...")
        cursor.execute("""
            CREATE TABLE notification (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_id INTEGER,
                notification_type VARCHAR(50) NOT NULL,
                title VARCHAR(200) NOT NULL,
                message TEXT NOT NULL,
                is_read BOOLEAN DEFAULT 0,
                email_sent BOOLEAN DEFAULT 0,
                email_sent_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user (id),
                FOREIGN KEY (event_id) REFERENCES event (id)
            )
        """)
        print("✅ Tabla 'notification' creada exitosamente")
    
    conn.commit()
    print("\n✅ Migración completada exitosamente")
    
except Exception as e:
    conn.rollback()
    print(f"\n❌ Error durante la migración: {e}")
    raise
finally:
    conn.close()
















