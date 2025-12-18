#!/usr/bin/env python3
"""
Script de prueba rápida para verificar que el sistema de carrito funciona
"""

import sqlite3
import os

def test_cart_tables():
    """Verificar que las tablas del carrito existen"""
    
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
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cart'")
        cart_exists = cursor.fetchone() is not None
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cart_item'")
        cart_item_exists = cursor.fetchone() is not None
        
        conn.close()
        
        if cart_exists and cart_item_exists:
            print("✅ Tablas del carrito verificadas correctamente")
            print(f"   - cart: {'✅' if cart_exists else '❌'}")
            print(f"   - cart_item: {'✅' if cart_item_exists else '❌'}")
            return True
        else:
            print("❌ Faltan tablas del carrito")
            print(f"   - cart: {'✅' if cart_exists else '❌'}")
            print(f"   - cart_item: {'✅' if cart_item_exists else '❌'}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    success = test_cart_tables()
    exit(0 if success else 1)






