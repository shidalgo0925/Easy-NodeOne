#!/usr/bin/env python3
"""
Migración: Agregar campos de citas y abono al modelo Service.
Ejecutar con: python backend/migrate_service_appointment_fields.py
"""

import sys
import os

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from sqlalchemy import text, inspect

def check_column_exists(table_name, column_name):
    """Verifica si una columna existe en una tabla."""
    inspector = inspect(db.engine)
    existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in existing_columns

def migrate():
    """Agregar campos nuevos a la tabla service."""
    
    with app.app_context():
        try:
            print("=" * 60)
            print("MIGRACIÓN: Campos de Citas y Abono en Service")
            print("=" * 60)
            print()
            
            # Verificar que la tabla service existe
            inspector = inspect(db.engine)
            if 'service' not in inspector.get_table_names():
                print("❌ Error: La tabla 'service' no existe.")
                return False
            
            print("✅ Tabla 'service' encontrada.")
            print()
            
            columns_to_add = []
            
            # Verificar y agregar appointment_type_id
            if not check_column_exists('service', 'appointment_type_id'):
                print("📝 Agregando columna: appointment_type_id")
                columns_to_add.append("""
                    ALTER TABLE service 
                    ADD COLUMN appointment_type_id INTEGER 
                    REFERENCES appointment_type(id)
                """)
            else:
                print("✓ Columna 'appointment_type_id' ya existe")
            
            # Verificar y agregar requires_payment_before_appointment
            if not check_column_exists('service', 'requires_payment_before_appointment'):
                print("📝 Agregando columna: requires_payment_before_appointment")
                columns_to_add.append("""
                    ALTER TABLE service 
                    ADD COLUMN requires_payment_before_appointment BOOLEAN DEFAULT TRUE
                """)
            else:
                print("✓ Columna 'requires_payment_before_appointment' ya existe")
            
            # Verificar y agregar deposit_amount
            if not check_column_exists('service', 'deposit_amount'):
                print("📝 Agregando columna: deposit_amount")
                columns_to_add.append("""
                    ALTER TABLE service 
                    ADD COLUMN deposit_amount FLOAT
                """)
            else:
                print("✓ Columna 'deposit_amount' ya existe")
            
            # Verificar y agregar deposit_percentage
            if not check_column_exists('service', 'deposit_percentage'):
                print("📝 Agregando columna: deposit_percentage")
                columns_to_add.append("""
                    ALTER TABLE service 
                    ADD COLUMN deposit_percentage FLOAT
                """)
            else:
                print("✓ Columna 'deposit_percentage' ya existe")
            
            print()
            
            if columns_to_add:
                print("Ejecutando migración...")
                for sql in columns_to_add:
                    try:
                        db.session.execute(text(sql))
                        print("  ✅ Comando ejecutado correctamente")
                    except Exception as e:
                        print(f"  ⚠️  Error: {e}")
                        # Continuar con los demás
                
                db.session.commit()
                print()
                print("✅ Migración de columnas completada.")
            else:
                print("✅ Todas las columnas ya existen. No se requiere migración.")
            
            # Crear índices (si no existen)
            print()
            print("Verificando índices...")
            try:
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_service_appointment_type_id 
                    ON service(appointment_type_id)
                """))
                db.session.commit()
                print("✅ Índice 'ix_service_appointment_type_id' creado/verificado.")
            except Exception as e:
                print(f"⚠️  Advertencia al crear índice (puede que ya exista): {e}")
            
            print()
            print("=" * 60)
            print("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
            print("=" * 60)
            return True
        
        except Exception as e:
            db.session.rollback()
            print()
            print("=" * 60)
            print(f"❌ ERROR EN LA MIGRACIÓN: {e}")
            print("=" * 60)
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    if migrate():
        sys.exit(0)
    else:
        sys.exit(1)
