#!/usr/bin/env python3
"""
Script de migración para agregar campos country y cedula_or_passport a la tabla User
Ejecutar desde el directorio backend: python migrate_add_user_fields.py
"""

import sqlite3
import os
from pathlib import Path

# Ruta a la base de datos
db_path = Path(__file__).parent / 'instance' / 'relaticpanama.db'

if not db_path.exists():
    print(f"❌ Error: No se encontró la base de datos en {db_path}")
    print("   Asegúrate de que la aplicación se haya ejecutado al menos una vez.")
    exit(1)

print(f"📦 Conectando a la base de datos: {db_path}")

try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Verificar si las columnas ya existen
    cursor.execute("PRAGMA table_info(user)")
    columns = [column[1] for column in cursor.fetchall()]
    
    changes_made = False
    
    # Agregar columna country si no existe
    if 'country' not in columns:
        print("➕ Agregando columna 'country'...")
        cursor.execute("ALTER TABLE user ADD COLUMN country VARCHAR(100)")
        changes_made = True
        print("   ✅ Columna 'country' agregada")
    else:
        print("   ℹ️  Columna 'country' ya existe")
    
    # Agregar columna cedula_or_passport si no existe
    if 'cedula_or_passport' not in columns:
        print("➕ Agregando columna 'cedula_or_passport'...")
        cursor.execute("ALTER TABLE user ADD COLUMN cedula_or_passport VARCHAR(20)")
        changes_made = True
        print("   ✅ Columna 'cedula_or_passport' agregada")
    else:
        print("   ℹ️  Columna 'cedula_or_passport' ya existe")
    
    if changes_made:
        conn.commit()
        print("\n✅ Migración completada exitosamente")
    else:
        print("\nℹ️  No se requirieron cambios. Las columnas ya existen.")
    
    conn.close()
    
except sqlite3.Error as e:
    print(f"❌ Error de SQLite: {e}")
    if conn:
        conn.rollback()
        conn.close()
    exit(1)
except Exception as e:
    print(f"❌ Error inesperado: {e}")
    if conn:
        conn.rollback()
        conn.close()
    exit(1)

