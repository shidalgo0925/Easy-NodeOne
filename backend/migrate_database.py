#!/usr/bin/env python3
"""
Script de migración para agregar nuevas columnas a las tablas existentes
"""
import sqlite3
import os
from pathlib import Path

# Ruta a la base de datos
db_path = Path(__file__).parent / 'instance' / 'membership_legacy.db'

if not db_path.exists():
    # Si no existe en instance, buscar en el directorio actual
    db_path = Path(__file__).parent / 'membership_legacy.db'

if not db_path.exists():
    print(f"❌ Base de datos no encontrada en: {db_path}")
    exit(1)

print(f"📦 Conectando a la base de datos: {db_path}")

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

try:
    # Verificar si la columna current_uses existe en discount
    cursor.execute("PRAGMA table_info(discount)")
    columns = [col[1] for col in cursor.fetchall()]
    
    migrations = []
    
    # Migración 1: Agregar current_uses a discount
    if 'current_uses' not in columns:
        print("➕ Agregando columna 'current_uses' a la tabla 'discount'...")
        cursor.execute("ALTER TABLE discount ADD COLUMN current_uses INTEGER DEFAULT 0")
        migrations.append("current_uses en discount")
    
    # Verificar columnas de Event
    cursor.execute("PRAGMA table_info(event)")
    event_columns = [col[1] for col in cursor.fetchall()]
    
    # Migración 2: Agregar campos nuevos a Event
    new_event_fields = {
        'venue': 'VARCHAR(200)',
        'university': 'VARCHAR(200)',
        'certificate_template': 'VARCHAR(500)',
        'kahoot_enabled': 'BOOLEAN DEFAULT 0',
        'kahoot_link': 'VARCHAR(500)',
        'kahoot_required': 'BOOLEAN DEFAULT 0',
        'step_1_event_completed': 'BOOLEAN DEFAULT 0',
        'step_2_description_completed': 'BOOLEAN DEFAULT 0',
        'step_3_publicity_completed': 'BOOLEAN DEFAULT 0',
        'step_4_certificate_completed': 'BOOLEAN DEFAULT 0',
        'step_5_kahoot_completed': 'BOOLEAN DEFAULT 0',
        'generates_poster': 'BOOLEAN DEFAULT 0',
        'generates_magazine': 'BOOLEAN DEFAULT 0',
        'generates_book': 'BOOLEAN DEFAULT 0',
        'registered_count': 'INTEGER DEFAULT 0'
    }
    
    for field, field_type in new_event_fields.items():
        if field not in event_columns:
            print(f"➕ Agregando columna '{field}' a la tabla 'event'...")
            cursor.execute(f"ALTER TABLE event ADD COLUMN {field} {field_type}")
            migrations.append(f"{field} en event")
    
    # Verificar si las nuevas tablas existen
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [row[0] for row in cursor.fetchall()]
    
    # Las nuevas tablas se crearán automáticamente cuando se ejecute db.create_all()
    # pero verificamos si necesitamos crear alguna manualmente
    
    conn.commit()
    
    if migrations:
        print(f"\n✅ Migraciones aplicadas exitosamente:")
        for migration in migrations:
            print(f"   - {migration}")
    else:
        print("\n✅ No se requieren migraciones. La base de datos está actualizada.")
    
    print("\n📝 Nota: Las nuevas tablas (event_participant, event_speaker, etc.)")
    print("   se crearán automáticamente cuando se ejecute db.create_all()")
    
except sqlite3.Error as e:
    conn.rollback()
    print(f"\n❌ Error durante la migración: {e}")
    exit(1)
finally:
    conn.close()

print("\n✨ Migración completada!")

















