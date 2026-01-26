#!/usr/bin/env python3
"""
Script para debuggear qué datos se pasan al template de servicios
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Service, ServicePricingRule
from flask import render_template

def debug_service_template():
    """Debug qué se pasa al template"""
    
    with app.app_context():
        # Simular lo que hace la ruta /services
        membership_type = 'basic'  # Cambiar según el usuario
        
        all_services = Service.query.filter_by(is_active=True).order_by(Service.display_order, Service.name).all()
        services_by_plan = {}
        
        for service in all_services:
            # Obtener reglas de precio
            pricing_rules = ServicePricingRule.query.filter_by(
                service_id=service.id,
                is_active=True
            ).all()
            
            available_plans = set()
            if service.membership_type:
                available_plans.add(service.membership_type)
            for rule in pricing_rules:
                available_plans.add(rule.membership_type)
            
            user_pricing = service.pricing_for_membership(membership_type)
            
            for plan_type in available_plans:
                if plan_type not in services_by_plan:
                    services_by_plan[plan_type] = []
                
                service_data = {
                    'id': service.id,
                    'name': service.name,
                    'description': service.description,
                    'icon': service.icon or 'fas fa-cog',
                    'external_link': service.external_link,
                    'base_price': service.base_price,
                    'pricing': user_pricing,
                    'requires_diagnostic_appointment': service.requires_diagnostic_appointment if service.requires_diagnostic_appointment is not None else False,
                    'appointment_type_id': service.appointment_type_id,
                    'requires_appointment': service.requires_appointment(),
                    'is_free': service.is_free_service(membership_type)
                }
                
                services_by_plan[plan_type].append(service_data)
        
        # Buscar el servicio de prueba
        print("=" * 60)
        print("DEBUG: DATOS DEL SERVICIO EN TEMPLATE")
        print("=" * 60)
        
        if 'basic' in services_by_plan:
            for s in services_by_plan['basic']:
                if s['id'] == 1:  # Artículos/Revistas
                    print(f"\n📋 Servicio: {s['name']}")
                    print(f"   ID: {s['id']}")
                    print(f"   appointment_type_id: {s['appointment_type_id']}")
                    print(f"   requires_appointment: {s['requires_appointment']}")
                    print(f"   is_free: {s['is_free']}")
                    print(f"   pricing.is_included: {s['pricing']['is_included']}")
                    print(f"   pricing.final_price: {s['pricing']['final_price']}")
                    print()
                    print("🔍 CONDICIÓN EN TEMPLATE:")
                    condition1 = s['appointment_type_id'] is not None
                    condition2 = not (s['pricing']['is_included'] and s['pricing']['final_price'] == 0)
                    print(f"   service.appointment_type_id: {condition1}")
                    print(f"   not (service.pricing.is_included and service.pricing.final_price == 0): {condition2}")
                    print(f"   RESULTADO: {condition1 and condition2}")
                    print()
                    print("✅ El botón DEBE aparecer si ambas condiciones son True")
                    break
        else:
            print("❌ El servicio no aparece en el plan 'basic'")

if __name__ == '__main__':
    debug_service_template()
