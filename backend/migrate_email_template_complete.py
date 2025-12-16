#!/usr/bin/env python3
"""
Script para migrar completamente la tabla email_template al nuevo esquema.
Agrega todas las columnas faltantes según el modelo EmailTemplate.
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
    
    # Verificar columnas actuales
    cursor.execute("PRAGMA table_info(email_template)")
    existing_cols = [column[1] for column in cursor.fetchall()]
    
    print(f"📋 Columnas actuales: {', '.join(existing_cols)}")
    
    # Columnas que deben existir según el modelo EmailTemplate
    required_columns = {
        'template_key': 'VARCHAR(100)',
        'html_content': 'TEXT',
        'text_content': 'TEXT',
        'is_custom': 'BOOLEAN DEFAULT 0',
        'variables': 'TEXT'
    }
    
    added_columns = []
    
    for col_name, col_type in required_columns.items():
        if col_name not in existing_cols:
            print(f"🔧 Agregando columna '{col_name}' ({col_type})...")
            try:
                cursor.execute(f"ALTER TABLE email_template ADD COLUMN {col_name} {col_type}")
                added_columns.append(col_name)
                print(f"   ✅ Columna '{col_name}' agregada")
            except sqlite3.Error as e:
                print(f"   ⚠️ Error al agregar '{col_name}': {e}")
        else:
            print(f"   ✅ Columna '{col_name}' ya existe")
    
    if added_columns:
        conn.commit()
        print(f"\n✅ Migración completada. Columnas agregadas: {', '.join(added_columns)}")
    else:
        print("\n✅ Todas las columnas requeridas ya existen")
    
    # Verificar columnas finales
    cursor.execute("PRAGMA table_info(email_template)")
    final_cols = [column[1] for column in cursor.fetchall()]
    print(f"\n📋 Columnas finales: {', '.join(final_cols)}")
    
    # Si existe 'body' pero no 'html_content', migrar datos
    if 'body' in existing_cols and 'html_content' in final_cols:
        cursor.execute("SELECT COUNT(*) FROM email_template WHERE html_content IS NULL AND body IS NOT NULL")
        count = cursor.fetchone()[0]
        if count > 0:
            print(f"\n🔄 Migrando datos de 'body' a 'html_content' ({count} registros)...")
            cursor.execute("UPDATE email_template SET html_content = body WHERE html_content IS NULL AND body IS NOT NULL")
            conn.commit()
            print("   ✅ Datos migrados")
    
    # Si existe 'is_active' pero no 'is_custom', migrar datos
    if 'is_active' in existing_cols and 'is_custom' in final_cols:
        cursor.execute("SELECT COUNT(*) FROM email_template WHERE is_custom IS NULL")
        count = cursor.fetchone()[0]
        if count > 0:
            print(f"\n🔄 Migrando datos de 'is_active' a 'is_custom' ({count} registros)...")
            cursor.execute("UPDATE email_template SET is_custom = is_active WHERE is_custom IS NULL")
            conn.commit()
            print("   ✅ Datos migrados")
    
    conn.close()
    print("\n✅ Migración completa finalizada exitosamente")
    
except sqlite3.Error as e:
    print(f"❌ Error de SQLite: {e}")
    if conn:
        conn.rollback()
        conn.close()
    sys.exit(1)
except Exception as e:
    print(f"❌ Error inesperado: {e}")
    import traceback
    traceback.print_exc()
    if conn:
        conn.rollback()
        conn.close()
    sys.exit(1)


