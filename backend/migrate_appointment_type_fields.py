#!/usr/bin/env python3
"""
Migración: Agregar campos nuevos a AppointmentType inspirados en Odoo
- location
- assign_method
- min_schedule_hours
- max_schedule_days
- allow_guests
- payment_required
- service_id

Y crear tabla AppointmentReminder
"""

import sys
import os

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from sqlalchemy import text

def migrate():
    """Ejecutar migración"""
    with app.app_context():
        try:
            print("🔄 Iniciando migración de AppointmentType...")
            
            # Verificar si las columnas ya existen
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('appointment_type')]
            
            # Campos a agregar
            new_columns = {
                'location': "ALTER TABLE appointment_type ADD COLUMN location VARCHAR(20) DEFAULT 'virtual'",
                'assign_method': "ALTER TABLE appointment_type ADD COLUMN assign_method VARCHAR(20) DEFAULT 'automatic'",
                'min_schedule_hours': "ALTER TABLE appointment_type ADD COLUMN min_schedule_hours INTEGER DEFAULT 24",
                'max_schedule_days': "ALTER TABLE appointment_type ADD COLUMN max_schedule_days INTEGER DEFAULT 90",
                'allow_guests': "ALTER TABLE appointment_type ADD COLUMN allow_guests BOOLEAN DEFAULT 0",
                'payment_required': "ALTER TABLE appointment_type ADD COLUMN payment_required BOOLEAN DEFAULT 1",
                'service_id': "ALTER TABLE appointment_type ADD COLUMN service_id INTEGER REFERENCES service(id)"
            }
            
            # Agregar columnas que no existen
            for col_name, sql in new_columns.items():
                if col_name not in columns:
                    print(f"  ➕ Agregando columna: {col_name}")
                    db.session.execute(text(sql))
                    db.session.commit()
                else:
                    print(f"  ✓ Columna {col_name} ya existe")
            
            # Crear tabla AppointmentReminder si no existe
            tables = inspector.get_table_names()
            if 'appointment_reminder' not in tables:
                print("  ➕ Creando tabla appointment_reminder...")
                db.session.execute(text("""
                    CREATE TABLE appointment_reminder (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        appointment_type_id INTEGER NOT NULL,
                        reminder_type VARCHAR(20) DEFAULT 'email',
                        interval_value INTEGER NOT NULL,
                        interval_unit VARCHAR(10) DEFAULT 'hours',
                        message_template TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (appointment_type_id) REFERENCES appointment_type(id)
                    )
                """))
                db.session.commit()
                print("  ✅ Tabla appointment_reminder creada")
            else:
                print("  ✓ Tabla appointment_reminder ya existe")
            
            # Agregar campos nuevos a Appointment si no existen
            appointment_columns = [col['name'] for col in inspector.get_columns('appointment')]
            appointment_new_columns = {
                'guest_emails': "ALTER TABLE appointment ADD COLUMN guest_emails TEXT",
                'location_address': "ALTER TABLE appointment ADD COLUMN location_address VARCHAR(500)",
                'internal_notes': "ALTER TABLE appointment ADD COLUMN internal_notes TEXT"
            }
            
            for col_name, sql in appointment_new_columns.items():
                if col_name not in appointment_columns:
                    print(f"  ➕ Agregando columna a appointment: {col_name}")
                    db.session.execute(text(sql))
                    db.session.commit()
                else:
                    print(f"  ✓ Columna appointment.{col_name} ya existe")
            
            print("✅ Migración completada exitosamente")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error en migración: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    migrate()
