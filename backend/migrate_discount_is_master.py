#!/usr/bin/env python3
"""
Script para agregar la columna is_master a la tabla discount.
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
    cursor.execute("PRAGMA table_info(discount)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'is_master' in columns:
        print("✅ La columna 'is_master' ya existe en la tabla 'discount'")
        conn.close()
        sys.exit(0)
    
    print("🔧 Agregando columna 'is_master' a la tabla 'discount'...")
    
    # Agregar la columna is_master
    cursor.execute("""
        ALTER TABLE discount 
        ADD COLUMN is_master BOOLEAN DEFAULT 0
    """)
    
    conn.commit()
    print("✅ Columna 'is_master' agregada exitosamente a la tabla 'discount'")
    
    # Verificar que se agregó correctamente
    cursor.execute("PRAGMA table_info(discount)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'is_master' in columns:
        print("✅ Verificación: La columna 'is_master' está presente en la tabla 'discount'")
    else:
        print("❌ Error: La columna 'is_master' no se encontró después de agregarla")
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


