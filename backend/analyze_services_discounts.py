#!/usr/bin/env python3
"""
Análisis completo de servicios y descuentos
Compara el esquema esperado con la implementación actual
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from app import Service, ServicePricingRule, MembershipDiscount, Discount, DiscountCode, Cart, CartItem

def print_header(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def analyze_services():
    """Analizar servicios y sus reglas de precio"""
    print_header("📦 ANÁLISIS DE SERVICIOS")
    
    services = Service.query.all()
    print(f"Total de servicios: {len(services)}")
    active_services = [s for s in services if s.is_active]
    print(f"Servicios activos: {len(active_services)}")
    
    # Servicios con reglas de precio
    services_with_rules = []
    services_without_rules = []
    
    for service in active_services:
        rules = ServicePricingRule.query.filter_by(service_id=service.id).all()
        if rules:
            services_with_rules.append((service, rules))
        else:
            services_without_rules.append(service)
    
    print(f"\nServicios con reglas de precio: {len(services_with_rules)}")
    print(f"Servicios sin reglas (usan MembershipDiscount): {len(services_without_rules)}")
    
    # Analizar reglas
    all_rules = ServicePricingRule.query.all()
    active_rules = [r for r in all_rules if r.is_active]
    inactive_rules = [r for r in all_rules if not r.is_active]
    
    print(f"\n📋 REGLAS DE PRECIO:")
    print(f"   Total: {len(all_rules)}")
    print(f"   Activas: {len(active_rules)}")
    print(f"   Inactivas: {len(inactive_rules)}")
    
    if inactive_rules:
        print(f"\n   ⚠️  REGLAS INACTIVAS (no se aplican):")
        for rule in inactive_rules:
            service = Service.query.get(rule.service_id)
            print(f"   - {service.name if service else 'N/A'} ({rule.membership_type}):")
            print(f"     * Incluido: {rule.is_included}")
            print(f"     * Precio fijo: {rule.price}")
            print(f"     * Descuento %: {rule.discount_percentage}")
            print(f"     * Activo: {rule.is_active} ❌")
    
    # Probar cálculo de precios
    if services_with_rules:
        print(f"\n🔍 PRUEBA DE CÁLCULO (primer servicio con reglas):")
        service, rules = services_with_rules[0]
        print(f"   Servicio: {service.name}")
        print(f"   Precio base: ${service.base_price}")
        
        for membership in ['basic', 'pro', 'premium', 'deluxe', 'corporativo']:
            pricing = service.pricing_for_membership(membership)
            rule = ServicePricingRule.query.filter_by(
                service_id=service.id,
                membership_type=membership,
                is_active=True
            ).first()
            
            status = "✅" if pricing['is_included'] or pricing['final_price'] < service.base_price else "ℹ️"
            print(f"   {status} {membership}: ${pricing['final_price']:.2f} "
                  f"(descuento: {pricing['discount_percentage']}%, "
                  f"incluido: {pricing['is_included']}, "
                  f"regla activa: {'Sí' if rule else 'No'})")

def analyze_discounts():
    """Analizar sistema de descuentos"""
    print_header("🎫 ANÁLISIS DE DESCUENTOS")
    
    # MembershipDiscount (descuentos automáticos por membresía)
    print("📊 MembershipDiscount (Descuentos Automáticos por Membresía):")
    membership_discounts = MembershipDiscount.query.filter_by(is_active=True).all()
    print(f"   Total activos: {len(membership_discounts)}")
    
    for product_type in ['service', 'event']:
        print(f"\n   {product_type.upper()}:")
        for membership in ['basic', 'pro', 'premium', 'deluxe', 'corporativo']:
            discount = MembershipDiscount.query.filter_by(
                membership_type=membership,
                product_type=product_type,
                is_active=True
            ).first()
            if discount:
                print(f"     - {membership}: {discount.discount_percentage}%")
            else:
                print(f"     - {membership}: ❌ NO CONFIGURADO")
    
    # Discount (descuentos reutilizables)
    print(f"\n📊 Discount (Descuentos Reutilizables):")
    discounts = Discount.query.all()
    active_discounts = [d for d in discounts if d.is_active]
    master_discounts = [d for d in discounts if d.is_master]
    
    print(f"   Total: {len(discounts)}")
    print(f"   Activos: {len(active_discounts)}")
    print(f"   Descuento maestro: {len(master_discounts)}")
    
    if active_discounts:
        print(f"\n   Descuentos activos:")
        for d in active_discounts:
            print(f"     - {d.name} ({d.code or 'sin código'}): {d.value}{'%' if d.discount_type == 'percentage' else '$'}")
            print(f"       Categoría: {d.category}, Membresía: {d.membership_tier or 'todas'}")
            print(f"       Maestro: {'Sí' if d.is_master else 'No'}")
    
    # DiscountCode (códigos promocionales)
    print(f"\n📊 DiscountCode (Códigos Promocionales):")
    codes = DiscountCode.query.all()
    active_codes = [c for c in codes if c.is_active]
    
    print(f"   Total: {len(codes)}")
    print(f"   Activos: {len(active_codes)}")
    
    if active_codes:
        for code in active_codes:
            print(f"     - {code.code}: {code.value}{'%' if code.discount_type == 'percentage' else '$'}")
            print(f"       Alcance: {code.applies_to}, Usos: {code.current_uses}/{code.max_uses_total or '∞'}")

def analyze_cart_calculation():
    """Analizar cómo se calculan los totales en el carrito"""
    print_header("🛒 ANÁLISIS DE CÁLCULO EN CARRITO")
    
    print("📋 FLUJO DE CÁLCULO:")
    print("   1. CartItem.get_subtotal() = unit_price * quantity")
    print("   2. Cart.get_subtotal() = suma de todos los items")
    print("   3. Cart.get_discount_breakdown():")
    print("      a. Aplica descuento maestro (si existe)")
    print("      b. Aplica código promocional (si existe)")
    print("   4. Cart.get_final_total() = subtotal - descuentos")
    
    print("\n⚠️  OBSERVACIONES:")
    print("   - Los descuentos por membresía se aplican al calcular unit_price")
    print("   - unit_price se calcula usando Service.pricing_for_membership()")
    print("   - Los descuentos del carrito (maestro/código) se aplican al subtotal")
    
    # Verificar carritos activos
    carts = Cart.query.all()
    if carts:
        print(f"\n📊 Carritos en el sistema: {len(carts)}")
        for cart in carts[:3]:
            items = CartItem.query.filter_by(cart_id=cart.id).all()
            if items:
                print(f"\n   Carrito #{cart.id} (Usuario: {cart.user_id}):")
                print(f"   Items: {len(items)}")
                subtotal = cart.get_subtotal()
                total = cart.get_final_total()
                print(f"   Subtotal: ${subtotal:.2f}")
                print(f"   Total final: ${total:.2f}")
                if subtotal != total:
                    print(f"   Descuento aplicado: ${subtotal - total:.2f}")

def compare_schema_vs_implementation():
    """Comparar esquema esperado con implementación"""
    print_header("🔍 COMPARACIÓN: ESQUEMA vs IMPLEMENTACIÓN")
    
    print("📋 ESQUEMA ESPERADO (según comentarios):")
    print("   Básico (Ba): 0% descuento")
    print("   Pro: 10% descuento")
    print("   Premium (R): 20% descuento")
    print("   Deluxe (DX): 30% descuento")
    print("   Corporativo: 40% descuento")
    
    print("\n💰 IMPLEMENTACIÓN ACTUAL:")
    discounts = MembershipDiscount.query.filter_by(product_type='service', is_active=True).all()
    schema_match = True
    
    expected = {
        'basic': 0.0,
        'pro': 10.0,
        'premium': 20.0,
        'deluxe': 30.0,
        'corporativo': 40.0
    }
    
    for membership, expected_discount in expected.items():
        discount = MembershipDiscount.query.filter_by(
            membership_type=membership,
            product_type='service',
            is_active=True
        ).first()
        
        if discount:
            match = "✅" if discount.discount_percentage == expected_discount else "⚠️"
            if discount.discount_percentage != expected_discount:
                schema_match = False
            print(f"   {match} {membership}: {discount.discount_percentage}% (esperado: {expected_discount}%)")
        else:
            print(f"   ❌ {membership}: NO CONFIGURADO (esperado: {expected_discount}%)")
            schema_match = False
    
    print(f"\n{'✅ ESQUEMA COINCIDE' if schema_match else '⚠️  HAY DISCREPANCIAS'}")

def identify_issues():
    """Identificar problemas e inconsistencias"""
    print_header("⚠️  PROBLEMAS IDENTIFICADOS")
    
    issues = []
    
    # Problema 1: Reglas inactivas
    inactive_rules = ServicePricingRule.query.filter_by(is_active=False).all()
    if inactive_rules:
        issues.append({
            'type': 'Reglas Inactivas',
            'severity': 'Media',
            'description': f'{len(inactive_rules)} reglas de precio están inactivas',
            'impact': 'Las reglas específicas no se aplican, se usa MembershipDiscount automático',
            'services_affected': len(set(r.service_id for r in inactive_rules))
        })
    
    # Problema 2: Servicios sin reglas
    services = Service.query.filter_by(is_active=True).all()
    services_without_rules = []
    for service in services:
        rules = ServicePricingRule.query.filter_by(service_id=service.id, is_active=True).all()
        if not rules:
            services_without_rules.append(service)
    
    if services_without_rules:
        issues.append({
            'type': 'Servicios sin Reglas',
            'severity': 'Baja',
            'description': f'{len(services_without_rules)} servicios usan solo MembershipDiscount',
            'impact': 'Funciona correctamente, pero no hay personalización por servicio',
            'services_affected': len(services_without_rules)
        })
    
    # Problema 3: Descuento maestro
    master_discounts = Discount.query.filter_by(is_master=True, is_active=True).all()
    if not master_discounts:
        issues.append({
            'type': 'Sin Descuento Maestro',
            'severity': 'Baja',
            'description': 'No hay descuento maestro configurado',
            'impact': 'No se puede aplicar descuento global automático',
            'services_affected': 0
        })
    
    # Mostrar problemas
    if issues:
        for i, issue in enumerate(issues, 1):
            print(f"\n{i}. {issue['type']} [{issue['severity']}]")
            print(f"   Descripción: {issue['description']}")
            print(f"   Impacto: {issue['impact']}")
            if issue['services_affected'] > 0:
                print(f"   Servicios afectados: {issue['services_affected']}")
    else:
        print("✅ No se encontraron problemas críticos")

def main():
    with app.app_context():
        print_header("ANÁLISIS COMPLETO: SERVICIOS Y DESCUENTOS")
        
        analyze_services()
        analyze_discounts()
        analyze_cart_calculation()
        compare_schema_vs_implementation()
        identify_issues()
        
        print_header("ANÁLISIS COMPLETADO")

if __name__ == '__main__':
    main()
