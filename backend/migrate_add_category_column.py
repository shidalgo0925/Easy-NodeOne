#!/usr/bin/env python3
"""
Script para agregar la columna category_id a la tabla service
y crear la tabla service_category si no existe.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db
from sqlalchemy import text

def migrate_database():
    """Agregar columna category_id a service y crear tabla service_category"""
    with app.app_context():
        print("=" * 80)
        print("MIGRACIÓN: Agregar columna category_id a tabla service")
        print("=" * 80)
        print()
        
        try:
            # Verificar si la columna category_id ya existe
            inspector = db.inspect(db.engine)
            service_columns = [col['name'] for col in inspector.get_columns('service')]
            
            if 'category_id' in service_columns:
                print("✓ La columna category_id ya existe en la tabla service")
            else:
                print("1. Agregando columna category_id a la tabla service...")
                # SQLite no soporta ALTER TABLE ADD COLUMN con FOREIGN KEY directamente
                # Necesitamos agregar la columna primero y luego la constraint
                db.session.execute(text("""
                    ALTER TABLE service 
                    ADD COLUMN category_id INTEGER
                """))
                db.session.commit()
                print("   ✓ Columna category_id agregada")
            
            # Verificar si la tabla service_category existe
            tables = inspector.get_table_names()
            
            if 'service_category' in tables:
                print("✓ La tabla service_category ya existe")
            else:
                print("2. Creando tabla service_category...")
                # Crear la tabla usando el modelo
                from app import ServiceCategory
                ServiceCategory.__table__.create(db.engine, checkfirst=True)
                print("   ✓ Tabla service_category creada")
            
            print()
            print("=" * 80)
            print("✅ Migración completada exitosamente")
            print("=" * 80)
            print()
            print("Próximo paso: Ejecutar migrate_service_categories.py para crear categorías")
            
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error durante la migración: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True

if __name__ == '__main__':
    migrate_database()
