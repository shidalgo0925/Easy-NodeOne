#!/usr/bin/env python3
"""
Migración para crear la tabla history_transaction
Ejecutar: python migrate_history_transactions.py
"""

import sys
import os

# Agregar el directorio del backend al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from sqlalchemy import text

def create_history_transaction_table():
    """Crear tabla history_transaction con índices"""
    
    with app.app_context():
        try:
            # Verificar si la tabla ya existe
            inspector = db.inspect(db.engine)
            if 'history_transaction' in inspector.get_table_names():
                print("⚠️  La tabla history_transaction ya existe")
                return
            
            print("📋 Creando tabla history_transaction...")
            
            # Crear tabla
            db.engine.execute(text("""
                CREATE TABLE history_transaction (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid VARCHAR(36) NOT NULL UNIQUE,
                    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    transaction_type VARCHAR(50) NOT NULL,
                    actor_type VARCHAR(20) NOT NULL,
                    actor_id INTEGER,
                    owner_user_id INTEGER,
                    visibility VARCHAR(20) NOT NULL DEFAULT 'both',
                    action VARCHAR(200) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'success',
                    context_app VARCHAR(100),
                    context_screen VARCHAR(100),
                    context_module VARCHAR(100),
                    payload TEXT,
                    result TEXT,
                    transaction_metadata TEXT,
                    FOREIGN KEY (actor_id) REFERENCES user(id),
                    FOREIGN KEY (owner_user_id) REFERENCES user(id)
                )
            """))
            
            print("📋 Creando índices...")
            
            # Crear índices
            db.engine.execute(text("""
                CREATE INDEX idx_history_timestamp ON history_transaction(timestamp)
            """))
            
            db.engine.execute(text("""
                CREATE INDEX idx_history_owner_user ON history_transaction(owner_user_id)
            """))
            
            db.engine.execute(text("""
                CREATE INDEX idx_history_type ON history_transaction(transaction_type)
            """))
            
            db.engine.execute(text("""
                CREATE INDEX idx_history_status ON history_transaction(status)
            """))
            
            db.engine.execute(text("""
                CREATE INDEX idx_history_actor ON history_transaction(actor_id)
            """))
            
            db.engine.execute(text("""
                CREATE INDEX idx_history_timestamp_owner ON history_transaction(timestamp, owner_user_id)
            """))
            
            db.session.commit()
            
            print("✅ Tabla history_transaction creada exitosamente")
            print("✅ Índices creados exitosamente")
            
        except Exception as e:
            print(f"❌ Error creando tabla: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()

if __name__ == '__main__':
    print("═══════════════════════════════════════════════════════════════")
    print("🚀 MIGRACIÓN: History Transaction")
    print("═══════════════════════════════════════════════════════════════\n")
    
    create_history_transaction_table()
    
    print("\n✅ Migración completada")
