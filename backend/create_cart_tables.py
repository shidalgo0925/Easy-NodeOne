#!/usr/bin/env python3
"""
Script para crear las tablas del carrito directamente en la base de datos
"""

import sqlite3
import os

def create_cart_tables():
    """Crear tablas del carrito en la base de datos SQLite"""
    
    # Buscar la base de datos
    db_paths = [
        'relaticpanama.db',
        'instance/relaticpanama.db',
        '../relaticpanama.db',
        '../instance/relaticpanama.db'
    ]
    
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("❌ No se encontró la base de datos")
        return False
    
    print(f"📦 Conectando a la base de datos: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si las tablas ya existen
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cart'")
        cart_exists = cursor.fetchone() is not None
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cart_item'")
        cart_item_exists = cursor.fetchone() is not None
        
        if cart_exists and cart_item_exists:
            print("✅ Las tablas del carrito ya existen")
            conn.close()
            return True
        
        # Crear tabla cart
        if not cart_exists:
            print("📦 Creando tabla 'cart'...")
            cursor.execute("""
                CREATE TABLE cart (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    created_at DATETIME,
                    updated_at DATETIME,
                    FOREIGN KEY(user_id) REFERENCES user (id),
                    UNIQUE(user_id)
                )
            """)
            print("✅ Tabla 'cart' creada")
        
        # Crear tabla cart_item
        if not cart_item_exists:
            print("📦 Creando tabla 'cart_item'...")
            cursor.execute("""
                CREATE TABLE cart_item (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    cart_id INTEGER NOT NULL,
                    product_type VARCHAR(50) NOT NULL,
                    product_id INTEGER NOT NULL,
                    product_name VARCHAR(200) NOT NULL,
                    product_description TEXT,
                    unit_price FLOAT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    metadata TEXT,
                    created_at DATETIME,
                    updated_at DATETIME,
                    FOREIGN KEY(cart_id) REFERENCES cart (id)
                )
            """)
            print("✅ Tabla 'cart_item' creada")
        
        # Crear índices para mejorar el rendimiento
        print("📦 Creando índices...")
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cart_user_id ON cart(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cart_item_cart_id ON cart_item(cart_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cart_item_product ON cart_item(product_type, product_id)")
            print("✅ Índices creados")
        except Exception as e:
            print(f"⚠️ Advertencia al crear índices: {e}")
        
        conn.commit()
        conn.close()
        
        print("\n✅ Migración completada exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = create_cart_tables()
    exit(0 if success else 1)






