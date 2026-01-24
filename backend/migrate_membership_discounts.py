#!/usr/bin/env python3
"""
Script para crear la tabla membership_discount y poblar con datos iniciales
basados en los descuentos hardcodeados actuales.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db, MembershipDiscount
from sqlalchemy import text

def create_table():
    """Crear la tabla membership_discount si no existe"""
    with app.app_context():
        try:
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'membership_discount' in tables:
                print("✓ La tabla membership_discount ya existe")
                return True
            else:
                print("1. Creando tabla membership_discount...")
                # Crear la tabla usando el modelo
                MembershipDiscount.__table__.create(db.engine, checkfirst=True)
                print("   ✓ Tabla membership_discount creada")
                return True
        except Exception as e:
            print(f"✗ Error creando tabla: {e}")
            import traceback
            traceback.print_exc()
            return False

def create_initial_discounts():
    """Crear descuentos iniciales basados en los valores hardcodeados actuales"""
    with app.app_context():
        print("\n2. Creando descuentos iniciales...")
        
        # Descuentos para SERVICIOS (valores actuales hardcodeados)
        service_discounts = [
            ('basic', 'service', 0.0),      # Sin descuento
            ('pro', 'service', 10.0),       # 10% descuento
            ('premium', 'service', 20.0),   # 20% descuento
            ('deluxe', 'service', 30.0),    # 30% descuento
            ('corporativo', 'service', 40.0) # 40% descuento (nuevo)
        ]
        
        # Descuentos para EVENTOS (valores sugeridos, pueden ajustarse)
        event_discounts = [
            ('basic', 'event', 0.0),
            ('pro', 'event', 10.0),
            ('premium', 'event', 20.0),
            ('deluxe', 'event', 30.0),
            ('corporativo', 'event', 40.0)
        ]
        
        created = 0
        skipped = 0
        
        for membership_type, product_type, discount_percent in service_discounts + event_discounts:
            # Verificar si ya existe
            existing = MembershipDiscount.query.filter_by(
                membership_type=membership_type,
                product_type=product_type
            ).first()
            
            if existing:
                print(f"  → Ya existe: {membership_type} - {product_type} ({existing.discount_percentage}%)")
                skipped += 1
            else:
                discount = MembershipDiscount(
                    membership_type=membership_type,
                    product_type=product_type,
                    discount_percentage=discount_percent,
                    is_active=True
                )
                db.session.add(discount)
                created += 1
                print(f"  ✓ Creado: {membership_type} - {product_type}: {discount_percent}%")
        
        db.session.commit()
        print(f"\n   → {created} descuentos creados, {skipped} ya existían")
        return created

def main():
    print("=" * 80)
    print("MIGRACIÓN: Crear Tabla y Descuentos de Membresía")
    print("=" * 80)
    print()
    
    if not create_table():
        print("\n✗ Error: No se pudo crear la tabla")
        return
    
    created = create_initial_discounts()
    
    print()
    print("=" * 80)
    print("✅ Migración completada")
    print("=" * 80)
    print()
    print("Descuentos configurados:")
    print("  - Servicios: Basic (0%), Pro (10%), Premium (20%), Deluxe (30%), Corporativo (40%)")
    print("  - Eventos: Basic (0%), Pro (10%), Premium (20%), Deluxe (30%), Corporativo (40%)")
    print()
    print("Puedes modificar estos valores desde /admin/membership-discounts")

if __name__ == '__main__':
    main()
