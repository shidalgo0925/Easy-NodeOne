#!/usr/bin/env python3
"""
Script para agregar campos de roles (moderador, administrador, expositor) a la tabla event
"""

import sys
sys.path.insert(0, 'backend')

from app import app, db
import sqlite3

db_path = 'membership_legacy.db'

with app.app_context():
    # Usar conexión directa de SQLite para ALTER TABLE
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Obtener información de las columnas actuales
        cursor.execute("PRAGMA table_info(event)")
        columns = {row[1]: row for row in cursor.fetchall()}
        
        migrations = []
        
        # Agregar moderator_id si no existe
        if 'moderator_id' not in columns:
            print("➕ Agregando columna 'moderator_id' a la tabla 'event'...")
            cursor.execute("ALTER TABLE event ADD COLUMN moderator_id INTEGER REFERENCES user(id)")
            migrations.append("moderator_id")
        
        # Agregar administrator_id si no existe
        if 'administrator_id' not in columns:
            print("➕ Agregando columna 'administrator_id' a la tabla 'event'...")
            cursor.execute("ALTER TABLE event ADD COLUMN administrator_id INTEGER REFERENCES user(id)")
            migrations.append("administrator_id")
        
        # Agregar speaker_id si no existe
        if 'speaker_id' not in columns:
            print("➕ Agregando columna 'speaker_id' a la tabla 'event'...")
            cursor.execute("ALTER TABLE event ADD COLUMN speaker_id INTEGER REFERENCES user(id)")
            migrations.append("speaker_id")
        
        if migrations:
            conn.commit()
            print(f"\n✅ Columnas agregadas: {', '.join(migrations)}")
        else:
            print("\n✅ Todas las columnas ya existen")
        
        print("\n✅ Migración completada exitosamente")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error durante la migración: {e}")
        raise
    finally:
        conn.close()
