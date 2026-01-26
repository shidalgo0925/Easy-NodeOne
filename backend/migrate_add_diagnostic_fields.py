#!/usr/bin/env python3
"""
Script de migración para agregar las columnas de cita de diagnóstico
a las tablas service y appointment en la base de datos.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from sqlalchemy import text, inspect

def add_service_columns():
    """Agregar columnas requires_diagnostic_appointment y diagnostic_appointment_type_id a la tabla service"""
    with app.app_context():
        print("1. Agregando columnas a la tabla 'service'...")
        
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('service')]
        
        # Agregar requires_diagnostic_appointment si no existe
        if 'requires_diagnostic_appointment' not in columns:
            try:
                db.session.execute(text("""
                    ALTER TABLE service 
                    ADD COLUMN requires_diagnostic_appointment BOOLEAN DEFAULT 0
                """))
                db.session.commit()
                print("   ✓ Columna 'requires_diagnostic_appointment' agregada")
            except Exception as e:
                print(f"   ✗ Error agregando 'requires_diagnostic_appointment': {e}")
                db.session.rollback()
                return False
        else:
            print("   → Columna 'requires_diagnostic_appointment' ya existe")
        
        # Agregar diagnostic_appointment_type_id si no existe
        if 'diagnostic_appointment_type_id' not in columns:
            try:
                db.session.execute(text("""
                    ALTER TABLE service 
                    ADD COLUMN diagnostic_appointment_type_id INTEGER
                """))
                # Agregar foreign key constraint
                try:
                    db.session.execute(text("""
                        CREATE INDEX IF NOT EXISTS ix_service_diagnostic_appointment_type_id 
                        ON service(diagnostic_appointment_type_id)
                    """))
                except:
                    pass  # El índice puede ya existir
                db.session.commit()
                print("   ✓ Columna 'diagnostic_appointment_type_id' agregada")
            except Exception as e:
                print(f"   ✗ Error agregando 'diagnostic_appointment_type_id': {e}")
                db.session.rollback()
                return False
        else:
            print("   → Columna 'diagnostic_appointment_type_id' ya existe")
        
        return True

def add_appointment_columns():
    """Agregar columnas service_id y payment_id a la tabla appointment"""
    with app.app_context():
        print("\n2. Agregando columnas a la tabla 'appointment'...")
        
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('appointment')]
        
        # Agregar service_id si no existe
        if 'service_id' not in columns:
            try:
                db.session.execute(text("""
                    ALTER TABLE appointment 
                    ADD COLUMN service_id INTEGER
                """))
                # Agregar índice
                try:
                    db.session.execute(text("""
                        CREATE INDEX IF NOT EXISTS ix_appointment_service_id 
                        ON appointment(service_id)
                    """))
                except:
                    pass
                db.session.commit()
                print("   ✓ Columna 'service_id' agregada")
            except Exception as e:
                print(f"   ✗ Error agregando 'service_id': {e}")
                db.session.rollback()
                return False
        else:
            print("   → Columna 'service_id' ya existe")
        
        # Agregar payment_id si no existe
        if 'payment_id' not in columns:
            try:
                db.session.execute(text("""
                    ALTER TABLE appointment 
                    ADD COLUMN payment_id INTEGER
                """))
                # Agregar índice
                try:
                    db.session.execute(text("""
                        CREATE INDEX IF NOT EXISTS ix_appointment_payment_id 
                        ON appointment(payment_id)
                    """))
                except:
                    pass
                db.session.commit()
                print("   ✓ Columna 'payment_id' agregada")
            except Exception as e:
                print(f"   ✗ Error agregando 'payment_id': {e}")
                db.session.rollback()
                return False
        else:
            print("   → Columna 'payment_id' ya existe")
        
        return True

def verify_migration():
    """Verificar que las columnas se agregaron correctamente"""
    with app.app_context():
        print("\n3. Verificando migración...")
        
        inspector = db.inspect(db.engine)
        
        # Verificar tabla service
        service_columns = [col['name'] for col in inspector.get_columns('service')]
        required_service_columns = ['requires_diagnostic_appointment', 'diagnostic_appointment_type_id']
        
        for col in required_service_columns:
            if col in service_columns:
                print(f"   ✓ Columna '{col}' existe en tabla 'service'")
            else:
                print(f"   ✗ Columna '{col}' NO existe en tabla 'service'")
                return False
        
        # Verificar tabla appointment
        appointment_columns = [col['name'] for col in inspector.get_columns('appointment')]
        required_appointment_columns = ['service_id', 'payment_id']
        
        for col in required_appointment_columns:
            if col in appointment_columns:
                print(f"   ✓ Columna '{col}' existe en tabla 'appointment'")
            else:
                print(f"   ✗ Columna '{col}' NO existe en tabla 'appointment'")
                return False
        
        return True

def main():
    print("=" * 80)
    print("MIGRACIÓN: Agregar Columnas de Cita de Diagnóstico")
    print("=" * 80)
    print()
    print("Este script agrega las columnas necesarias a las tablas:")
    print("  - service: requires_diagnostic_appointment, diagnostic_appointment_type_id")
    print("  - appointment: service_id, payment_id")
    print()
    
    try:
        # Paso 1: Agregar columnas a service
        if not add_service_columns():
            print("\n✗ Error agregando columnas a 'service'")
            return 1
        
        # Paso 2: Agregar columnas a appointment
        if not add_appointment_columns():
            print("\n✗ Error agregando columnas a 'appointment'")
            return 1
        
        # Paso 3: Verificar
        if verify_migration():
            print()
            print("=" * 80)
            print("✅ Migración de columnas completada exitosamente")
            print("=" * 80)
            print()
            print("PRÓXIMO PASO:")
            print("  Ejecuta: python backend/migrate_service_diagnostic_appointments.py")
            print("  (Este script marcará los servicios y creará el AppointmentType)")
            print()
            return 0
        else:
            print()
            print("=" * 80)
            print("⚠️  Migración completada con errores de verificación")
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
