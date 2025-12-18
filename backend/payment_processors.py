#!/usr/bin/env python3
"""
Módulo para procesar pagos con diferentes métodos de pago
"""

import os
import json
from datetime import datetime
from flask import current_app

# Constantes para métodos de pago
PAYMENT_METHODS = {
    'stripe': 'Stripe (Tarjeta de Crédito)',
    'paypal': 'PayPal',
    'banco_general': 'Banco General',
    'yappy': 'Yappy',
    'interbank': 'Interbank (Transferencia)'
}

# Estados de pago
PAYMENT_STATUS = {
    'pending': 'Pendiente',
    'awaiting_confirmation': 'Esperando Confirmación',
    'succeeded': 'Completado',
    'failed': 'Fallido',
    'cancelled': 'Cancelado'
}


class PaymentProcessor:
    """Clase base para procesadores de pago"""
    
    def __init__(self, payment_method):
        self.payment_method = payment_method
    
    def create_payment(self, amount, currency='usd', metadata=None):
        """
        Crear un pago
        Retorna: (success, payment_data, error_message)
        payment_data puede contener: payment_url, payment_reference, etc.
        """
        raise NotImplementedError("Subclases deben implementar create_payment")
    
    def verify_payment(self, payment_reference):
        """
        Verificar el estado de un pago
        Retorna: (success, status, payment_data)
        """
        raise NotImplementedError("Subclases deben implementar verify_payment")


class StripeProcessor(PaymentProcessor):
    """Procesador para pagos con Stripe"""
    
    def __init__(self, config=None):
        super().__init__('stripe')
        try:
            import stripe
            self.stripe = stripe
            # Usar configuración de BD si está disponible, sino variables de entorno
            if config:
                self.stripe.api_key = config.get_stripe_secret_key()
            else:
                self.stripe.api_key = os.getenv('STRIPE_SECRET_KEY', '')
        except ImportError:
            self.stripe = None
            print("⚠️ Stripe no está instalado")
    
    def create_payment(self, amount, currency='usd', metadata=None):
        """Crear Payment Intent de Stripe"""
        # Verificar si hay credenciales configuradas
        has_credentials = bool(self.stripe and self.stripe.api_key and 
                              self.stripe.api_key != '' and 
                              not self.stripe.api_key.startswith('sk_test_your_'))
        
        if not has_credentials:
            # Modo demo - simular pago
            import secrets
            fake_intent_id = f"pi_demo_{secrets.token_hex(16)}"
            return True, {
                'payment_reference': fake_intent_id,
                'client_secret': 'demo_client_secret',
                'payment_url': None,
                'demo_mode': True
            }, None
        
        if not self.stripe:
            return False, None, "Stripe no está configurado"
        
        try:
            intent = self.stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                metadata=metadata or {}
            )
            
            return True, {
                'payment_reference': intent.id,
                'client_secret': intent.client_secret,
                'payment_url': None,  # Stripe se maneja en el frontend
                'demo_mode': False
            }, None
        except Exception as e:
            return False, None, str(e)
    
    def verify_payment(self, payment_reference):
        """Verificar estado del pago en Stripe"""
        if not self.stripe:
            return False, 'failed', None
        
        try:
            intent = self.stripe.PaymentIntent.retrieve(payment_reference)
            
            status_map = {
                'succeeded': 'succeeded',
                'processing': 'pending',
                'requires_payment_method': 'failed',
                'requires_confirmation': 'pending',
                'requires_action': 'pending',
                'canceled': 'cancelled'
            }
            
            status = status_map.get(intent.status, 'pending')
            
            return True, status, {
                'status': intent.status,
                'amount': intent.amount,
                'currency': intent.currency
            }
        except Exception as e:
            return False, 'failed', {'error': str(e)}


