#!/usr/bin/env python3
"""
Script de migración para crear la tabla media_config
Ejecutar desde el directorio backend: python migrate_media_config.py
"""

import sqlite3
import os
from pathlib import Path

# Ruta a la base de datos
db_path = Path(__file__).parent / 'instance' / 'membership_legacy.db'

if not db_path.exists():
    print(f"❌ Error: No se encontró la base de datos en {db_path}")
    print("   Asegúrate de que la aplicación se haya ejecutado al menos una vez.")
    exit(1)

print(f"📦 Conectando a la base de datos: {db_path}")

try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Verificar si la tabla ya existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='media_config'")
    table_exists = cursor.fetchone() is not None
    
    if table_exists:
        print("   ℹ️  La tabla 'media_config' ya existe")
        # Verificar columnas
        cursor.execute("PRAGMA table_info(media_config)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"   Columnas existentes: {', '.join(columns)}")
    else:
        print("➕ Creando tabla 'media_config'...")
        cursor.execute("""
            CREATE TABLE media_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                procedure_key VARCHAR(100) NOT NULL,
                step_number INTEGER NOT NULL,
                video_url VARCHAR(500),
                audio_url VARCHAR(500),
                step_title VARCHAR(200),
                description TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(procedure_key, step_number)
            )
        """)
        conn.commit()
        print("   ✅ Tabla 'media_config' creada exitosamente")
        
        # Crear índices para mejor rendimiento
        print("➕ Creando índices...")
        cursor.execute("CREATE INDEX idx_media_config_procedure ON media_config(procedure_key)")
        cursor.execute("CREATE INDEX idx_media_config_active ON media_config(is_active)")
        conn.commit()
        print("   ✅ Índices creados")
    
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

