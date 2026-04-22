#!/usr/bin/env python3
"""
Script para re-enviar webhooks a Odoo para pagos pasados
Uso: python3 reenviar_webhook_odoo.py <payment_id>
"""

import sys
import os
import subprocess

# Cargar variables de entorno desde systemd
try:
    result = subprocess.run(
        ['systemctl', 'show', 'nodeone.service'],
        capture_output=True,
        text=True
    )
    
    for line in result.stdout.split('\n'):
        if 'Environment=' in line and 'ODOO_' in line:
            env_line = line.replace('Environment=', '')
            for var in env_line.split():
                if '=' in var:
                    key, value = var.split('=', 1)
                    value = value.strip('"')
                    os.environ[key] = value
except:
    pass

import sys
sys.path.insert(0, '.')

from app import app, db, Payment, User, Cart
from datetime import datetime

def reenviar_webhook(payment_id):
    """Re-enviar webhook a Odoo para un pago específico"""
    
    with app.app_context():
        payment = Payment.query.get(payment_id)
        
        if not payment:
            print(f"❌ Pago ID {payment_id} no encontrado")
            return False
        
        if payment.status != 'succeeded':
            print(f"⚠️  El pago {payment_id} no está confirmado (estado: {payment.status})")
            return False
        
        user = User.query.get(payment.user_id)
        if not user:
            print(f"❌ Usuario no encontrado para pago {payment_id}")
            return False
        
        cart = Cart.query.filter_by(user_id=payment.user_id).first()
        
        print("=" * 70)
        print(f"RE-ENVIANDO WEBHOOK A ODOO PARA PAGO ID: {payment_id}")
        print("=" * 70)
        print(f"\n📋 Información del pago:")
        print(f"   Order ID: ORD-{datetime.now().year}-{payment.id:05d}")
        print(f"   Usuario: {user.email}")
        print(f"   Nombre: {user.first_name} {user.last_name}")
        print(f"   Monto: ${payment.amount/100:.2f} {payment.currency.upper()}")
        print(f"   Método: {payment.payment_method.upper()}")
        print(f"   Estado: {payment.status}")
        print(f"   Fecha confirmación: {payment.paid_at}")
        
        try:
            from odoo_integration_service import get_odoo_service
            
            odoo_service = get_odoo_service()
            print(f"\n🔧 Servicio Odoo:")
            print(f"   Habilitado: {odoo_service.enabled}")
            print(f"   URL: {odoo_service.api_url}")
            print(f"   API Key: {'✅ Configurada' if odoo_service.api_key and odoo_service.api_key != 'CAMBIAR_CON_API_KEY_REAL' else '❌ No configurada'}")
            print(f"   HMAC Secret: {'✅ Configurado' if odoo_service.hmac_secret and odoo_service.hmac_secret != 'CAMBIAR_CON_HMAC_SECRET_REAL' else '❌ No configurado'}")
            
            if not odoo_service.enabled:
                print(f"\n⚠️  Integración deshabilitada")
                print(f"   Verificar ODOO_INTEGRATION_ENABLED en systemd")
                return False
            
            cart_items = list(cart.items) if cart else None
            print(f"\n📤 Enviando webhook...")
            success, error_msg, response = odoo_service.send_payment_webhook(payment, user, cart_items)
            
            if success:
                print(f"✅ Webhook enviado exitosamente")
                if response:
                    data = response.get('data', {})
                    print(f"   Order ID: {data.get('order_id', 'N/A')}")
                    print(f"   Factura: {data.get('invoice_number', 'N/A')}")
                    print(f"   Partner ID: {data.get('partner_id', 'N/A')}")
                    print(f"   Invoice ID: {data.get('invoice_id', 'N/A')}")
                return True
            else:
                print(f"❌ Error enviando webhook: {error_msg}")
                return False
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            print("\n" + "=" * 70)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python3 reenviar_webhook_odoo.py <payment_id>")
        print("\nEjemplo:")
        print("  python3 reenviar_webhook_odoo.py 7")
        sys.exit(1)
    
    payment_id = int(sys.argv[1])
    success = reenviar_webhook(payment_id)
    sys.exit(0 if success else 1)
