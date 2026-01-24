#!/usr/bin/env python3
"""
Script de migración para agregar el campo yappy_merchant_phone a PaymentConfig
Usa sqlite3 directamente sin importar Flask
"""

import sqlite3
import os
import sys

def find_database():
    """Encontrar la base de datos"""
    # Buscar en el directorio del backend
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(backend_dir)
    
    # Posibles ubicaciones (según app.py línea 80)
    possible_paths = [
        os.path.join(project_root, 'instance', 'relaticpanama.db'),  # Ruta según app.py
        os.path.join(backend_dir, 'instance', 'relaticpanama.db'),    # Alternativa
        os.path.join(backend_dir, 'relaticpanama.db'),
        os.path.join(project_root, 'relaticpanama.db'),
        os.path.join(os.getcwd(), 'relaticpanama.db'),
        'relaticpanama.db'
    ]
    
    # También verificar variable de entorno
    db_url = os.environ.get('DATABASE_URL', '')
    if db_url and db_url.startswith('sqlite:///'):
        db_path = db_url.replace('sqlite:///', '')
        if os.path.exists(db_path):
            return db_path
    
    # Buscar en las rutas posibles
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None

def migrate():
    """Agregar campo yappy_merchant_phone si no existe"""
    db_path = find_database()
    
    if not db_path:
        print("❌ No se encontró la base de datos relaticpanama.db")
        print("   Buscando en:")
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(backend_dir)
        print(f"   - {os.path.join(backend_dir, 'relaticpanama.db')}")
        print(f"   - {os.path.join(project_root, 'relaticpanama.db')}")
        print(f"   - {os.path.join(os.getcwd(), 'relaticpanama.db')}")
        print("\n   Por favor, ejecuta este script desde el directorio donde está la base de datos")
        return False
    
    print(f"📁 Base de datos encontrada: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(payment_config)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'yappy_merchant_phone' in columns:
            print("✅ El campo yappy_merchant_phone ya existe en payment_config")
            conn.close()
            return True
        
        # Agregar la columna
        print("🔄 Agregando campo yappy_merchant_phone a payment_config...")
        cursor.execute("""
            ALTER TABLE payment_config 
            ADD COLUMN yappy_merchant_phone VARCHAR(20)
        """)
        conn.commit()
        print("✅ Campo yappy_merchant_phone agregado exitosamente")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Error en migración: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
