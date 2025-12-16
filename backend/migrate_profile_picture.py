#!/usr/bin/env python3
"""
Script para agregar la columna profile_picture a la tabla user.
"""

import sqlite3
import os
import sys

# Obtener la ruta de la base de datos
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(os.path.dirname(basedir), 'instance', 'relaticpanama.db')

if not os.path.exists(db_path):
    print(f"❌ Error: No se encontró la base de datos en {db_path}")
    sys.exit(1)

print(f"📁 Base de datos: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Verificar si la columna ya existe
    cursor.execute("PRAGMA table_info(user)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'profile_picture' in columns:
        print("✅ La columna 'profile_picture' ya existe en la tabla 'user'")
        conn.close()
        sys.exit(0)
    
    print("🔧 Agregando columna 'profile_picture' a la tabla 'user'...")
    
    # Agregar la columna profile_picture
    cursor.execute("""
        ALTER TABLE user 
        ADD COLUMN profile_picture VARCHAR(500)
    """)
    
    conn.commit()
    print("✅ Columna 'profile_picture' agregada exitosamente a la tabla 'user'")
    
    # Verificar que se agregó correctamente
    cursor.execute("PRAGMA table_info(user)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'profile_picture' in columns:
        print("✅ Verificación: La columna 'profile_picture' está presente en la tabla 'user'")
    else:
        print("❌ Error: La columna 'profile_picture' no se encontró después de agregarla")
        conn.close()
        sys.exit(1)
    
    conn.close()
    print("\n✅ Migración completada exitosamente")
    
except sqlite3.Error as e:
    print(f"❌ Error de SQLite: {e}")
    if conn:
        conn.rollback()
        conn.close()
    sys.exit(1)
except Exception as e:
    print(f"❌ Error inesperado: {e}")
    if conn:
        conn.rollback()
        conn.close()
    sys.exit(1)


