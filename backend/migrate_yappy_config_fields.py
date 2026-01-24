#!/usr/bin/env python3
"""
Script de migración para agregar campos configurables de Yappy a PaymentConfig
Ejecutar desde el directorio backend: python migrate_yappy_config_fields.py
"""

import sqlite3
import os
from pathlib import Path

# Ruta a la base de datos (usar la misma lógica que app.py)
# app.py usa: os.path.join(os.path.dirname(basedir), 'instance', 'relaticpanama.db')
# donde basedir es el directorio backend, entonces el padre es el proyecto raíz
basedir = Path(__file__).parent  # backend/
db_path = basedir.parent / 'instance' / 'relaticpanama.db'  # proyecto/instance/relaticpanama.db

if not db_path.exists():
    print(f"❌ Error: No se encontró la base de datos en {db_path}")
    print("   Asegúrate de que la aplicación se haya ejecutado al menos una vez.")
    exit(1)

print(f"📦 Conectando a la base de datos: {db_path}")

try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Verificar si la tabla existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payment_config'")
    table_exists = cursor.fetchone() is not None
    
    if not table_exists:
        print("❌ Error: La tabla 'payment_config' no existe.")
        print("   Ejecuta primero: python migrate_payment_config.py")
        conn.close()
        exit(1)
    
    # Verificar columnas existentes
    cursor.execute("PRAGMA table_info(payment_config)")
    existing_columns = [column[1] for column in cursor.fetchall()]
    print(f"   Columnas existentes: {', '.join(existing_columns)}")
    
    # Campos a agregar
    new_fields = {
        'yappy_directory_name': "VARCHAR(100) DEFAULT '@multiserviciostk'",
        'yappy_qr_image_path': "VARCHAR(500) DEFAULT '/static/images/yappy-qr-multiserviciostk.png'",
        'yappy_business_name': "VARCHAR(200) DEFAULT 'MULTISERVICIOS TK'"
    }
    
    # Agregar campos que no existan
    for field_name, field_type in new_fields.items():
        if field_name not in existing_columns:
            print(f"➕ Agregando columna '{field_name}'...")
            try:
                cursor.execute(f"ALTER TABLE payment_config ADD COLUMN {field_name} {field_type}")
                conn.commit()
                print(f"   ✅ Columna '{field_name}' agregada exitosamente")
            except sqlite3.Error as e:
                print(f"   ⚠️  Error agregando '{field_name}': {e}")
                # Continuar con los demás campos
        else:
            print(f"   ℹ️  Columna '{field_name}' ya existe, omitiendo")
    
    # Actualizar registros existentes con valores por defecto si están NULL
    print("\n🔄 Actualizando registros existentes con valores por defecto...")
    cursor.execute("""
        UPDATE payment_config 
        SET yappy_directory_name = '@multiserviciostk'
        WHERE yappy_directory_name IS NULL
    """)
    cursor.execute("""
        UPDATE payment_config 
        SET yappy_qr_image_path = '/static/images/yappy-qr-multiserviciostk.png'
        WHERE yappy_qr_image_path IS NULL
    """)
    cursor.execute("""
        UPDATE payment_config 
        SET yappy_business_name = 'MULTISERVICIOS TK'
        WHERE yappy_business_name IS NULL
    """)
    conn.commit()
    print("   ✅ Registros actualizados")
    
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

