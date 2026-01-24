#!/usr/bin/env python3
"""
Script de migración para crear la tabla de anuncios (announcements)
"""

import sys
import os

# Agregar el directorio backend al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from datetime import datetime

def create_announcements_table():
    """Crear la tabla de anuncios si no existe"""
    with app.app_context():
        try:
            # Verificar si la tabla ya existe
            inspector = db.inspect(db.engine)
            if 'announcement' in inspector.get_table_names():
                print("✅ La tabla 'announcement' ya existe.")
                return
            
            # Crear la tabla usando el modelo
            from app import Announcement
            db.create_all()
            
            print("✅ Tabla 'announcement' creada exitosamente.")
            
            # Verificar que se creó correctamente
            inspector = db.inspect(db.engine)
            if 'announcement' in inspector.get_table_names():
                columns = inspector.get_columns('announcement')
                print(f"✅ Tabla creada con {len(columns)} columnas:")
                for col in columns:
                    print(f"   - {col['name']} ({col['type']})")
            else:
                print("❌ Error: La tabla no se creó correctamente.")
                
        except Exception as e:
            print(f"❌ Error creando la tabla: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

if __name__ == '__main__':
    print("🚀 Iniciando migración de tabla 'announcement'...")
    create_announcements_table()
    print("✅ Migración completada.")

