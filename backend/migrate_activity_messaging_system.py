#!/usr/bin/env python3
"""
Migración para sistema de actividades, mensajería y presencia en línea
Agrega:
- Campos de presencia al modelo User (last_seen, is_online, online_status)
- Campo metadata a ActivityLog
- Tablas: conversation, message, scheduled_activity, activity_participant
"""

import sqlite3
import os
from pathlib import Path

# Ruta a la base de datos
db_path = Path(__file__).parent.parent / 'instance' / 'relaticpanama.db'

if not db_path.exists():
    print(f"❌ Error: No se encontró la base de datos en {db_path}")
    print("   Asegúrate de que la aplicación se haya ejecutado al menos una vez.")
    exit(1)

print(f"📦 Conectando a la base de datos: {db_path}")

try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # ========== 1. AGREGAR CAMPOS DE PRESENCIA A USER ==========
    print("\n1️⃣ Agregando campos de presencia a la tabla 'user'...")
    cursor.execute("PRAGMA table_info(user)")
    user_columns = [column[1] for column in cursor.fetchall()]
    
    new_user_columns = {
        'last_seen': ("TIMESTAMP", "CURRENT_TIMESTAMP"),
        'is_online': ("BOOLEAN", "0"),
        'online_status': ("VARCHAR(20)", "'offline'")
    }
    
    for col_name, (col_type, default_value) in new_user_columns.items():
        if col_name not in user_columns:
            print(f"   ➕ Agregando columna '{col_name}'...")
            # SQLite no permite DEFAULT con funciones, agregamos sin DEFAULT
            cursor.execute(f"ALTER TABLE user ADD COLUMN {col_name} {col_type}")
            # Actualizar valores existentes
            if default_value:
                cursor.execute(f"UPDATE user SET {col_name} = {default_value} WHERE {col_name} IS NULL")
            conn.commit()
            print(f"      ✅ Columna '{col_name}' agregada")
        else:
            print(f"      ℹ️  Columna '{col_name}' ya existe")

    # ========== 2. AGREGAR CAMPO ACTIVITY_METADATA A ACTIVITY_LOG ==========
    print("\n2️⃣ Agregando campo 'activity_metadata' a la tabla 'activity_log'...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='activity_log'")
    if cursor.fetchone():
        cursor.execute("PRAGMA table_info(activity_log)")
        activity_log_columns = [column[1] for column in cursor.fetchall()]
        
        if 'activity_metadata' not in activity_log_columns:
            print("   ➕ Agregando columna 'activity_metadata'...")
            cursor.execute("ALTER TABLE activity_log ADD COLUMN activity_metadata TEXT")
            # Si existe 'metadata' antigua, migrar datos
            if 'metadata' in activity_log_columns:
                print("      🔄 Migrando datos de 'metadata' a 'activity_metadata'...")
                cursor.execute("UPDATE activity_log SET activity_metadata = metadata WHERE activity_metadata IS NULL AND metadata IS NOT NULL")
            conn.commit()
            print("      ✅ Columna 'activity_metadata' agregada")
        else:
            print("      ℹ️  Columna 'activity_metadata' ya existe")
    else:
        print("      ⚠️  Tabla 'activity_log' no existe, se creará con el modelo")

    # ========== 3. CREAR TABLA CONVERSATION ==========
    print("\n3️⃣ Creando tabla 'conversation'...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversation'")
    if not cursor.fetchone():
        print("   ➕ Creando tabla 'conversation'...")
        cursor.execute("""
            CREATE TABLE conversation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                participant1_id INTEGER NOT NULL,
                participant2_id INTEGER NOT NULL,
                last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (participant1_id) REFERENCES user(id),
                FOREIGN KEY (participant2_id) REFERENCES user(id)
            )
        """)
        cursor.execute("CREATE INDEX idx_conversation_participants ON conversation(participant1_id, participant2_id)")
        conn.commit()
        print("      ✅ Tabla 'conversation' creada")
    else:
        print("      ℹ️  Tabla 'conversation' ya existe")

    # ========== 4. CREAR TABLA MESSAGE ==========
    print("\n4️⃣ Creando tabla 'message'...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='message'")
    if not cursor.fetchone():
        print("   ➕ Creando tabla 'message'...")
        cursor.execute("""
            CREATE TABLE message (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                sender_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                is_read BOOLEAN DEFAULT 0,
                read_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversation(id) ON DELETE CASCADE,
                FOREIGN KEY (sender_id) REFERENCES user(id)
            )
        """)
        cursor.execute("CREATE INDEX idx_message_conversation ON message(conversation_id)")
        cursor.execute("CREATE INDEX idx_message_sender ON message(sender_id)")
        cursor.execute("CREATE INDEX idx_message_created ON message(created_at)")
        conn.commit()
        print("      ✅ Tabla 'message' creada")
    else:
        print("      ℹ️  Tabla 'message' ya existe")

    # ========== 5. CREAR TABLA SCHEDULED_ACTIVITY ==========
    print("\n5️⃣ Creando tabla 'scheduled_activity'...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scheduled_activity'")
    if not cursor.fetchone():
        print("   ➕ Creando tabla 'scheduled_activity'...")
        cursor.execute("""
            CREATE TABLE scheduled_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_type VARCHAR(50) NOT NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                organizer_id INTEGER NOT NULL,
                scheduled_at TIMESTAMP NOT NULL,
                duration_minutes INTEGER DEFAULT 30,
                location VARCHAR(500),
                status VARCHAR(20) DEFAULT 'scheduled',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organizer_id) REFERENCES user(id)
            )
        """)
        cursor.execute("CREATE INDEX idx_activity_organizer ON scheduled_activity(organizer_id)")
        cursor.execute("CREATE INDEX idx_activity_scheduled ON scheduled_activity(scheduled_at)")
        cursor.execute("CREATE INDEX idx_activity_status ON scheduled_activity(status)")
        conn.commit()
        print("      ✅ Tabla 'scheduled_activity' creada")
    else:
        print("      ℹ️  Tabla 'scheduled_activity' ya existe")

    # ========== 6. CREAR TABLA ACTIVITY_PARTICIPANT ==========
    print("\n6️⃣ Creando tabla 'activity_participant'...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='activity_participant'")
    if not cursor.fetchone():
        print("   ➕ Creando tabla 'activity_participant'...")
        cursor.execute("""
            CREATE TABLE activity_participant (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                joined_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (activity_id) REFERENCES scheduled_activity(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES user(id)
            )
        """)
        cursor.execute("CREATE INDEX idx_participant_activity ON activity_participant(activity_id)")
        cursor.execute("CREATE INDEX idx_participant_user ON activity_participant(user_id)")
        conn.commit()
        print("      ✅ Tabla 'activity_participant' creada")
    else:
        print("      ℹ️  Tabla 'activity_participant' ya existe")

    conn.close()
    print("\n✅ Migración completada exitosamente")

except sqlite3.Error as e:
    print(f"❌ Error de SQLite: {e}")
    if conn:
        conn.rollback()
        conn.close()
    exit(1)
except Exception as e:
    print(f"❌ Error inesperado: {e}")
    import traceback
    traceback.print_exc()
    if conn:
        conn.rollback()
        conn.close()
    exit(1)

