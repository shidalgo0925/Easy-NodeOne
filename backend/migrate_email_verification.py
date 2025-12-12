#!/usr/bin/env python3
"""
Script para migrar usuarios existentes y agregar campos de verificación de email
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User
from sqlalchemy import inspect

def migrate_email_verification():
    """Agregar columnas de verificación de email y marcar usuarios activos como verificados"""
    with app.app_context():
        print("="*70)
        print("MIGRACIÓN: VERIFICACIÓN DE EMAIL")
        print("="*70)
        
        try:
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('user')]
            
            # Verificar y agregar columnas si no existen
            columns_to_add = {
                'email_verified': ('BOOLEAN', 'False'),
                'email_verification_token': ('VARCHAR(100)', 'NULL'),
                'email_verification_token_expires': ('DATETIME', 'NULL'),
                'email_verification_sent_at': ('DATETIME', 'NULL')
            }
            
            added_columns = []
            for col_name, (col_type, default) in columns_to_add.items():
                if col_name not in columns:
                    print(f"🔧 Agregando columna '{col_name}'...")
                    try:
                        from sqlalchemy import text
                        with db.engine.connect() as conn:
                            if default == 'False':
                                sql = f"ALTER TABLE user ADD COLUMN {col_name} {col_type} DEFAULT 0"
                            elif default == 'NULL':
                                sql = f"ALTER TABLE user ADD COLUMN {col_name} {col_type}"
                            else:
                                sql = f"ALTER TABLE user ADD COLUMN {col_name} {col_type} DEFAULT {default}"
                            conn.execute(text(sql))
                            conn.commit()
                        print(f"   ✅ Columna '{col_name}' agregada")
                        added_columns.append(col_name)
                    except Exception as e:
                        print(f"   ⚠️ Error agregando columna '{col_name}': {e}")
                else:
                    print(f"   ✅ Columna '{col_name}' ya existe")
            
            if added_columns:
                print(f"\n✅ Migración de columnas completada: {len(added_columns)} columnas agregadas")
            else:
                print("\n✅ Todas las columnas ya existen")
            
            # Marcar usuarios activos existentes como verificados (período de gracia)
            print("\n📋 Verificando usuarios existentes...")
            all_users = User.query.all()
            verified_count = 0
            
            for user in all_users:
                # Marcar usuarios existentes como verificados (período de gracia)
                if user.email_verified is None or user.email_verified == False:
                    user.email_verified = True  # Marcar como verificados por defecto
                    verified_count += 1
            
            if verified_count > 0:
                db.session.commit()
                print(f"✅ {verified_count} usuario(s) existente(s) marcado(s) como verificados (período de gracia)")
            else:
                print("✅ No hay usuarios que necesiten migración")
            
            # Estadísticas
            total_users = User.query.count()
            verified_users = User.query.filter_by(email_verified=True).count()
            unverified_users = User.query.filter_by(email_verified=False).count()
            
            print("\n" + "="*70)
            print("ESTADÍSTICAS")
            print("="*70)
            print(f"Total de usuarios: {total_users}")
            print(f"Usuarios verificados: {verified_users}")
            print(f"Usuarios no verificados: {unverified_users}")
            
            print("\n✅ Migración completada exitosamente")
            print("\n📝 Nota: Los usuarios nuevos deberán verificar su email al registrarse.")
            print("   Los usuarios existentes fueron marcados como verificados automáticamente.")
            
        except Exception as e:
            print(f"\n❌ Error durante la migración: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False
        
        return True

if __name__ == '__main__':
    migrate_email_verification()

