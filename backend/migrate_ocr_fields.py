#!/usr/bin/env python3
"""
Script de migración para agregar campos OCR al modelo Payment
"""

import sqlite3
import os
from datetime import datetime

def migrate_payment_table():
    """Agregar campos OCR a la tabla Payment si no existen"""
    db_path = os.path.join(os.path.dirname(__file__), 'relaticpanama.db')
    
    if not os.path.exists(db_path):
        print(f"⚠️ Base de datos no encontrada en: {db_path}")
        print("   La base de datos se creará automáticamente al ejecutar la aplicación.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Verificar qué columnas existen
        cursor.execute("PRAGMA table_info(payment)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        print("📋 Columnas existentes en Payment:", existing_columns)
        
        # Campos a agregar
        new_fields = {
            'ocr_data': 'TEXT',
            'ocr_status': 'VARCHAR(20) DEFAULT "pending"',
            'ocr_verified_at': 'DATETIME',
            'admin_notes': 'TEXT'
        }
        
        added_fields = []
        for field_name, field_type in new_fields.items():
            if field_name not in existing_columns:
                try:
                    alter_sql = f"ALTER TABLE payment ADD COLUMN {field_name} {field_type}"
                    cursor.execute(alter_sql)
                    added_fields.append(field_name)
                    print(f"✅ Campo '{field_name}' agregado exitosamente")
                except sqlite3.OperationalError as e:
                    print(f"⚠️ Error agregando campo '{field_name}': {e}")
            else:
                print(f"ℹ️ Campo '{field_name}' ya existe")
        
        conn.commit()
        
        if added_fields:
            print(f"\n✅ Migración completada. Campos agregados: {', '.join(added_fields)}")
        else:
            print("\n✅ Todos los campos OCR ya existen en la base de datos.")
        
    except Exception as e:
        print(f"❌ Error en migración: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    print("🔄 Iniciando migración de campos OCR...")
    migrate_payment_table()
    print("✅ Migración finalizada.")

