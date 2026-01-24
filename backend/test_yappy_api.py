#!/usr/bin/env python3
"""
Script para probar la conectividad con la API de Yappy
"""

import sys
import os
import requests
from pathlib import Path
from datetime import datetime

backend_dir = Path(__file__).parent
project_dir = backend_dir.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

try:
    from app import app, db, PaymentConfig
    
    with app.app_context():
        print("\n" + "="*70)
        print("🔍 PRUEBA DE CONECTIVIDAD CON API DE YAPPY")
        print("="*70 + "\n")
        
        payment_config = PaymentConfig.get_active_config()
        
        if not payment_config:
            print("❌ No hay configuración de pagos")
            sys.exit(1)
        
        api_key = payment_config.get_yappy_api_key()
        merchant_id = payment_config.yappy_merchant_id
        base_url = payment_config.yappy_api_url or 'https://api.yappy.im'
        
        print(f"📋 Configuración:")
        print(f"   Base URL: {base_url}")
        print(f"   Merchant ID: {merchant_id}")
        print(f"   API Key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else '***'}")
        print()
        
        # Probar diferentes endpoints
        endpoints_to_test = [
            '/v1/payments/test',
            '/v1/payments',
            '/api/v1/payments',
            '/health',
            '/status',
            '/',
        ]
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'X-Merchant-Id': merchant_id
        }
        
        print("🔄 Probando conectividad con diferentes endpoints...\n")
        
        for endpoint in endpoints_to_test:
            url = f"{base_url}{endpoint}"
            print(f"   Probando: {url}")
            
            try:
                # Intentar GET primero
                response = requests.get(url, headers=headers, timeout=10)
                print(f"      ✅ GET - Status: {response.status_code}")
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"      📄 Respuesta: {str(data)[:100]}...")
                    except:
                        print(f"      📄 Respuesta: {response.text[:100]}...")
                elif response.status_code == 404:
                    print(f"      ⚠️ Endpoint no encontrado (404)")
                elif response.status_code == 401:
                    print(f"      ⚠️ No autorizado (401) - Verificar credenciales")
                elif response.status_code == 403:
                    print(f"      ⚠️ Prohibido (403) - Verificar permisos")
                else:
                    print(f"      ⚠️ Status inesperado: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                print(f"      ❌ TIMEOUT (más de 10 segundos)")
            except requests.exceptions.ConnectionError as e:
                print(f"      ❌ Error de conexión: {str(e)[:80]}")
            except Exception as e:
                print(f"      ❌ Error: {str(e)[:80]}")
            
            print()
        
        # Probar con un pago específico
        print("🔄 Probando verificación de pago específico...\n")
        test_reference = "YAPPY-D298C08DE0C03D74"
        test_url = f"{base_url}/v1/payments/{test_reference}"
        
        print(f"   URL: {test_url}")
        try:
            response = requests.get(test_url, headers=headers, timeout=10)
            print(f"   ✅ Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   📄 Datos del pago: {data}")
            elif response.status_code == 404:
                print(f"   ⚠️ Pago no encontrado en Yappy")
            else:
                print(f"   ⚠️ Respuesta: {response.text[:200]}")
        except requests.exceptions.Timeout:
            print(f"   ❌ TIMEOUT - La API de Yappy no responde")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("\n" + "="*70)
        print("✅ Prueba completada")
        print("="*70 + "\n")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
