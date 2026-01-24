#!/usr/bin/env python3
"""
Script de migración para agregar nuevas funcionalidades de pago:
- Pagos recurrentes automáticos
- Facturación automática
- Múltiples monedas
- Pagos en cuotas
- Wallet/Credits del usuario
- Precios diferenciados por período
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from sqlalchemy import text

def migrate():
    """Ejecutar migraciones"""
    with app.app_context():
        print("🔄 Iniciando migración de funcionalidades de pago...")
        
        try:
            # 1. Agregar campos a Payment para pagos recurrentes
            print("\n1️⃣ Agregando campos para pagos recurrentes...")
            fields_recurring = [
                ("is_recurring", "BOOLEAN DEFAULT 0"),
                ("recurring_id", "VARCHAR(200)"),
                ("billing_cycle", "VARCHAR(20)"),
                ("next_billing_date", "DATETIME"),
                ("parent_payment_id", "INTEGER")
            ]
            
            for field_name, field_type in fields_recurring:
                try:
                    db.session.execute(text(f"""
                        ALTER TABLE payment 
                        ADD COLUMN {field_name} {field_type}
                    """))
                    print(f"   ✅ Campo {field_name} agregado")
                except Exception as e:
                    if "duplicate column" in str(e).lower():
                        print(f"   ⚠️ Campo {field_name} ya existe")
                    else:
                        raise
            
            # 2. Agregar campos para pagos en cuotas
            print("\n2️⃣ Agregando campos para pagos en cuotas...")
            fields_installments = [
                ("is_installment", "BOOLEAN DEFAULT 0"),
                ("installment_count", "INTEGER DEFAULT 1"),
                ("installment_number", "INTEGER DEFAULT 1"),
                ("installment_total", "INTEGER"),
                ("parent_installment_id", "INTEGER")
            ]
            
            for field_name, field_type in fields_installments:
                try:
                    db.session.execute(text(f"""
                        ALTER TABLE payment 
                        ADD COLUMN {field_name} {field_type}
                    """))
                    print(f"   ✅ Campo {field_name} agregado")
                except Exception as e:
                    if "duplicate column" in str(e).lower():
                        print(f"   ⚠️ Campo {field_name} ya existe")
                    else:
                        raise
            
            # 3. Agregar campos para múltiples monedas
            print("\n3️⃣ Agregando campos para múltiples monedas...")
            fields_currency = [
                ("exchange_rate", "FLOAT DEFAULT 1.0"),
                ("original_amount", "FLOAT"),
                ("original_currency", "VARCHAR(3)")
            ]
            
            for field_name, field_type in fields_currency:
                try:
                    db.session.execute(text(f"""
                        ALTER TABLE payment 
                        ADD COLUMN {field_name} {field_type}
                    """))
                    print(f"   ✅ Campo {field_name} agregado")
                except Exception as e:
                    if "duplicate column" in str(e).lower():
                        print(f"   ⚠️ Campo {field_name} ya existe")
                    else:
                        raise
            
            # 4. Agregar campo invoice_id a Payment
            print("\n4️⃣ Agregando relación con facturas...")
            try:
                db.session.execute(text("""
                    ALTER TABLE payment 
                    ADD COLUMN invoice_id INTEGER
                """))
                print("   ✅ Campo invoice_id agregado")
            except Exception as e:
                if "duplicate column" in str(e).lower():
                    print("   ⚠️ Campo invoice_id ya existe")
                else:
                    raise
            
            # 5. Agregar campos a Subscription para billing cycle
            print("\n5️⃣ Agregando campos de billing cycle a Subscription...")
            fields_billing = [
                ("billing_cycle", "VARCHAR(20) DEFAULT 'yearly'"),
                ("monthly_price", "FLOAT"),
                ("yearly_price", "FLOAT")
            ]
            
            for field_name, field_type in fields_billing:
                try:
                    db.session.execute(text(f"""
                        ALTER TABLE subscription 
                        ADD COLUMN {field_name} {field_type}
                    """))
                    print(f"   ✅ Campo {field_name} agregado")
                except Exception as e:
                    if "duplicate column" in str(e).lower():
                        print(f"   ⚠️ Campo {field_name} ya existe")
                    else:
                        raise
            
            # 6. Crear tabla invoice
            print("\n6️⃣ Creando tabla invoice...")
            try:
                db.session.execute(text("""
                    CREATE TABLE invoice (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        invoice_number VARCHAR(50) UNIQUE NOT NULL,
                        user_id INTEGER NOT NULL,
                        subscription_id INTEGER,
                        amount FLOAT NOT NULL,
                        currency VARCHAR(3) DEFAULT 'usd',
                        tax_amount FLOAT DEFAULT 0.0,
                        total_amount FLOAT NOT NULL,
                        status VARCHAR(20) DEFAULT 'pending',
                        due_date DATETIME NOT NULL,
                        paid_at DATETIME,
                        description TEXT,
                        items TEXT,
                        billing_address TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES user(id),
                        FOREIGN KEY (subscription_id) REFERENCES subscription(id)
                    )
                """))
                print("   ✅ Tabla invoice creada")
            except Exception as e:
                if "already exists" in str(e).lower() or "table" in str(e).lower() and "exists" in str(e).lower():
                    print("   ⚠️ Tabla invoice ya existe")
                else:
                    raise
            
            # 7. Crear tabla user_wallet
            print("\n7️⃣ Creando tabla user_wallet...")
            try:
                db.session.execute(text("""
                    CREATE TABLE user_wallet (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL UNIQUE,
                        balance FLOAT DEFAULT 0.0,
                        currency VARCHAR(3) DEFAULT 'usd',
                        credit_limit FLOAT DEFAULT 0.0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES user(id)
                    )
                """))
                print("   ✅ Tabla user_wallet creada")
            except Exception as e:
                if "already exists" in str(e).lower() or "table" in str(e).lower() and "exists" in str(e).lower():
                    print("   ⚠️ Tabla user_wallet ya existe")
                else:
                    raise
            
            # 8. Crear tabla wallet_transaction
            print("\n8️⃣ Creando tabla wallet_transaction...")
            try:
                db.session.execute(text("""
                    CREATE TABLE wallet_transaction (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        wallet_id INTEGER NOT NULL,
                        amount FLOAT NOT NULL,
                        transaction_type VARCHAR(20) NOT NULL,
                        description TEXT,
                        payment_id INTEGER,
                        invoice_id INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (wallet_id) REFERENCES user_wallet(id),
                        FOREIGN KEY (payment_id) REFERENCES payment(id),
                        FOREIGN KEY (invoice_id) REFERENCES invoice(id)
                    )
                """))
                print("   ✅ Tabla wallet_transaction creada")
            except Exception as e:
                if "already exists" in str(e).lower() or "table" in str(e).lower() and "exists" in str(e).lower():
                    print("   ⚠️ Tabla wallet_transaction ya existe")
                else:
                    raise
            
            # 9. Crear tabla membership_pricing
            print("\n9️⃣ Creando tabla membership_pricing...")
            try:
                db.session.execute(text("""
                    CREATE TABLE membership_pricing (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        membership_type VARCHAR(50) NOT NULL,
                        billing_cycle VARCHAR(20) NOT NULL,
                        price FLOAT NOT NULL,
                        currency VARCHAR(3) DEFAULT 'usd',
                        is_active BOOLEAN DEFAULT 1,
                        discount_percentage FLOAT DEFAULT 0.0,
                        discount_amount FLOAT DEFAULT 0.0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(membership_type, billing_cycle)
                    )
                """))
                print("   ✅ Tabla membership_pricing creada")
            except Exception as e:
                if "already exists" in str(e).lower() or "table" in str(e).lower() and "exists" in str(e).lower():
                    print("   ⚠️ Tabla membership_pricing ya existe")
                else:
                    raise
            
            # 10. Insertar precios por defecto
            print("\n🔟 Insertando precios por defecto...")
            try:
                # Precios mensuales y anuales para cada tipo de membresía
                default_prices = [
                    ('basic', 'monthly', 0.0),
                    ('basic', 'yearly', 0.0),
                    ('pro', 'monthly', 6.0),  # $6/mes = $72/año (más caro que $60/año)
                    ('pro', 'yearly', 60.0),
                    ('premium', 'monthly', 12.0),  # $12/mes = $144/año (más caro que $120/año)
                    ('premium', 'yearly', 120.0),
                    ('deluxe', 'monthly', 18.0),  # $18/mes = $216/año (más caro que $180/año)
                    ('deluxe', 'yearly', 180.0)
                ]
                
                for membership_type, billing_cycle, price in default_prices:
                    try:
                        db.session.execute(text("""
                            INSERT INTO membership_pricing (membership_type, billing_cycle, price, currency, is_active)
                            VALUES (:type, :cycle, :price, 'usd', 1)
                        """), {'type': membership_type, 'cycle': billing_cycle, 'price': price})
                    except Exception as e:
                        if "UNIQUE constraint" in str(e) or "unique constraint" in str(e).lower():
                            print(f"   ⚠️ Precio para {membership_type} {billing_cycle} ya existe")
                        else:
                            raise
                
                print("   ✅ Precios por defecto insertados")
            except Exception as e:
                print(f"   ⚠️ Error insertando precios: {e}")
            
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






