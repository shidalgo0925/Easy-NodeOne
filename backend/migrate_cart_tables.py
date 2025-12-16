#!/usr/bin/env python3
"""
Script de migración para agregar las tablas del carrito de compras
Ejecutar: python migrate_cart_tables.py
"""

import sys
import os

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db, Cart, CartItem

def migrate_cart_tables():
    """Crear las tablas del carrito si no existen"""
    with app.app_context():
        try:
            print("🔄 Iniciando migración de tablas del carrito...")
            
            # Verificar si las tablas ya existen
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            if 'cart' in existing_tables and 'cart_item' in existing_tables:
                print("✅ Las tablas del carrito ya existen")
                return
            
            # Crear las tablas
            print("📦 Creando tablas del carrito...")
            Cart.__table__.create(db.engine, checkfirst=True)
            CartItem.__table__.create(db.engine, checkfirst=True)
            
            print("✅ Tablas del carrito creadas exitosamente")
            print("   - cart")
            print("   - cart_item")
            
        except Exception as e:
            print(f"❌ Error en la migración: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

if __name__ == '__main__':
    success = migrate_cart_tables()
    if success:
        print("\n✅ Migración completada exitosamente")
        sys.exit(0)
    else:
        print("\n❌ La migración falló")
        sys.exit(1)






