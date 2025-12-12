#!/usr/bin/env python3
"""
Script de migración para crear la tabla PaymentConfig
Ejecutar desde el directorio backend: python migrate_payment_config.py
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
    
    # Verificar si la tabla ya existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payment_config'")
    table_exists = cursor.fetchone() is not None
    
    if table_exists:
        print("   ℹ️  La tabla 'payment_config' ya existe")
        # Verificar columnas
        cursor.execute("PRAGMA table_info(payment_config)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"   Columnas existentes: {', '.join(columns)}")
    else:
        print("➕ Creando tabla 'payment_config'...")
        cursor.execute("""
            CREATE TABLE payment_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_secret_key VARCHAR(500),
                stripe_publishable_key VARCHAR(500),
                stripe_webhook_secret VARCHAR(500),
                paypal_client_id VARCHAR(500),
                paypal_client_secret VARCHAR(500),
                paypal_mode VARCHAR(20) DEFAULT 'sandbox',
                paypal_return_url VARCHAR(500),
                paypal_cancel_url VARCHAR(500),
                banco_general_merchant_id VARCHAR(200),
                banco_general_api_key VARCHAR(500),
                banco_general_shared_secret VARCHAR(500),
                banco_general_api_url VARCHAR(500) DEFAULT 'https://api.cybersource.com',
                yappy_api_key VARCHAR(500),
                yappy_merchant_id VARCHAR(200),
                yappy_api_url VARCHAR(500) DEFAULT 'https://api.yappy.im',
                use_environment_variables BOOLEAN DEFAULT 1,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        print("   ✅ Tabla 'payment_config' creada exitosamente")
    
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

