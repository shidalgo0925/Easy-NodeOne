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
    'paypal': 'PayPal',
    'banco_general': 'Banco General',
    'yappy': 'Yappy'
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
            self.mode = config.get_paypal_mode()
            if getattr(config, 'use_environment_variables', False):
                self.return_url = (os.getenv('PAYPAL_RETURN_URL') or config.paypal_return_url or '').strip()
                self.cancel_url = (os.getenv('PAYPAL_CANCEL_URL') or config.paypal_cancel_url or '').strip()
            else:
                self.return_url = (config.paypal_return_url or os.getenv('PAYPAL_RETURN_URL', '') or '').strip()
                self.cancel_url = (config.paypal_cancel_url or os.getenv('PAYPAL_CANCEL_URL', '') or '').strip()
        else:
            self.client_id = os.getenv('PAYPAL_CLIENT_ID', '')
            self.client_secret = os.getenv('PAYPAL_CLIENT_SECRET', '')
            _m = (os.getenv('PAYPAL_MODE', 'sandbox') or 'sandbox').strip().lower()
            self.mode = 'live' if _m == 'live' else 'sandbox'
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
        import secrets

        if not self.client_id or not self.client_secret:
            # Mismo criterio que Stripe: sin credenciales, modo demo (carrito se completa localmente)
            return True, {
                'payment_reference': f'PAYPAL_DEMO_{secrets.token_hex(16)}',
                'payment_url': None,
                'demo_mode': True,
            }, None

        access_token = self._get_access_token()
        if not access_token:
            print(
                "⚠️ PayPal: OAuth falló (credenciales inválidas, modo sandbox vs live, o app no aprobada). "
                "Revisá PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET y PAYPAL_MODE. Usando modo demo."
            )
            return True, {
                'payment_reference': f'PAYPAL_DEMO_{secrets.token_hex(16)}',
                'payment_url': None,
                'demo_mode': True,
            }, None

        # Convertir amount de centavos a dólares
        amount_value = amount / 100.0
        
        url = f"{self.base_url}/v2/checkout/orders"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        
        # URL de retorno - incluir payment_id si está en metadata
        base_return_url = self.return_url or os.getenv('PAYPAL_RETURN_URL', 'http://localhost:8080/payment/paypal/return')
        base_cancel_url = self.cancel_url or os.getenv('PAYPAL_CANCEL_URL', 'http://localhost:8080/payment/paypal/cancel')
        
        # Si hay payment_id en metadata, agregarlo a las URLs
        payment_id = metadata.get('payment_id') if metadata else None
        if payment_id:
            separator = '&' if '?' in base_return_url else '?'
            return_url = f"{base_return_url}{separator}payment_id={payment_id}"
            separator = '&' if '?' in base_cancel_url else '?'
            cancel_url = f"{base_cancel_url}{separator}payment_id={payment_id}"
        else:
            return_url = base_return_url
            cancel_url = base_cancel_url
        
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
                'brand_name': 'Easy NodeOne'
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
    
    def capture_payment(self, order_id):
        """Capturar un pago de PayPal que está en estado APPROVED"""
        import requests
        
        if not self.access_token:
            self._get_access_token()
        
        if not self.access_token:
            return False, None, "No se pudo obtener token de acceso"
        
        url = f"{self.base_url}/v2/checkout/orders/{order_id}/capture"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        
        try:
            response = requests.post(url, headers=headers, json={})
            
            if response.status_code == 201:
                capture_data = response.json()
                status = capture_data.get('status', 'UNKNOWN')
                return True, status, capture_data
            else:
                error_msg = f"Error capturando orden PayPal: {response.status_code} - {response.text}"
                return False, None, error_msg
        except Exception as e:
            return False, None, str(e)
    
    def verify_payment(self, payment_reference):
        """Verificar estado de la orden en PayPal y capturar si es necesario"""
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
                
                # Si la orden está APPROVED, capturarla automáticamente
                if status == 'APPROVED':
                    print(f"🔄 Orden PayPal {payment_reference} está APPROVED, capturando...")
                    capture_success, capture_status, capture_data = self.capture_payment(payment_reference)
                    if capture_success:
                        status = capture_status or status
                        order_data = capture_data or order_data
                        print(f"✅ Orden PayPal {payment_reference} capturada exitosamente")
                    else:
                        print(f"⚠️ Error capturando orden PayPal: {capture_status}")
                
                status_map = {
                    'COMPLETED': 'succeeded',
                    'APPROVED': 'pending',  # Si aún está APPROVED después de intentar capturar
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
    
    def _make_api_request(self, endpoint, method='GET', data=None, timeout=15):
        """
        Hacer petición a la API de Yappy
        Timeout de 15 segundos para dar tiempo suficiente a la conexión
        """
        import requests
        import json
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
            'X-Merchant-Id': self.merchant_id
        }
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=timeout)
            else:
                return False, None, f"Método HTTP no soportado: {method}"
            
            response.raise_for_status()
            return True, response.json(), None
        except requests.exceptions.Timeout:
            return False, None, f"Timeout conectando a Yappy (más de {timeout}s)"
        except requests.exceptions.ConnectionError as e:
            return False, None, f"Error de conexión con Yappy: {str(e)}"
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('message', error_msg)
                except:
                    error_msg = e.response.text or error_msg
            return False, None, f"Error en API de Yappy: {error_msg}"
        except Exception as e:
            return False, None, f"Error inesperado: {str(e)}"
    
    def create_payment(self, amount, currency='USD', metadata=None):
        """
        Crear orden de pago con Botón de Pago Yappy
        Sigue el flujo: Backend → API Yappy → Botón de Pago → Webhook
        """
        import secrets
        import json
        from flask import url_for, request
        
        # Verificar que tenemos las credenciales necesarias
        if not self.api_key or not self.merchant_id:
            return False, None, "Yappy no está configurado. Configura YAPPY_API_KEY y YAPPY_MERCHANT_ID"
        
        # Generar referencia única interna para el pago
        reference = f"YAPPY-{secrets.token_hex(8).upper()}"
        
        # Convertir amount de centavos a dólares (si viene en centavos)
        amount_value = amount / 100.0 if amount >= 100 else amount
        
        # Obtener URLs de retorno y webhook desde metadata o generar
        base_url = metadata.get('base_url', '') if metadata else ''
        if not base_url and hasattr(request, 'host'):
            base_url = f"{request.scheme}://{request.host}"
        
        return_url = metadata.get('return_url', f"{base_url}/payment/yappy/return") if metadata else f"{base_url}/payment/yappy/return"
        cancel_url = metadata.get('cancel_url', f"{base_url}/payment/yappy/cancel") if metadata else f"{base_url}/payment/yappy/cancel"
        webhook_url = metadata.get('webhook_url', f"{base_url}/webhook/yappy") if metadata else f"{base_url}/webhook/yappy"
        
        # Preparar datos para crear la orden de pago en Yappy
        # Según documentación de Yappy Botón de Pago
        payment_data = {
            'merchantId': self.merchant_id,
            'amount': amount_value,
            'currency': currency.upper(),
            'reference': reference,  # ID interno de referencia
            'description': metadata.get('description', 'Membresía Easy NodeOne') if metadata else 'Membresía Easy NodeOne',
            'returnUrl': return_url,
            'cancelUrl': cancel_url,
            'webhookUrl': webhook_url  # URL donde Yappy notificará el resultado
        }
        
        # Intentar crear la orden de pago en la API de Yappy
        # Endpoint puede variar según documentación oficial de Yappy
        # Intentamos solo los endpoints más probables primero para evitar timeouts
        endpoints_to_try = [
            '/v1/payments',
            '/api/v1/payments'
        ]
        
        last_error = None
        last_response = None
        connection_error = False
        
        # Timeout de 15 segundos para dar tiempo suficiente a la conexión
        timeout = 15
        
        for endpoint in endpoints_to_try:
            print(f"🔄 Intentando crear orden en Yappy: {self.base_url}{endpoint}")
            success, response_data, error = self._make_api_request(endpoint, method='POST', data=payment_data, timeout=timeout)
            
            if success and response_data:
                last_response = response_data
                # Yappy devuelve URL del Botón de Pago
                payment_url = (
                    response_data.get('paymentUrl') or 
                    response_data.get('url') or 
                    response_data.get('redirectUrl') or
                    response_data.get('checkoutUrl') or
                    response_data.get('buttonUrl') or
                    response_data.get('payment_link') or
                    response_data.get('link')
                )
                yappy_transaction_id = (
                    response_data.get('transactionId') or 
                    response_data.get('id') or 
                    response_data.get('orderId') or
                    response_data.get('transaction_id')
                )
                
                if payment_url:
                    print(f"✅ Orden creada exitosamente en Yappy: {payment_url}")
                    return True, {
                        'payment_reference': reference,
                        'yappy_transaction_id': yappy_transaction_id,
                        'payment_url': payment_url,
                        'manual': False,
                        'yappy_info': {
                            'amount': amount_value,
                            'currency': currency.upper(),
                            'description': payment_data['description']
                        }
                    }, None
                else:
                    print(f"⚠️ API respondió pero sin payment_url. Respuesta: {response_data}")
            
            if error:
                last_error = error
                print(f"❌ Error en {endpoint}: {error}")
                # Si es un error de timeout o conexión, marcar y salir
                if 'Timeout' in error or 'conexión' in error.lower() or 'Connection' in error or 'timed out' in error.lower():
                    connection_error = True
                    print(f"⚠️ Error de conexión detectado, no intentando más endpoints")
                    break
        
        # Si hay error de conexión, retornar error (NO activar modo manual automáticamente)
        if connection_error:
            error_message = (
                f"La API de Yappy no está disponible en este momento. "
                f"Error: {last_error}. "
                f"Por favor, intenta más tarde o contacta al soporte."
            )
            print(f"❌ {error_message}")
            return False, None, error_message
        else:
            error_message = f"No se pudo crear orden de pago en Yappy"
            if last_error:
                error_message += f": {last_error}"
            if last_response:
                error_message += f" | Respuesta recibida: {last_response}"
        
        return False, None, error_message
    
    def verify_payment(self, payment_reference):
        """
        Verificar estado del pago consultando la API de Yappy
        Puede recibir payment_reference (nuestro) o yappy_transaction_id (de Yappy)
        
        Lógica mejorada:
        - Si el código es EBOWR-XXXXXXXX (formato de Yappy), usarlo directamente
        - Si el código es YAPPY-XXXXXXXX (nuestra referencia), intentar primero con ese código
        - Si falla con nuestra referencia, retornar error indicando que se necesita el transaction_id
        
        Retorna datos completos incluyendo fecha de creación para match automático
        """
        # Si no hay credenciales, retornar estado pendiente
        if not self.api_key or not self.merchant_id:
            return True, 'awaiting_confirmation', {
                'note': 'Pago requiere confirmación manual (API no configurada)',
                'raw_response': None
            }
        
        # Detectar el tipo de código recibido
        # Códigos de Yappy típicamente tienen formato EBOWR-XXXXXXXX o similar
        is_yappy_transaction_id = (
            payment_reference and 
            (payment_reference.startswith('EBOWR-') or 
             payment_reference.startswith('EBOWR') or
             len(payment_reference) > 10 and not payment_reference.startswith('YAPPY-'))
        )
        
        # Intentar consultar el pago en la API
        # Si es un código EBOWR (transaction_id de Yappy), usarlo directamente
        # Si es nuestra referencia YAPPY-XXXXXXXX, intentar primero con ese código
        endpoint = f"/v1/payments/{payment_reference}"
        
        success, response_data, error = self._make_api_request(endpoint, method='GET')
        
        # Si falla y es nuestra referencia interna (YAPPY-), el problema es que Yappy no conoce nuestra referencia
        # En este caso, necesitamos el transaction_id real de Yappy (EBOWR-XXXXXXXX)
        if not success and payment_reference and payment_reference.startswith('YAPPY-'):
            return True, 'awaiting_confirmation', {
                'note': f'No se pudo verificar con referencia interna {payment_reference}. Se requiere el código de transacción de Yappy (EBOWR-XXXXXXXX) para verificar el pago. Error: {error}',
                'raw_response': None,
                'needs_transaction_id': True
            }
        
        if success and response_data:
            # Mapear estados de Yappy a nuestros estados
            yappy_status = response_data.get('status', '').lower()
            
            status_map = {
                'completed': 'succeeded',
                'paid': 'succeeded',
                'success': 'succeeded',
                'succeeded': 'succeeded',
                'pending': 'pending',
                'processing': 'pending',
                'failed': 'failed',
                'cancelled': 'cancelled',
                'expired': 'failed'
            }
            
            mapped_status = status_map.get(yappy_status, 'awaiting_confirmation')
            
            # Extraer fecha de creación de la transacción (para match por ventana temporal)
            from datetime import datetime
            created_at_str = (
                response_data.get('createdAt') or 
                response_data.get('created_at') or 
                response_data.get('date') or
                response_data.get('timestamp')
            )
            created_at = None
            if created_at_str:
                try:
                    # Intentar parsear diferentes formatos de fecha
                    if isinstance(created_at_str, (int, float)):
                        created_at = datetime.fromtimestamp(created_at_str)
                    else:
                        # Intentar parsear ISO format
                        from dateutil import parser
                        created_at = parser.parse(created_at_str)
                except:
                    pass
            
            # Convertir amount a centavos si viene en dólares
            amount = response_data.get('amount', 0)
            if isinstance(amount, float) and amount < 100:
                # Probablemente está en dólares, convertir a centavos
                amount_cents = int(amount * 100)
            else:
                amount_cents = int(amount)
            
            return True, mapped_status, {
                'yappy_status': yappy_status,
                'transaction_id': response_data.get('transactionId') or response_data.get('id') or response_data.get('transaction_id'),
                'amount': amount_cents,  # Siempre en centavos
                'currency': response_data.get('currency', 'USD').upper(),
                'paid_at': response_data.get('paidAt') or response_data.get('completedAt') or response_data.get('paid_at'),
                'created_at': created_at,  # Fecha de creación para match por ventana temporal
                'raw_response': response_data,  # Respuesta completa para auditoría
                'note': f'Estado desde API: {yappy_status}'
            }
        else:
            # Si no se puede verificar, retornar estado pendiente
            return True, 'awaiting_confirmation', {
                'note': f'No se pudo verificar en API: {error}. Requiere confirmación manual.',
                'raw_response': None
            }


def get_payment_processor(payment_method, config=None):
    """Factory para obtener el procesador de pago correcto"""
    processors = {
        'paypal': PayPalProcessor,
        'banco_general': BancoGeneralProcessor,
        'yappy': YappyProcessor
    }
    
    processor_class = processors.get(payment_method)
    if processor_class:
        return processor_class(config)
    else:
        raise ValueError(f"Método de pago no soportado: {payment_method}")

