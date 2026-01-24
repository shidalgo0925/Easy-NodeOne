#!/usr/bin/env python3
"""
Script de prueba para verificar la conexión con Odoo
"""

import os
import sys
import json
import hmac
import hashlib
import requests
from datetime import datetime

def test_odoo_connection():
    """Prueba la conexión con Odoo"""
    
    print("🧪 Probando conexión con Odoo...")
    print("")
    
    # Obtener configuración
    api_url = os.getenv('ODOO_API_URL', 'https://odoo.relatic.org/api/relatic/v1/sale')
    api_key = os.getenv('ODOO_API_KEY', '')
    hmac_secret = os.getenv('ODOO_HMAC_SECRET', '')
    enabled = os.getenv('ODOO_INTEGRATION_ENABLED', 'false').lower() == 'true'
    
    print(f"📋 Configuración:")
    print(f"   URL: {api_url}")
    print(f"   Habilitado: {enabled}")
    print(f"   API Key: {'✅ Configurada' if api_key and api_key != 'CAMBIAR_CON_API_KEY_REAL' else '❌ No configurada'}")
    print(f"   HMAC Secret: {'✅ Configurada' if hmac_secret and hmac_secret != 'CAMBIAR_CON_HMAC_SECRET_REAL' else '❌ No configurada'}")
    print("")
    
    if not enabled:
        print("⚠️  Integración deshabilitada (ODOO_INTEGRATION_ENABLED=false)")
        return False
    
    if not api_key or api_key == 'CAMBIAR_CON_API_KEY_REAL':
        print("❌ API Key no configurada o tiene valor por defecto")
        print("   Configura ODOO_API_KEY en el servicio systemd")
        return False
    
    if not hmac_secret or hmac_secret == 'CAMBIAR_CON_HMAC_SECRET_REAL':
        print("❌ HMAC Secret no configurado o tiene valor por defecto")
        print("   Configura ODOO_HMAC_SECRET en el servicio systemd")
        return False
    
    # Crear payload de prueba
    test_payload = {
        'meta': {
            'version': '1.0',
            'source': 'membresia-relatic',
            'environment': 'test',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        },
        'order_id': 'TEST-ORDER-001',
        'member': {
            'email': 'test@relatic.test',
            'name': 'Usuario de Prueba',
            'vat': '',
            'phone': ''
        },
        'items': [
            {
                'sku': 'MEMB-ANUAL',
                'name': 'Membresía Anual (Prueba)',
                'qty': 1,
                'price': 120.00,
                'tax_rate': 7.0
            }
        ],
        'payment': {
            'method': 'TARJETA',
            'amount': 128.40,
            'reference': 'TEST-REF-001',
            'date': datetime.utcnow().strftime('%Y-%m-%d'),
            'currency': 'USD'
        }
    }
    
    # Generar firma HMAC
    payload_json = json.dumps(test_payload, ensure_ascii=False)
    signature = hmac.new(
        hmac_secret.encode('utf-8'),
        payload_json.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Preparar headers
    headers = {
        'Authorization': f'Bearer {api_key}',
        'X-Relatic-Signature': signature,
        'Content-Type': 'application/json'
    }
    
    print("📤 Enviando request de prueba...")
    print(f"   Order ID: {test_payload['order_id']}")
    print("")
    
    try:
        response = requests.post(
            api_url,
            json=test_payload,
            headers=headers,
            timeout=10
        )
        
        print(f"📥 Respuesta recibida:")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            print("   ✅ Conexión exitosa!")
            print(f"   Order ID: {response_data.get('data', {}).get('order_id', 'N/A')}")
            print(f"   Factura: {response_data.get('data', {}).get('invoice_number', 'N/A')}")
            return True
        elif response.status_code == 401:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get('error', {}).get('message', 'Error de autenticación')
            print(f"   ❌ Error de autenticación: {error_msg}")
            print("")
            print("   Posibles causas:")
            print("   - API Key incorrecta")
            print("   - HMAC Secret incorrecto")
            print("   - Verificar que coincidan con los valores en Odoo")
            return False
        elif response.status_code == 422:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get('error', {}).get('message', 'Error de validación')
            print(f"   ⚠️  Error de validación: {error_msg}")
            print("   (Esto es normal en una prueba - el Order ID ya existe o falta configuración en Odoo)")
            return True  # Consideramos esto como éxito de conexión
        else:
            print(f"   ⚠️  Status inesperado: {response.status_code}")
            print(f"   Respuesta: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print("   ❌ Timeout al conectar con Odoo")
        print("   Verificar que el servidor de Odoo esté accesible")
        return False
    
    except requests.exceptions.ConnectionError:
        print("   ❌ Error de conexión con Odoo")
        print(f"   Verificar que {api_url} sea accesible")
        return False
    
    except Exception as e:
        print(f"   ❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    # Cargar variables de entorno del servicio systemd si están disponibles
    # Esto simula cómo las carga el servicio
    try:
        import subprocess
        result = subprocess.run(
            ['systemctl', 'show', 'membresia-relatic.service'],
            capture_output=True,
            text=True
        )
        for line in result.stdout.split('\n'):
            if line.startswith('Environment='):
                env_vars = line.replace('Environment=', '').split(' ')
                for var in env_vars:
                    if '=' in var:
                        key, value = var.split('=', 1)
                        # Remover comillas si existen
                        value = value.strip('"')
                        os.environ[key] = value
    except:
        pass
    
    success = test_odoo_connection()
    print("")
    if success:
        print("✅ Prueba completada exitosamente")
        sys.exit(0)
    else:
        print("❌ Prueba falló - Revisar configuración")
        sys.exit(1)
