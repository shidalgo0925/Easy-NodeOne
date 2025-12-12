#!/usr/bin/env python3
"""
Script de migración para crear las tablas de códigos de descuento
Ejecutar desde el directorio backend: python migrate_discount_codes.py
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
    
    # 1. Agregar campo is_master a la tabla discount
    print("\n1️⃣ Verificando campo 'is_master' en tabla 'discount'...")
    cursor.execute("PRAGMA table_info(discount)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'is_master' not in columns:
        print("   ➕ Agregando columna 'is_master' a la tabla 'discount'...")
        cursor.execute("ALTER TABLE discount ADD COLUMN is_master BOOLEAN DEFAULT 0")
        print("   ✅ Columna 'is_master' agregada exitosamente")
    else:
        print("   ℹ️  La columna 'is_master' ya existe")
    
    # 2. Agregar campos a la tabla cart
    print("\n2️⃣ Verificando campos de descuento en tabla 'cart'...")
    cursor.execute("PRAGMA table_info(cart)")
    cart_columns = [column[1] for column in cursor.fetchall()]
    
    if 'discount_code_id' not in cart_columns:
        print("   ➕ Agregando columna 'discount_code_id' a la tabla 'cart'...")
        cursor.execute("ALTER TABLE cart ADD COLUMN discount_code_id INTEGER")
        print("   ✅ Columna 'discount_code_id' agregada exitosamente")
    else:
        print("   ℹ️  La columna 'discount_code_id' ya existe")
    
    if 'master_discount_id' not in cart_columns:
        print("   ➕ Agregando columna 'master_discount_id' a la tabla 'cart'...")
        cursor.execute("ALTER TABLE cart ADD COLUMN master_discount_id INTEGER")
        print("   ✅ Columna 'master_discount_id' agregada exitosamente")
    else:
        print("   ℹ️  La columna 'master_discount_id' ya existe")
    
    # 3. Crear tabla discount_code
    print("\n3️⃣ Verificando tabla 'discount_code'...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='discount_code'")
    table_exists = cursor.fetchone() is not None
    
    if not table_exists:
        print("   ➕ Creando tabla 'discount_code'...")
        cursor.execute("""
            CREATE TABLE discount_code (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                discount_type VARCHAR(20) DEFAULT 'percentage',
                value FLOAT NOT NULL,
                applies_to VARCHAR(50) DEFAULT 'all',
                event_ids TEXT,
                start_date DATETIME,
                end_date DATETIME,
                max_uses_total INTEGER,
                max_uses_per_user INTEGER DEFAULT 1,
                current_uses INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_by INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES user(id)
            )
        """)
        cursor.execute("CREATE INDEX idx_discount_code_code ON discount_code(code)")
        print("   ✅ Tabla 'discount_code' creada exitosamente")
    else:
        print("   ℹ️  La tabla 'discount_code' ya existe")
    
    # 4. Crear tabla discount_application
    print("\n4️⃣ Verificando tabla 'discount_application'...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='discount_application'")
    table_exists = cursor.fetchone() is not None
    
    if not table_exists:
        print("   ➕ Creando tabla 'discount_application'...")
        cursor.execute("""
            CREATE TABLE discount_application (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discount_code_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                payment_id INTEGER,
                cart_id INTEGER,
                original_amount FLOAT NOT NULL,
                discount_amount FLOAT NOT NULL,
                final_amount FLOAT NOT NULL,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (discount_code_id) REFERENCES discount_code(id),
                FOREIGN KEY (user_id) REFERENCES user(id),
                FOREIGN KEY (payment_id) REFERENCES payment(id),
                FOREIGN KEY (cart_id) REFERENCES cart(id)
            )
        """)
        cursor.execute("CREATE INDEX idx_discount_application_code ON discount_application(discount_code_id)")
        cursor.execute("CREATE INDEX idx_discount_application_user ON discount_application(user_id)")
        print("   ✅ Tabla 'discount_application' creada exitosamente")
    else:
        print("   ℹ️  La tabla 'discount_application' ya existe")
    
    # Commit cambios
    conn.commit()
    print("\n✅ Migración completada exitosamente!")
    
except sqlite3.Error as e:
    print(f"\n❌ Error de SQLite: {e}")
    conn.rollback()
    exit(1)
except Exception as e:
    print(f"\n❌ Error inesperado: {e}")
    import traceback
    traceback.print_exc()
    conn.rollback()
    exit(1)
finally:
    conn.close()

