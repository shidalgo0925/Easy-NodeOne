#!/usr/bin/env python3
"""
Migración: Crear tabla daily_service_availability
Ejecutar desde el directorio backend con: python3 migrate_daily_service_availability.py
"""

import sys
import os

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from datetime import datetime

def migrate():
    """Crear la tabla daily_service_availability"""
    with app.app_context():
        print("=" * 60)
        print("Migración: Crear tabla daily_service_availability")
        print("=" * 60)
        
        try:
            # Verificar si la tabla ya existe
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            if 'daily_service_availability' in existing_tables:
                print("✅ La tabla 'daily_service_availability' ya existe.")
                print("   No es necesario crear la tabla nuevamente.")
                return
            
            print("\n📋 Creando tabla daily_service_availability...")
            
            # Crear la tabla usando SQL directo para mayor control
            create_table_sql = """
            CREATE TABLE daily_service_availability (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                advisor_id INTEGER NOT NULL,
                appointment_type_id INTEGER NOT NULL,
                start_time TIME NOT NULL,
                end_time TIME NOT NULL,
                timezone VARCHAR(50) DEFAULT 'America/Panama',
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                FOREIGN KEY(advisor_id) REFERENCES advisor (id),
                FOREIGN KEY(appointment_type_id) REFERENCES appointment_type (id),
                FOREIGN KEY(created_by) REFERENCES user (id),
                CHECK (end_time > start_time)
            )
            """
            
            db.engine.execute(create_table_sql)
            
            # Crear índices
            print("📊 Creando índices...")
            db.engine.execute("""
                CREATE INDEX idx_daily_availability 
                ON daily_service_availability (date, advisor_id, appointment_type_id)
            """)
            
            db.engine.execute("""
                CREATE INDEX idx_daily_availability_date 
                ON daily_service_availability (date)
            """)
            
            db.session.commit()
            
            print("\n✅ Migración completada exitosamente!")
            print("   - Tabla 'daily_service_availability' creada")
            print("   - Índices creados")
            print("   - Restricciones aplicadas")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error durante la migración: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    migrate()