class PayPalProcessor(PaymentProcessor):
    """Procesador para pagos con PayPal"""
    
    def __init__(self, config=None):
        super().__init__('paypal')
        # Usar configuración de BD si está disponible, sino variables de entorno
        if config:
            self.client_id = config.get_paypal_client_id()
            self.client_secret = config.get_paypal_client_secret()
            self.mode = config.paypal_mode or 'sandbox'
            self.return_url = config.paypal_return_url or os.getenv('PAYPAL_RETURN_URL', '')
            self.cancel_url = config.paypal_cancel_url or os.getenv('PAYPAL_CANCEL_URL', '')
        else:
            self.client_id = os.getenv('PAYPAL_CLIENT_ID', '')
            self.client_secret = os.getenv('PAYPAL_CLIENT_SECRET', '')
            self.mode = os.getenv('PAYPAL_MODE', 'sandbox')
            self.return_url = os.getenv('PAYPAL_RETURN_URL', '')
            self.cancel_url = os.getenv('PAYPAL_CANCEL_URL', '')
        self.base_url = 'https://api-m.sandbox.paypal.com' if self.mode == 'sandbox' else 'https://api-m.paypal.com'
        self.access_token = None
    
    def _get_access_token(self):
        """Obtener token de acceso de PayPal"""
        import requests
        
        if not self.client_id or not self.client_secret:
            return None
        
        url = f"{self.base_url}/v1/oauth2/token"
        headers = {
            'Accept': 'application/json',
            'Accept-Language': 'en_US'
        }
        data = {
            'grant_type': 'client_credentials'
        }
        
        try:
            response = requests.post(
                url,
                headers=headers,
                data=data,
                auth=(self.client_id, self.client_secret)
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                return self.access_token
            else:
                print(f"Error obteniendo token PayPal: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Excepción obteniendo token PayPal: {e}")
            return None
    
    def create_payment(self, amount, currency='USD', metadata=None):
        """Crear orden de pago en PayPal"""
        import requests
        
        if not self.client_id or not self.client_secret:
            return False, None, "PayPal no está configurado. Configura PAYPAL_CLIENT_ID y PAYPAL_CLIENT_SECRET"
        
        access_token = self._get_access_token()
        if not access_token:
            return False, None, "No se pudo obtener token de acceso de PayPal"
        
        # Convertir amount de centavos a dólares
        amount_value = amount / 100.0
        
        url = f"{self.base_url}/v2/checkout/orders"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        
        # URL de retorno
        return_url = self.return_url or os.getenv('PAYPAL_RETURN_URL', 'http://localhost:8080/payment/paypal/return')
        cancel_url = self.cancel_url or os.getenv('PAYPAL_CANCEL_URL', 'http://localhost:8080/payment/paypal/cancel')
        
        data = {
            'intent': 'CAPTURE',
            'purchase_units': [{
                'amount': {
                    'currency_code': currency,
                    'value': f"{amount_value:.2f}"
                }
            }],
            'application_context': {
                'return_url': return_url,
                'cancel_url': cancel_url,
                'brand_name': 'RELATIC Panamá'
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 201:
                order_data = response.json()
                
                # Buscar link de aprobación
                approval_url = None
                for link in order_data.get('links', []):
                    if link.get('rel') == 'approve':
                        approval_url = link.get('href')
                        break
                
                return True, {
                    'payment_reference': order_data.get('id'),
                    'payment_url': approval_url,
                    'order_data': order_data
                }, None
            else:
                error_msg = f"Error creando orden PayPal: {response.status_code} - {response.text}"
                return False, None, error_msg
        except Exception as e:
            return False, None, str(e)
    
    def verify_payment(self, payment_reference):
        """Verificar estado de la orden en PayPal"""
        import requests
        
        if not self.access_token:
            self._get_access_token()
        
        if not self.access_token:
            return False, 'failed', None
        
        url = f"{self.base_url}/v2/checkout/orders/{payment_reference}"
        headers = {
            'Authorization': f'Bearer {self.access_token}'
        }
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                order_data = response.json()
                status = order_data.get('status', 'UNKNOWN')
                
                status_map = {
                    'COMPLETED': 'succeeded',
                    'APPROVED': 'pending',
                    'CREATED': 'pending',
                    'SAVED': 'pending',
                    'VOIDED': 'cancelled',
                    'PAYER_ACTION_REQUIRED': 'pending'
                }
                
                mapped_status = status_map.get(status, 'pending')
                
                return True, mapped_status, {
                    'status': status,
                    'order_data': order_data
                }
            else:
                return False, 'failed', {'error': f"HTTP {response.status_code}"}
        except Exception as e:
            return False, 'failed', {'error': str(e)}


class BancoGeneralProcessor(PaymentProcessor):
    """Procesador para pagos con Banco General (CyberSource)"""
    
    def __init__(self, config=None):
        super().__init__('banco_general')
        # Usar configuración de BD si está disponible, sino variables de entorno
        if config:
            self.merchant_id = config.get_banco_general_merchant_id()
            self.api_key = config.get_banco_general_api_key()
            self.shared_secret = config.banco_general_shared_secret or os.getenv('BANCO_GENERAL_SHARED_SECRET', '')
            self.base_url = config.banco_general_api_url or 'https://api.cybersource.com'
        else:
            self.merchant_id = os.getenv('BANCO_GENERAL_MERCHANT_ID', '')
            self.api_key = os.getenv('BANCO_GENERAL_API_KEY', '')
            self.shared_secret = os.getenv('BANCO_GENERAL_SHARED_SECRET', '')
            self.base_url = os.getenv('BANCO_GENERAL_API_URL', 'https://api.cybersource.com')
    
    def create_payment(self, amount, currency='USD', metadata=None):
        """
        Crear enlace de pago con Banco General
        Por ahora retorna estructura para método manual hasta que se configure la API
        """
        # Si no hay credenciales, usar método manual
        if not self.merchant_id or not self.api_key:
            # Generar número de referencia único
            import secrets
            reference = f"BG-{secrets.token_hex(8).upper()}"
            
            return True, {
                'payment_reference': reference,
                'payment_url': None,  # Se mostrarán datos bancarios
                'manual': True,
                'bank_account': {
                    'bank': 'Banco General',
                    'account_type': 'Cuenta Corriente',
                    'account_number': '03-78-01-089981-8',
                    'account_name': 'Multi Servicios TK'
                }
            }, None
        
        # TODO: Implementar API de CyberSource cuando se tengan las credenciales
        # Por ahora retorna método manual
        import secrets
        reference = f"BG-{secrets.token_hex(8).upper()}"
        
        return True, {
            'payment_reference': reference,
            'payment_url': None,
            'manual': True,
            'bank_account': {
                'bank': 'Banco General',
                'account_type': 'Cuenta Corriente',
                'account_number': '03-78-01-089981-8',
                'account_name': 'Multi Servicios TK'
            }
        }, None
    
    def verify_payment(self, payment_reference):
        """Verificar pago - requiere confirmación manual"""
        # Los pagos de Banco General requieren confirmación manual
        return True, 'awaiting_confirmation', {
            'note': 'Pago requiere confirmación manual'
        }


class YappyProcessor(PaymentProcessor):
    """Procesador para pagos con Yappy"""
    
    def __init__(self, config=None):
        super().__init__('yappy')
        # Usar configuración de BD si está disponible, sino variables de entorno
        if config:
            self.api_key = config.get_yappy_api_key()
            self.merchant_id = config.yappy_merchant_id or os.getenv('YAPPY_MERCHANT_ID', '')
            self.base_url = config.yappy_api_url or 'https://api.yappy.im'
        else:
            self.api_key = os.getenv('YAPPY_API_KEY', '')
            self.merchant_id = os.getenv('YAPPY_MERCHANT_ID', '')
            self.base_url = os.getenv('YAPPY_API_URL', 'https://api.yappy.im')
    
    def create_payment(self, amount, currency='USD', metadata=None):
        """
        Crear pago con Yappy
        Por ahora retorna estructura para método manual hasta que se configure la API
        """
        import secrets
        reference = f"YAPPY-{secrets.token_hex(8).upper()}"
        
        return True, {
            'payment_reference': reference,
            'payment_url': None,
            'manual': True,
            'yappy_info': {
                'directorio': '@multiservicio',
                'nombre': 'Multiservicios TK'
            }
        }, None
    
    def verify_payment(self, payment_reference):
        """Verificar pago - requiere confirmación manual"""
        return True, 'awaiting_confirmation', {
            'note': 'Pago requiere confirmación manual'
        }


class InterbankProcessor(PaymentProcessor):
    """Procesador para pagos con Interbank (transferencia bancaria)"""
    
    def __init__(self):
        super().__init__('interbank')
    
    def create_payment(self, amount, currency='USD', metadata=None):
        """Crear referencia de pago para Interbank"""
        import secrets
        reference = f"INTERBANK-{secrets.token_hex(8).upper()}"
        
        return True, {
            'payment_reference': reference,
            'payment_url': None,
            'manual': True,
            'bank_account': {
                'bank': 'Interbank',
                'account_type': 'Cuenta de Ahorros',
                'account_number': '898-346625274-5',
                'cci': '003-898-013466252745-43',
                'titular': 'Poma Gonzáles Sósimo Misael'
            }
        }, None
    
    def verify_payment(self, payment_reference):
        """Verificar pago - requiere confirmación manual"""
        return True, 'awaiting_confirmation', {
            'note': 'Pago requiere confirmación manual'
        }


def get_payment_processor(payment_method, config=None):
    """Factory para obtener el procesador de pago correcto"""
    processors = {
        'stripe': StripeProcessor,
        'paypal': PayPalProcessor,
        'banco_general': BancoGeneralProcessor,
        'yappy': YappyProcessor,
        'interbank': InterbankProcessor
    }
    
    processor_class = processors.get(payment_method)
    if processor_class:
        return processor_class(config)
    else:
        raise ValueError(f"Método de pago no soportado: {payment_method}")

