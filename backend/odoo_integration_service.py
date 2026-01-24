#!/usr/bin/env python3
"""
Servicio de integración con Odoo 18
Envía webhooks a Odoo cuando se confirma un pago en membresia-relatic
"""

import os
import json
import hmac
import hashlib
import requests
from datetime import datetime
from typing import Dict, Optional, Tuple
from flask import current_app


class OdooIntegrationService:
    """Servicio para enviar webhooks a Odoo"""
    
    def __init__(self):
        self.api_url = os.getenv('ODOO_API_URL', 'https://odoo.relatic.org/api/relatic/v1/sale')
        self.api_key = os.getenv('ODOO_API_KEY', '')
        self.hmac_secret = os.getenv('ODOO_HMAC_SECRET', '')
        self.environment = os.getenv('ODOO_ENVIRONMENT', 'prod')
        self.enabled = os.getenv('ODOO_INTEGRATION_ENABLED', 'false').lower() == 'true'
    
    def _generate_hmac_signature(self, payload: str) -> str:
        """Genera firma HMAC del payload"""
        if not self.hmac_secret:
            return ''
        
        signature = hmac.new(
            self.hmac_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _format_order_id(self, payment_id: int) -> str:
        """Formatea el order_id según el estándar"""
        year = datetime.utcnow().year
        return f"ORD-{year}-{payment_id:05d}"
    
    def _get_payment_method_odoo(self, payment_method: str) -> str:
        """Mapea método de pago de membresia-relatic a formato Odoo"""
        mapping = {
            'yappy': 'YAPPY',
            'paypal': 'TARJETA',  # PayPal se procesa como tarjeta
            'stripe': 'TARJETA',
            'banco_general': 'TRANSFERENCIA',
            'interbank': 'TRANSFERENCIA'
        }
        return mapping.get(payment_method.lower(), 'TRANSFERENCIA')
    
    def _get_currency_code(self, currency: str) -> str:
        """Mapea código de moneda"""
        mapping = {
            'usd': 'USD',
            'pab': 'PAB',
            'pen': 'PEN'
        }
        return mapping.get(currency.lower(), currency.upper())
    
    def _build_payload(self, payment, user, cart_items: list = None) -> Dict:
        """Construye el payload según contrato JSON v1.0"""
        
        # Obtener items del carrito si están disponibles
        items = []
        if cart_items:
            for item in cart_items:
                # Parsear metadata si existe
                metadata = {}
                if item.item_metadata:
                    try:
                        metadata = json.loads(item.item_metadata) if isinstance(item.item_metadata, str) else item.item_metadata
                    except:
                        metadata = {}
                
                # Determinar SKU según el tipo de item
                if item.product_type == 'membership':
                    sku_map = {
                        'basic': 'MEMB-BASICO',
                        'pro': 'MEMB-ANUAL',
                        'premium': 'MEMB-PREMIUM',
                        'deluxe': 'MEMB-DELUXE'
                    }
                    membership_type = metadata.get('membership_type', '').lower()
                    sku = sku_map.get(membership_type, 'MEMB-ANUAL')
                    name = item.product_name or f"Membresía {metadata.get('membership_type', 'Anual').title()}"
                elif item.product_type == 'event':
                    event_id = metadata.get('event_id', item.product_id)
                    sku = f"EVENT-{event_id}"
                    name = item.product_name or metadata.get('event_name', 'Evento')
                else:
                    sku = f"SERVICE-{item.product_id}"
                    name = item.product_name or metadata.get('service_name', 'Servicio')
                
                # Calcular precio (en centavos a dólares)
                price = (item.unit_price / 100.0) if item.unit_price else 0.0
                
                # ITBMS en Panamá es 7%
                tax_rate = 7.0
                
                items.append({
                    'sku': sku,
                    'name': name,
                    'qty': item.quantity or 1,
                    'price': price,
                    'tax_rate': tax_rate
                })
        
        # Si no hay items del carrito, crear item genérico basado en el pago
        if not items:
            # Determinar SKU según membership_type del pago
            membership_type = payment.membership_type.lower() if payment.membership_type else 'cart'
            sku_map = {
                'basic': 'MEMB-BASICO',
                'pro': 'MEMB-ANUAL',
                'premium': 'MEMB-PREMIUM',
                'deluxe': 'MEMB-DELUXE',
                'cart': 'MEMB-ANUAL'  # Default
            }
            sku = sku_map.get(membership_type, 'MEMB-ANUAL')
            name = f"Membresía {payment.membership_type.title()}" if payment.membership_type != 'cart' else 'Membresía'
            
            # Monto en centavos a dólares
            amount_dollars = payment.amount / 100.0
            
            items.append({
                'sku': sku,
                'name': name,
                'qty': 1,
                'price': amount_dollars,
                'tax_rate': 7.0
            })
        
        # Calcular total con impuestos
        subtotal = sum(item['price'] * item['qty'] for item in items)
        tax_amount = sum(item['price'] * item['qty'] * (item['tax_rate'] / 100.0) for item in items)
        total_amount = subtotal + tax_amount
        
        # Obtener información del usuario
        user_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
        # Intentar obtener VAT/cedula (puede tener diferentes nombres según el modelo)
        user_vat = ''
        if hasattr(user, 'vat'):
            user_vat = user.vat or ''
        elif hasattr(user, 'cedula'):
            user_vat = user.cedula or ''
        elif hasattr(user, 'dni'):
            user_vat = user.dni or ''
        elif hasattr(user, 'pasaporte'):
            user_vat = user.pasaporte or ''
        
        user_phone = user.phone if hasattr(user, 'phone') else ''
        
        # Formatear fecha de pago
        payment_date = payment.paid_at.strftime('%Y-%m-%d') if payment.paid_at else datetime.utcnow().strftime('%Y-%m-%d')
        
        # Construir payload
        payload = {
            'meta': {
                'version': '1.0',
                'source': 'membresia-relatic',
                'environment': self.environment,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            },
            'order_id': self._format_order_id(payment.id),
            'member': {
                'email': user.email,
                'name': user_name,
                'vat': user_vat,
                'phone': user_phone
            },
            'items': items,
            'payment': {
                'method': self._get_payment_method_odoo(payment.payment_method),
                'amount': round(total_amount, 2),
                'reference': payment.payment_reference or f"PAY-{payment.id}",
                'date': payment_date,
                'currency': self._get_currency_code(payment.currency)
            }
        }
        
        return payload
    
    def send_payment_webhook(self, payment, user, cart_items: list = None) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Envía webhook a Odoo cuando se confirma un pago
        
        Args:
            payment: Objeto Payment confirmado
            user: Objeto User que realizó el pago
            cart_items: Lista de CartItem (opcional)
        
        Returns:
            Tuple (success, error_message, response_data)
        """
        
        # Verificar si la integración está habilitada
        if not self.enabled:
            print("⚠️ Integración con Odoo deshabilitada (ODOO_INTEGRATION_ENABLED=false)")
            return False, "Integración deshabilitada", None
        
        # Verificar configuración
        if not self.api_key:
            print("⚠️ ODOO_API_KEY no configurada")
            return False, "API Key no configurada", None
        
        if not self.hmac_secret:
            print("⚠️ ODOO_HMAC_SECRET no configurada")
            return False, "HMAC Secret no configurada", None
        
        try:
            # Construir payload
            payload = self._build_payload(payment, user, cart_items)
            
            # Convertir a JSON string
            payload_json = json.dumps(payload, ensure_ascii=False)
            
            # Generar firma HMAC
            signature = self._generate_hmac_signature(payload_json)
            
            # Preparar headers
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'X-Relatic-Signature': signature,
                'Content-Type': 'application/json'
            }
            
            # Enviar request
            print(f"📤 Enviando webhook a Odoo para pago {payment.id} (Order ID: {payload['order_id']})")
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            # Verificar respuesta
            if response.status_code == 200:
                response_data = response.json()
                print(f"✅ Webhook enviado exitosamente a Odoo")
                print(f"   Order ID: {payload['order_id']}")
                print(f"   Factura: {response_data.get('data', {}).get('invoice_number', 'N/A')}")
                return True, None, response_data
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get('error', {}).get('message', f'Error HTTP {response.status_code}')
                print(f"❌ Error enviando webhook a Odoo: {error_msg}")
                print(f"   Status Code: {response.status_code}")
                return False, error_msg, error_data
            
        except requests.exceptions.Timeout:
            error_msg = "Timeout al conectar con Odoo"
            print(f"❌ {error_msg}")
            return False, error_msg, None
        
        except requests.exceptions.ConnectionError:
            error_msg = "Error de conexión con Odoo"
            print(f"❌ {error_msg}")
            return False, error_msg, None
        
        except Exception as e:
            error_msg = f"Error inesperado: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return False, error_msg, None


# Instancia global del servicio
_odoo_service = None

def get_odoo_service() -> OdooIntegrationService:
    """Obtiene instancia singleton del servicio Odoo"""
    global _odoo_service
    if _odoo_service is None:
        _odoo_service = OdooIntegrationService()
    return _odoo_service
