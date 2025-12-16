#!/usr/bin/env python3
"""
Script para agregar la columna template_key a la tabla email_template.
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
    cursor.execute("PRAGMA table_info(email_template)")
    columns = [column[1] for column in cursor.fetchall()]
    
    print(f"📋 Columnas actuales en email_template: {', '.join(columns)}")
    
    if 'template_key' in columns:
        print("✅ La columna 'template_key' ya existe en la tabla 'email_template'")
        conn.close()
        sys.exit(0)
    
    print("🔧 Agregando columna 'template_key' a la tabla 'email_template'...")
    
    # Agregar la columna template_key
    cursor.execute("""
        ALTER TABLE email_template 
        ADD COLUMN template_key VARCHAR(100)
    """)
    
    conn.commit()
    print("✅ Columna 'template_key' agregada exitosamente a la tabla 'email_template'")
    
    # Verificar que se agregó correctamente
    cursor.execute("PRAGMA table_info(email_template)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'template_key' in columns:
        print("✅ Verificación: La columna 'template_key' está presente en la tabla 'email_template'")
    else:
        print("❌ Error: La columna 'template_key' no se encontró después de agregarla")
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


