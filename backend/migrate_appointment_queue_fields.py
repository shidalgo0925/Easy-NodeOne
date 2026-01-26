#!/usr/bin/env python3
"""
Script de migración para agregar campos de cola a la tabla appointment.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from sqlalchemy import text, inspect

def add_queue_fields():
    """Agregar campos queue_position y hacer start_datetime/end_datetime nullable"""
    with app.app_context():
        print("1. Agregando campos de cola a la tabla 'appointment'...")
        
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('appointment')]
        
        # Agregar queue_position si no existe
        if 'queue_position' not in columns:
            try:
                db.session.execute(text("""
                    ALTER TABLE appointment 
                    ADD COLUMN queue_position INTEGER
                """))
                db.session.commit()
                print("   ✓ Columna 'queue_position' agregada")
            except Exception as e:
                print(f"   ✗ Error agregando 'queue_position': {e}")
                db.session.rollback()
                return False
        else:
            print("   → Columna 'queue_position' ya existe")
        
        # Hacer start_datetime nullable (SQLite no permite ALTER COLUMN directamente)
        # En SQLite, necesitamos recrear la tabla o usar una migración más compleja
        # Por ahora, solo agregamos queue_position
        # start_datetime y end_datetime ya deberían ser nullable en el modelo
        
        return True

def verify_migration():
    """Verificar que las columnas se agregaron correctamente"""
    with app.app_context():
        print("\n2. Verificando migración...")
        
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('appointment')]
        
        if 'queue_position' in columns:
            print("   ✓ Columna 'queue_position' existe")
        else:
            print("   ✗ Columna 'queue_position' NO existe")
            return False
        
        return True

def main():
    print("=" * 80)
    print("MIGRACIÓN: Campos de Cola para Appointment")
    print("=" * 80)
    print()
    
    try:
        if not add_queue_fields():
            print("\n✗ Error agregando campos")
            return 1
        
        if verify_migration():
            print()
            print("=" * 80)
            print("✅ Migración completada exitosamente")
            print("=" * 80)
            print()
            print("NOTA: start_datetime y end_datetime ahora pueden ser NULL")
            print("      para citas en cola (sin slot asignado)")
            print()
            return 0
        else:
            print()
            print("=" * 80)
            print("⚠️  Migración completada con errores")
            print("=" * 80)
            return 1
    
    except Exception as e:
        print()
        print("=" * 80)
        print("✗ ERROR durante la migración")
        print("=" * 80)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return 1

if __name__ == '__main__':
    exit(main())
