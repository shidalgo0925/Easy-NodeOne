#!/usr/bin/env python3
"""
Script de migración para actualizar el modelo Payment con nuevos campos
Ejecutar desde el directorio backend: python migrate_payment_model.py
"""

import sqlite3
import os
from pathlib import Path

# Ruta a la base de datos
db_path = Path(__file__).parent / 'instance' / 'membership_legacy.db'

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
    
    # Agregar payment_method si no existe
    if 'payment_method' not in columns:
        print("➕ Agregando columna 'payment_method'...")
        cursor.execute("ALTER TABLE payment ADD COLUMN payment_method VARCHAR(50) DEFAULT 'stripe'")
        # Actualizar registros existentes
        cursor.execute("UPDATE payment SET payment_method = 'stripe' WHERE payment_method IS NULL")
        changes_made = True
        print("   ✅ Columna 'payment_method' agregada")
    else:
        print("   ℹ️  Columna 'payment_method' ya existe")
    
    # Renombrar stripe_payment_intent_id a payment_reference si existe
    if 'stripe_payment_intent_id' in columns and 'payment_reference' not in columns:
        print("➕ Renombrando 'stripe_payment_intent_id' a 'payment_reference'...")
        # SQLite no soporta RENAME COLUMN directamente, necesitamos recrear la tabla
        cursor.execute("""
            CREATE TABLE payment_new (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                payment_method VARCHAR(50) DEFAULT 'stripe',
                payment_reference VARCHAR(200),
                amount INTEGER NOT NULL,
                currency VARCHAR(3) DEFAULT 'usd',
                status VARCHAR(20) DEFAULT 'pending',
                membership_type VARCHAR(50) NOT NULL,
                payment_url VARCHAR(500),
                receipt_url VARCHAR(500),
                receipt_filename VARCHAR(255),
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(id)
            )
        """)
        
        # Copiar datos
        cursor.execute("""
            INSERT INTO payment_new 
            (id, user_id, payment_method, payment_reference, amount, currency, status, membership_type, created_at, updated_at)
            SELECT 
                id, user_id, 'stripe', stripe_payment_intent_id, amount, currency, status, membership_type, created_at, updated_at
            FROM payment
        """)
        
        # Eliminar tabla antigua y renombrar nueva
        cursor.execute("DROP TABLE payment")
        cursor.execute("ALTER TABLE payment_new RENAME TO payment")
        changes_made = True
        print("   ✅ Columna renombrada y tabla actualizada")
    elif 'payment_reference' not in columns:
        print("➕ Agregando columna 'payment_reference'...")
        cursor.execute("ALTER TABLE payment ADD COLUMN payment_reference VARCHAR(200)")
        # Copiar datos de stripe_payment_intent_id si existe
        if 'stripe_payment_intent_id' in columns:
            cursor.execute("UPDATE payment SET payment_reference = stripe_payment_intent_id WHERE payment_reference IS NULL")
        changes_made = True
        print("   ✅ Columna 'payment_reference' agregada")
    else:
        print("   ℹ️  Columna 'payment_reference' ya existe")
    
    # Verificar columnas nuevamente después de renombrar
    cursor.execute("PRAGMA table_info(payment)")
    columns_after = {column[1]: column for column in cursor.fetchall()}
    
    # Agregar otras columnas nuevas
    new_columns = {
        'payment_url': 'VARCHAR(500)',
        'receipt_url': 'VARCHAR(500)',
        'receipt_filename': 'VARCHAR(255)',
        'payment_metadata': 'TEXT',  # Renombrado de 'metadata' porque es palabra reservada
        'paid_at': 'TIMESTAMP'
    }
    
    for col_name, col_type in new_columns.items():
        if col_name not in columns_after:
            print(f"➕ Agregando columna '{col_name}'...")
            try:
                cursor.execute(f"ALTER TABLE payment ADD COLUMN {col_name} {col_type}")
                changes_made = True
                print(f"   ✅ Columna '{col_name}' agregada")
            except sqlite3.OperationalError as e:
                if 'duplicate column' in str(e).lower():
                    print(f"   ℹ️  Columna '{col_name}' ya existe (ignorando error)")
                else:
                    raise
        else:
            print(f"   ℹ️  Columna '{col_name}' ya existe")
    
    if changes_made:
        conn.commit()
        print("\n✅ Migración completada exitosamente")
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

