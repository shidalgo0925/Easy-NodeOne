#!/usr/bin/env python3
"""
Migración: Agregar campos de recuperación de contraseña a la tabla user
"""

import sys
import os

# Agregar el directorio del backend al path
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db
from sqlalchemy import inspect

def migrate_password_reset_fields():
    """Agregar columnas de recuperación de contraseña a la tabla user"""
    with app.app_context():
        inspector = inspect(db.engine)
        
        # Verificar si la tabla user existe
        if 'user' not in inspector.get_table_names():
            print("❌ La tabla 'user' no existe en la base de datos")
            return False
        
        # Obtener columnas actuales
        columns = [col['name'] for col in inspector.get_columns('user')]
        print(f"📋 Columnas actuales en user: {', '.join(columns)}")
        
        # Columnas a agregar
        columns_to_add = {
            'password_reset_token': 'VARCHAR(100)',
            'password_reset_token_expires': 'DATETIME',
            'password_reset_sent_at': 'DATETIME'
        }
        
        # Agregar columnas faltantes
        added_columns = []
        with db.engine.connect() as conn:
            for col_name, col_type in columns_to_add.items():
                if col_name not in columns:
                    print(f"🔧 Agregando columna '{col_name}' ({col_type}) a la tabla user...")
                    try:
                        # SQLite no soporta ALTER TABLE ADD COLUMN con restricciones UNIQUE directamente
                        # Primero agregamos la columna sin UNIQUE
                        if 'UNIQUE' in col_type:
                            # Para password_reset_token, lo agregamos sin UNIQUE primero
                            sql = f"ALTER TABLE user ADD COLUMN {col_name} VARCHAR(100)"
                        else:
                            sql = f"ALTER TABLE user ADD COLUMN {col_name} {col_type}"
                        
                        conn.execute(db.text(sql))
                        conn.commit()
                        added_columns.append(col_name)
                        print(f"✅ Columna '{col_name}' agregada exitosamente")
                    except Exception as e:
                        print(f"⚠️ Error agregando columna '{col_name}': {e}")
                        conn.rollback()
                else:
                    print(f"ℹ️ Columna '{col_name}' ya existe, omitiendo")
        
        if added_columns:
            print(f"\n✅ Migración completada. Columnas agregadas: {', '.join(added_columns)}")
        else:
            print("\n✅ Todas las columnas ya existen. No se requieren cambios.")
        
        return True

if __name__ == '__main__':
    print("🚀 Iniciando migración: Campos de recuperación de contraseña\n")
    success = migrate_password_reset_fields()
    if success:
        print("\n✅ Migración completada exitosamente")
        sys.exit(0)
    else:
        print("\n❌ Migración falló")
        sys.exit(1)

