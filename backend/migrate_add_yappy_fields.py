#!/usr/bin/env python3
"""
Script de migración para agregar campos yappy_transaction_id y yappy_raw_response a Payment
Estos campos permiten match automático de pagos sin depender del webhook.

Ejecutar desde el directorio backend: python migrate_add_yappy_fields.py
"""

import sqlite3
import os
from pathlib import Path

# Ruta a la base de datos (misma lógica que app.py)
backend_dir = Path(__file__).parent
project_dir = backend_dir.parent
db_path = project_dir / 'instance' / 'membership_legacy.db'

# También intentar rutas alternativas
if not db_path.exists():
    db_path = backend_dir / 'instance' / 'membership_legacy.db'

if not db_path.exists():
    print(f"❌ Error: No se encontró la base de datos en {db_path}")
    print("   Asegúrate de que la aplicación se haya ejecutado al menos una vez.")
    exit(1)

print(f"📦 Conectando a la base de datos: {db_path}")

try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Verificar columnas existentes
    cursor.execute("PRAGMA table_info(payment)")
    columns = {column[1]: column for column in cursor.fetchall()}
    
    changes_made = False
    
    # Agregar yappy_transaction_id si no existe
    if 'yappy_transaction_id' not in columns:
        print("➕ Agregando columna 'yappy_transaction_id'...")
        cursor.execute("ALTER TABLE payment ADD COLUMN yappy_transaction_id VARCHAR(200)")
        changes_made = True
        print("   ✅ Columna 'yappy_transaction_id' agregada")
        print("   📝 Esta columna guarda el código EBOWR-XXXXXXXX de Yappy (NO sobrescribe payment_reference)")
    else:
        print("   ℹ️  Columna 'yappy_transaction_id' ya existe")
    
    # Agregar yappy_raw_response si no existe
    if 'yappy_raw_response' not in columns:
        print("➕ Agregando columna 'yappy_raw_response'...")
        cursor.execute("ALTER TABLE payment ADD COLUMN yappy_raw_response TEXT")
        changes_made = True
        print("   ✅ Columna 'yappy_raw_response' agregada")
        print("   📝 Esta columna guarda la respuesta completa de Yappy API para auditoría")
    else:
        print("   ℹ️  Columna 'yappy_raw_response' ya existe")
    
    if changes_made:
        conn.commit()
        print("\n✅ Migración completada exitosamente")
        print("\n📋 Campos agregados:")
        print("   - yappy_transaction_id: Código de comprobante de Yappy (EBOWR-XXXXXXXX)")
        print("   - yappy_raw_response: Respuesta completa de Yappy API (JSON)")
        print("\n⚠️  IMPORTANTE: payment_reference (YAPPY-XXXXXXXX) NUNCA se sobrescribe")
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
    import traceback
    traceback.print_exc()
    if conn:
        conn.rollback()
        conn.close()
    exit(1)
