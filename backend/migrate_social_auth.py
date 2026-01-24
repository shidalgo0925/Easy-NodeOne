#!/usr/bin/env python3
"""
Migración para agregar tabla SocialAuth para login social
"""

import sys
import os

# Agregar el directorio del backend al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from datetime import datetime

def migrate():
    """Agregar tabla SocialAuth si no existe"""
    with app.app_context():
        try:
            # Verificar si la tabla ya existe
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            if 'social_auth' in existing_tables:
                print("✅ La tabla 'social_auth' ya existe. No se necesita migración.")
                return
            
            # Crear la tabla
            print("📝 Creando tabla 'social_auth'...")
            db.create_all()
            
            print("✅ Migración completada exitosamente.")
            print("   - Tabla 'social_auth' creada")
            
        except Exception as e:
            print(f"❌ Error en la migración: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == '__main__':
    migrate()






