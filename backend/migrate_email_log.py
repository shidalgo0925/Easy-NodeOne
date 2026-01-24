#!/usr/bin/env python3
"""
Script para crear la tabla email_log en la base de datos
"""
import sys
from pathlib import Path

# Agregar el directorio backend al path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app import app, db, EmailLog

with app.app_context():
    print("📦 Creando tabla email_log en la base de datos...")
    try:
        # Crear solo la tabla EmailLog
        EmailLog.__table__.create(db.engine, checkfirst=True)
        print("✅ Tabla email_log creada exitosamente!")
        print("\n✨ Proceso completado!")
    except Exception as e:
        print(f"❌ Error al crear la tabla: {e}")
        # Intentar con create_all como fallback
        try:
            print("\n🔄 Intentando con db.create_all()...")
            db.create_all()
            print("✅ Tablas creadas exitosamente con db.create_all()")
        except Exception as e2:
            print(f"❌ Error con db.create_all(): {e2}")
            sys.exit(1)



