#!/usr/bin/env python3
"""
Script para probar la integración de Yappy API
"""

import sys
import os

# Agregar el directorio backend al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import app, db, PaymentConfig
from payment_processors import get_payment_processor

def test_yappy_config():
    """Probar que la configuración de Yappy esté correcta"""
    print("=" * 60)
    print("🔍 PRUEBA 1: Verificar Configuración de Yappy")
    print("=" * 60)
    
    with app.app_context():
        config = PaymentConfig.get_active_config()
        
        if not config:
            print("❌ No hay configuración de pagos activa")
            return False
        
        api_key = config.get_yappy_api_key()
        merchant_id = config.yappy_merchant_id
        api_url = config.yappy_api_url
        
        print(f"📋 API URL: {api_url}")
        print(f"📋 Merchant ID: {merchant_id if merchant_id else 'NO CONFIGURADO'}")
        print(f"📋 API Key: {'✅ Configurado' if api_key else '❌ NO CONFIGURADO'}")
        
        if not api_key or not merchant_id:
            print("\n⚠️ ADVERTENCIA: Faltan credenciales. La API usará modo manual como fallback.")
            return False
        
        print("\n✅ Configuración encontrada correctamente")
        return True

def test_yappy_processor():
    """Probar el procesador de Yappy"""
    print("\n" + "=" * 60)
    print("🔍 PRUEBA 2: Inicializar Procesador de Yappy")
    print("=" * 60)
    
    with app.app_context():
        config = PaymentConfig.get_active_config()
        processor = get_payment_processor('yappy', config)
        
        if not processor:
            print("❌ No se pudo crear el procesador de Yappy")
            return False
        
        print(f"✅ Procesador creado: {processor.__class__.__name__}")
        print(f"📋 API Key: {'✅' if processor.api_key else '❌'}")
        print(f"📋 Merchant ID: {processor.merchant_id if processor.merchant_id else '❌'}")
        print(f"📋 Base URL: {processor.base_url}")
        
        return True

def test_yappy_create_payment():
    """Probar crear un pago de prueba"""
    print("\n" + "=" * 60)
    print("🔍 PRUEBA 3: Crear Pago de Prueba (NO se procesará realmente)")
    print("=" * 60)
    
    with app.app_context():
        config = PaymentConfig.get_active_config()
        processor = get_payment_processor('yappy', config)
        
        # Crear un pago de prueba de $1.00 USD
        amount = 100  # En centavos
        metadata = {
            'description': 'Pago de prueba - NO PROCESAR',
            'return_url': 'https://ejemplo.com/return',
            'cancel_url': 'https://ejemplo.com/cancel'
        }
        
        print(f"💰 Monto: ${amount/100:.2f} USD")
        print("🔄 Intentando crear pago en API de Yappy...")
        
        try:
            success, payment_data, error = processor.create_payment(
                amount=amount,
                currency='USD',
                metadata=metadata
            )
            
            if success:
                print("✅ Pago creado exitosamente")
                print(f"📋 Referencia: {payment_data.get('payment_reference')}")
                
                if payment_data.get('payment_url'):
                    print(f"🔗 URL de pago: {payment_data.get('payment_url')}")
                    print("✅ API de Yappy respondió correctamente - Modo AUTOMÁTICO")
                else:
                    print("⚠️ No se recibió URL de pago - Modo MANUAL (fallback)")
                    if payment_data.get('api_error'):
                        print(f"   Error: {payment_data.get('api_error')}")
                
                if payment_data.get('yappy_transaction_id'):
                    print(f"📋 Transaction ID: {payment_data.get('yappy_transaction_id')}")
                
                return True, payment_data
            else:
                print(f"❌ Error al crear pago: {error}")
                return False, None
                
        except Exception as e:
            print(f"❌ Excepción al crear pago: {e}")
            import traceback
            traceback.print_exc()
            return False, None

