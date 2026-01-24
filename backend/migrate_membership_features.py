#!/usr/bin/env python3
"""
Script de migración para agregar nuevas funcionalidades de membresía:
- Pausar membresía temporalmente
- Upgrade/Downgrade automático
- Período de gracia para renovación
- Membresías familiares/grupales
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from sqlalchemy import text

def migrate():
    """Ejecutar migraciones"""
    with app.app_context():
        print("🔄 Iniciando migración de funcionalidades de membresía...")
        
        try:
            # 1. Agregar campos a Subscription para pausar membresía
            print("\n1️⃣ Agregando campos para pausar membresía...")
            try:
                db.session.execute(text("""
                    ALTER TABLE subscription 
                    ADD COLUMN is_paused BOOLEAN DEFAULT 0
                """))
                print("   ✅ Campo is_paused agregado")
            except Exception as e:
                if "duplicate column" in str(e).lower():
                    print("   ⚠️ Campo is_paused ya existe")
                else:
                    raise
            
            try:
                db.session.execute(text("""
                    ALTER TABLE subscription 
                    ADD COLUMN paused_at DATETIME
                """))
                print("   ✅ Campo paused_at agregado")
            except Exception as e:
                if "duplicate column" in str(e).lower():
                    print("   ⚠️ Campo paused_at ya existe")
                else:
                    raise
            
            try:
                db.session.execute(text("""
                    ALTER TABLE subscription 
                    ADD COLUMN paused_until DATETIME
                """))
                print("   ✅ Campo paused_until agregado")
            except Exception as e:
                if "duplicate column" in str(e).lower():
                    print("   ⚠️ Campo paused_until ya existe")
                else:
                    raise
            
            try:
                db.session.execute(text("""
                    ALTER TABLE subscription 
                    ADD COLUMN paused_days_remaining INTEGER DEFAULT 0
                """))
                print("   ✅ Campo paused_days_remaining agregado")
            except Exception as e:
                if "duplicate column" in str(e).lower():
                    print("   ⚠️ Campo paused_days_remaining ya existe")
                else:
                    raise
            
            # 2. Agregar campos para período de gracia
            print("\n2️⃣ Agregando campos para período de gracia...")
            try:
                db.session.execute(text("""
                    ALTER TABLE subscription 
                    ADD COLUMN grace_period_days INTEGER DEFAULT 7
                """))
                print("   ✅ Campo grace_period_days agregado")
            except Exception as e:
                if "duplicate column" in str(e).lower():
                    print("   ⚠️ Campo grace_period_days ya existe")
                else:
                    raise
            
            try:
                db.session.execute(text("""
                    ALTER TABLE subscription 
                    ADD COLUMN grace_period_end DATETIME
                """))
                print("   ✅ Campo grace_period_end agregado")
            except Exception as e:
                if "duplicate column" in str(e).lower():
                    print("   ⚠️ Campo grace_period_end ya existe")
                else:
                    raise
            
            # 3. Agregar campos para upgrade/downgrade
            print("\n3️⃣ Agregando campos para upgrade/downgrade...")
            try:
                db.session.execute(text("""
                    ALTER TABLE subscription 
                    ADD COLUMN previous_membership_type VARCHAR(50)
                """))
                print("   ✅ Campo previous_membership_type agregado")
            except Exception as e:
                if "duplicate column" in str(e).lower():
                    print("   ⚠️ Campo previous_membership_type ya existe")
                else:
                    raise
            
            try:
                db.session.execute(text("""
                    ALTER TABLE subscription 
                    ADD COLUMN upgrade_requested BOOLEAN DEFAULT 0
                """))
                print("   ✅ Campo upgrade_requested agregado")
            except Exception as e:
                if "duplicate column" in str(e).lower():
                    print("   ⚠️ Campo upgrade_requested ya existe")
                else:
                    raise
            
            try:
                db.session.execute(text("""
                    ALTER TABLE subscription 
                    ADD COLUMN downgrade_requested BOOLEAN DEFAULT 0
                """))
                print("   ✅ Campo downgrade_requested agregado")
            except Exception as e:
                if "duplicate column" in str(e).lower():
                    print("   ⚠️ Campo downgrade_requested ya existe")
                else:
                    raise
            
            try:
                db.session.execute(text("""
                    ALTER TABLE subscription 
                    ADD COLUMN requested_membership_type VARCHAR(50)
                """))
                print("   ✅ Campo requested_membership_type agregado")
            except Exception as e:
                if "duplicate column" in str(e).lower():
                    print("   ⚠️ Campo requested_membership_type ya existe")
                else:
                    raise
            
            # 4. Actualizar status para incluir 'paused'
            print("\n4️⃣ Actualizando valores de status...")
            # No hay cambios necesarios, el campo status ya acepta cualquier string
            
            # 5. Crear tabla family_group
            print("\n5️⃣ Creando tabla family_group...")
            try:
                db.session.execute(text("""
                    CREATE TABLE family_group (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(200) NOT NULL,
                        owner_id INTEGER NOT NULL,
                        membership_type VARCHAR(50) NOT NULL,
                        max_members INTEGER DEFAULT 5,
                        subscription_id INTEGER,
                        is_active BOOLEAN DEFAULT 1,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (owner_id) REFERENCES user(id),
                        FOREIGN KEY (subscription_id) REFERENCES subscription(id)
                    )
                """))
                print("   ✅ Tabla family_group creada")
            except Exception as e:
                if "already exists" in str(e).lower() or "table" in str(e).lower() and "exists" in str(e).lower():
                    print("   ⚠️ Tabla family_group ya existe")
                else:
                    raise
            
            # 6. Crear tabla family_group_member
            print("\n6️⃣ Creando tabla family_group_member...")
            try:
                db.session.execute(text("""
                    CREATE TABLE family_group_member (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        family_group_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        role VARCHAR(20) DEFAULT 'member',
                        added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1,
                        FOREIGN KEY (family_group_id) REFERENCES family_group(id),
                        FOREIGN KEY (user_id) REFERENCES user(id),
                        UNIQUE(family_group_id, user_id)
                    )
                """))
                print("   ✅ Tabla family_group_member creada")
            except Exception as e:
                if "already exists" in str(e).lower() or "table" in str(e).lower() and "exists" in str(e).lower():
                    print("   ⚠️ Tabla family_group_member ya existe")
                else:
                    raise
            
            # 7. Calcular períodos de gracia para suscripciones expiradas
            print("\n7️⃣ Calculando períodos de gracia para suscripciones expiradas...")
            try:
                db.session.execute(text("""
                    UPDATE subscription 
                    SET grace_period_end = datetime(end_date, '+' || grace_period_days || ' days')
                    WHERE status = 'expired' 
                    AND grace_period_end IS NULL
                    AND grace_period_days > 0
                """))
                affected = db.session.execute(text("SELECT changes()")).scalar()
                print(f"   ✅ {affected} suscripciones actualizadas con período de gracia")
            except Exception as e:
                print(f"   ⚠️ Error calculando períodos de gracia: {e}")
            
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






