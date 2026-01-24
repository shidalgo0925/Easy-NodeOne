#!/usr/bin/env python3
"""
Script de migración para agregar campos de billing a subscription
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from sqlalchemy import text

def migrate():
    """Ejecutar migraciones"""
    with app.app_context():
        print("🔄 Agregando campos de billing a subscription...")
        
        try:
            # Agregar next_billing_date si no existe
            try:
                db.session.execute(text("""
                    ALTER TABLE subscription 
                    ADD COLUMN next_billing_date DATETIME
                """))
                print("   ✅ Campo next_billing_date agregado")
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print("   ⚠️ Campo next_billing_date ya existe")
                else:
                    raise
            
            db.session.commit()
            print("\n✅ Migración completada exitosamente!")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error en la migración: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True

if __name__ == '__main__':
    migrate()