def test_yappy_verify_payment(payment_reference):
    """Probar verificar un pago"""
    print("\n" + "=" * 60)
    print("🔍 PRUEBA 4: Verificar Estado de Pago")
    print("=" * 60)
    
    if not payment_reference:
        print("⚠️ No hay referencia de pago para verificar")
        return False
    
    with app.app_context():
        config = PaymentConfig.get_active_config()
        processor = get_payment_processor('yappy', config)
        
        print(f"🔍 Verificando pago: {payment_reference}")
        print("🔄 Consultando API de Yappy...")
        
        try:
            success, status, payment_data = processor.verify_payment(payment_reference)
            
            if success:
                print(f"✅ Verificación exitosa")
                print(f"📋 Estado: {status}")
                
                if payment_data:
                    if payment_data.get('yappy_status'):
                        print(f"📋 Estado Yappy: {payment_data.get('yappy_status')}")
                    if payment_data.get('note'):
                        print(f"📝 Nota: {payment_data.get('note')}")
                
                return True
            else:
                print(f"❌ Error al verificar: {payment_data.get('note', 'Error desconocido')}")
                return False
                
        except Exception as e:
            print(f"❌ Excepción al verificar: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_api_connection():
    """Probar conexión básica a la API"""
    print("\n" + "=" * 60)
    print("🔍 PRUEBA 5: Probar Conexión a API de Yappy")
    print("=" * 60)
    
    with app.app_context():
        config = PaymentConfig.get_active_config()
        processor = get_payment_processor('yappy', config)
        
        if not processor.api_key or not processor.merchant_id:
            print("⚠️ No hay credenciales configuradas - saltando prueba de conexión")
            return False
        
        # Intentar hacer una petición simple a la API
        print(f"🌐 Conectando a: {processor.base_url}")
        print("🔄 Probando conexión...")
        
        try:
            # Hacer una petición simple (puede fallar si el endpoint no existe, pero veremos el error)
            success, response, error = processor._make_api_request('/v1/health', method='GET')
            
            if success:
                print("✅ Conexión exitosa a la API")
                return True
            else:
                # Si falla, puede ser que el endpoint no exista, pero la conexión funciona
                if "404" in error or "Not Found" in error:
                    print("⚠️ API responde pero el endpoint de prueba no existe (esto es normal)")
                    print("   La conexión básica funciona correctamente")
                    return True
                else:
                    print(f"⚠️ Error en conexión: {error}")
                    print("   Esto puede ser normal si la API requiere autenticación específica")
                    return False
                    
        except Exception as e:
            print(f"⚠️ Error de conexión: {e}")
            print("   Esto puede ser normal si la API tiene restricciones")
            return False

def main():
    """Ejecutar todas las pruebas"""
    print("\n" + "🚀 INICIANDO PRUEBAS DE INTEGRACIÓN YAPPY API")
    print("=" * 60)
    
    results = {}
    
    # Prueba 1: Configuración
    results['config'] = test_yappy_config()
    
    # Prueba 2: Procesador
    results['processor'] = test_yappy_processor()
    
    # Prueba 3: Crear pago
    success, payment_data = test_yappy_create_payment()
    results['create_payment'] = success
    payment_reference = payment_data.get('payment_reference') if payment_data else None
    
    # Prueba 4: Verificar pago (solo si se creó uno)
    if payment_reference:
        results['verify_payment'] = test_yappy_verify_payment(payment_reference)
    else:
        results['verify_payment'] = None
    
    # Prueba 5: Conexión API
    results['api_connection'] = test_api_connection()
    
    # Resumen
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 60)
    
    for test_name, result in results.items():
        if result is None:
            status = "⏭️  Saltado"
        elif result:
            status = "✅ Pasó"
        else:
            status = "❌ Falló"
        print(f"{status} - {test_name}")
    
    # Conclusión
    print("\n" + "=" * 60)
    print("💡 CONCLUSIÓN")
    print("=" * 60)
    
    if results.get('config') and results.get('processor'):
        if results.get('create_payment'):
            if payment_data and payment_data.get('payment_url'):
                print("✅ La integración con API de Yappy está FUNCIONANDO correctamente")
                print("   El sistema puede crear pagos automáticamente")
            else:
                print("⚠️ La integración está configurada pero usa modo MANUAL")
                print("   Esto puede ser porque:")
                print("   - La API no respondió correctamente")
                print("   - Las credenciales no son válidas")
                print("   - El endpoint de la API es diferente")
        else:
            print("⚠️ Hay problemas al crear pagos")
    else:
        print("❌ La configuración básica tiene problemas")
        print("   Verifica que las credenciales estén guardadas correctamente")
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()


