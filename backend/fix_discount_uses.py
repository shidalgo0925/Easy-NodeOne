#!/usr/bin/env python3
"""
Script para corregir la columna 'uses' en la tabla discount.
El modelo usa 'current_uses' pero la base de datos puede tener 'uses'.
"""

import sqlite3
import os

db_path = 'membership_legacy.db'

if not os.path.exists(db_path):
    print(f"❌ No se encontró la base de datos: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Obtener información de las columnas
    cursor.execute("PRAGMA table_info(discount)")
    columns = {row[1]: row for row in cursor.fetchall()}
    
    print("📋 Columnas actuales en la tabla 'discount':")
    for col_name in columns.keys():
        print(f"  - {col_name}")
    
    # Verificar si existe 'uses' y 'current_uses'
    has_uses = 'uses' in columns
    has_current_uses = 'current_uses' in columns
    
    if has_uses and not has_current_uses:
        print("\n🔄 La tabla tiene 'uses' pero no 'current_uses'")
        print("   Agregando columna 'current_uses' y copiando datos de 'uses'...")
        
        # Agregar columna current_uses
        cursor.execute("ALTER TABLE discount ADD COLUMN current_uses INTEGER DEFAULT 0")
        
        # Copiar datos de 'uses' a 'current_uses'
        cursor.execute("UPDATE discount SET current_uses = COALESCE(uses, 0) WHERE current_uses IS NULL")
        
        # Hacer que 'uses' sea nullable (si es posible) o simplemente dejarlo
        # SQLite no permite cambiar NOT NULL directamente, pero podemos trabajar con ambos campos
        print("✅ Columna 'current_uses' agregada y datos copiados")
        print("   Nota: La columna 'uses' permanece en la tabla pero el modelo usa 'current_uses'")
        
    elif not has_current_uses:
        print("\n➕ Agregando columna 'current_uses'...")
        cursor.execute("ALTER TABLE discount ADD COLUMN current_uses INTEGER DEFAULT 0")
        print("✅ Columna 'current_uses' agregada exitosamente")
        
    else:
        print("\n✅ La tabla ya tiene la columna 'current_uses'")
    
    # Verificar si 'uses' tiene NOT NULL y necesitamos hacerla nullable
    if has_uses:
        print("\n⚠️  La tabla tiene una columna 'uses' que puede causar conflictos")
        print("   El modelo usa 'current_uses'. Considera eliminar 'uses' manualmente si no se usa.")
    
    conn.commit()
    print("\n✅ Migración completada exitosamente")
    
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("\n✅ La columna 'current_uses' ya existe")
    else:
        conn.rollback()
        print(f"\n❌ Error durante la migración: {e}")
        raise
except Exception as e:
    conn.rollback()
    print(f"\n❌ Error durante la migración: {e}")
    raise
finally:
    conn.close()
