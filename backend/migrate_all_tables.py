#!/usr/bin/env python3
"""
Script completo de migración para todas las tablas
Agrega todas las columnas faltantes según los modelos actuales
"""

import sqlite3
import os
from datetime import datetime

def migrate_user_table(db_path):
    """Migrar tabla User"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('PRAGMA table_info(user)')
        existing_cols = [row[1] for row in cursor.fetchall()]
        
        new_fields = {
            'country': 'VARCHAR(100)',
            'cedula_or_passport': 'VARCHAR(50)',
            'tags': 'TEXT',
            'user_group': 'VARCHAR(50)',
            'email_verified': 'BOOLEAN DEFAULT 0',
            'email_verification_token': 'VARCHAR(255)',
            'email_verification_token_expires': 'DATETIME',
            'email_verification_sent_at': 'DATETIME',
        }
        
        added = []
        for field_name, field_type in new_fields.items():
            if field_name not in existing_cols:
                try:
                    cursor.execute(f'ALTER TABLE user ADD COLUMN {field_name} {field_type}')
                    added.append(field_name)
                    print(f'   ✅ user.{field_name} agregada')
                except Exception as e:
                    print(f'   ⚠️ Error con user.{field_name}: {e}')
        
        conn.commit()
        return len(added)
    except Exception as e:
        print(f'   ❌ Error migrando tabla user: {e}')
        conn.rollback()
        return 0
    finally:
        conn.close()

def migrate_payment_table(db_path):
    """Migrar tabla Payment"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('PRAGMA table_info(payment)')
        existing_cols = [row[1] for row in cursor.fetchall()]
        
        new_fields = {
            'ocr_data': 'TEXT',
            'ocr_status': 'VARCHAR(20) DEFAULT "pending"',
            'ocr_verified_at': 'DATETIME',
            'admin_notes': 'TEXT',
            'payment_method': 'VARCHAR(50)',
            'payment_reference': 'VARCHAR(200)',
            'payment_url': 'VARCHAR(500)',
            'receipt_url': 'VARCHAR(500)',
            'receipt_filename': 'VARCHAR(255)',
            'payment_metadata': 'TEXT',
            'paid_at': 'DATETIME',
        }
        
        added = []
        for field_name, field_type in new_fields.items():
            if field_name not in existing_cols:
                try:
                    cursor.execute(f'ALTER TABLE payment ADD COLUMN {field_name} {field_type}')
                    added.append(field_name)
                    print(f'   ✅ payment.{field_name} agregada')
                except Exception as e:
                    print(f'   ⚠️ Error con payment.{field_name}: {e}')
        
        conn.commit()
        return len(added)
    except Exception as e:
        print(f'   ❌ Error migrando tabla payment: {e}')
        conn.rollback()
        return 0
    finally:
        conn.close()

def migrate_discount_table(db_path):
    """Migrar tabla Discount"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('PRAGMA table_info(discount)')
        existing_cols = [row[1] for row in cursor.fetchall()]
        
        new_fields = {
            'is_master': 'BOOLEAN DEFAULT 0',
        }
        
        added = []
        for field_name, field_type in new_fields.items():
            if field_name not in existing_cols:
                try:
                    cursor.execute(f'ALTER TABLE discount ADD COLUMN {field_name} {field_type}')
                    added.append(field_name)
                    print(f'   ✅ discount.{field_name} agregada')
                except Exception as e:
                    print(f'   ⚠️ Error con discount.{field_name}: {e}')
        
        conn.commit()
        return len(added)
    except Exception as e:
        print(f'   ❌ Error migrando tabla discount: {e}')
        conn.rollback()
        return 0
    finally:
        conn.close()

def migrate_all():
    """Ejecutar todas las migraciones"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(os.path.dirname(script_dir), 'instance', 'relaticpanama.db')
    
    if not os.path.exists(db_path):
        print(f"⚠️ Base de datos no encontrada en: {db_path}")
        print("   La base de datos se creará automáticamente al ejecutar la aplicación.")
        return
    
    print(f"🔄 Iniciando migración completa...")
    print(f"📁 Base de datos: {db_path}\n")
    
    total_added = 0
    
    print("📋 Migrando tabla 'user'...")
    total_added += migrate_user_table(db_path)
    
    print("\n📋 Migrando tabla 'payment'...")
    total_added += migrate_payment_table(db_path)
    
    print("\n📋 Migrando tabla 'discount'...")
    total_added += migrate_discount_table(db_path)
    
    print(f"\n✅ Migración completada. Total de columnas agregadas: {total_added}")

if __name__ == '__main__':
    migrate_all()

