#!/usr/bin/env python3
"""
Script de diagnóstico para verificar pagos pendientes y problemas
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Agregar el directorio del backend al path
backend_dir = Path(__file__).parent
project_dir = backend_dir.parent
sys.path.insert(0, str(backend_dir))

# Cambiar al directorio del backend
os.chdir(backend_dir)

try:
    from app import app, db, Payment, PaymentConfig, User, Cart, CartItem
    from payment_processors import get_payment_processor
    from utils.organization import default_organization_id

    with app.app_context():
        print("\n" + "="*70)
        print("🔍 DIAGNÓSTICO DE PAGOS PENDIENTES - YAPPY")
        print("="*70 + "\n")
        
        # 1. Verificar configuración de Yappy
        print("1️⃣ VERIFICANDO CONFIGURACIÓN DE YAPPY")
        print("-" * 70)
        _def_oid = default_organization_id()
        payment_config = PaymentConfig.get_active_config(organization_id=_def_oid)
        print(f"   (config mostrada: tenant por defecto organization_id={_def_oid})")

        if not payment_config:
            print("❌ No hay configuración de pagos activa")
        else:
            yappy_api_key = payment_config.get_yappy_api_key()
            yappy_merchant_id = payment_config.yappy_merchant_id
            
            if yappy_api_key:
                masked_key = yappy_api_key[:10] + "..." + yappy_api_key[-4:] if len(yappy_api_key) > 14 else "***"
                print(f"✅ API Key configurada: {masked_key}")
            else:
                print("❌ API Key NO configurada")
            
            if yappy_merchant_id:
                print(f"✅ Merchant ID configurado: {yappy_merchant_id}")
            else:
                print("❌ Merchant ID NO configurado")
            
            use_env = payment_config.use_environment_variables
            print(f"📋 Usa variables de entorno: {'Sí' if use_env else 'No'}")
        
        print()
        
        # 2. Buscar pagos pendientes de Yappy
        print("2️⃣ BUSCANDO PAGOS PENDIENTES DE YAPPY")
        print("-" * 70)
        
        pending_payments = Payment.query.filter(
            Payment.payment_method == 'yappy',
            Payment.status.in_(['pending', 'awaiting_confirmation'])
        ).order_by(Payment.created_at.desc()).all()
        
        if not pending_payments:
            print("✅ No hay pagos pendientes de Yappy")
        else:
            print(f"⚠️ Encontrados {len(pending_payments)} pagos pendientes:\n")
            
            for payment in pending_payments:
                user = User.query.get(payment.user_id)
                user_email = user.email if user else "Usuario no encontrado"
                user_name = f"{user.first_name} {user.last_name}" if user else "N/A"
                
                # Calcular tiempo desde creación
                time_ago = datetime.utcnow() - payment.created_at
                hours_ago = time_ago.total_seconds() / 3600
                
                print(f"  📄 Pago ID: {payment.id}")
                print(f"     Usuario: {user_name} ({user_email})")
                print(f"     Monto: ${payment.amount / 100:.2f}")
                print(f"     Estado: {payment.status}")
                print(f"     Referencia: {payment.payment_reference}")
                print(f"     URL: {payment.payment_url[:80] if payment.payment_url else 'N/A'}...")
                print(f"     Creado: {payment.created_at.strftime('%Y-%m-%d %H:%M:%S')} ({hours_ago:.1f} horas atrás)")
                
                # Verificar si tiene carrito asociado
                cart = Cart.query.filter_by(user_id=payment.user_id).first()
                if cart:
                    items_count = CartItem.query.filter_by(cart_id=cart.id).count()
                    print(f"     Carrito: {items_count} items pendientes")
                else:
                    print(f"     Carrito: No encontrado")
                
                print()
        
        # 3. Verificar pagos recientes confirmados
        print("3️⃣ PAGOS RECIENTES CONFIRMADOS (últimas 24 horas)")
        print("-" * 70)
        
        recent_confirmed = Payment.query.filter(
            Payment.payment_method == 'yappy',
            Payment.status == 'succeeded',
            Payment.paid_at >= datetime.utcnow() - timedelta(hours=24)
        ).order_by(Payment.paid_at.desc()).all()
        
        if not recent_confirmed:
            print("ℹ️ No hay pagos confirmados en las últimas 24 horas")
        else:
            print(f"✅ {len(recent_confirmed)} pagos confirmados recientemente:\n")
            for payment in recent_confirmed[:5]:  # Mostrar solo los 5 más recientes
                user = User.query.get(payment.user_id)
                user_email = user.email if user else "Usuario no encontrado"
                print(f"  ✅ Pago ID: {payment.id} - ${payment.amount / 100:.2f} - {user_email} - {payment.paid_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print()
        
        # 4. Verificar si el procesador funciona
        print("4️⃣ VERIFICANDO PROCESADOR DE YAPPY")
        print("-" * 70)
        
        proc_config = payment_config
        if pending_payments:
            pc_user = PaymentConfig.get_active_config_for_user_id(pending_payments[0].user_id)
            if pc_user:
                proc_config = pc_user
                print(
                    f"   (procesador: tenant del pago pendiente user_id={pending_payments[0].user_id})"
                )

        if proc_config:
            try:
                processor = get_payment_processor('yappy', proc_config)
                print("✅ Procesador de Yappy inicializado correctamente")
                
                # Probar con un pago pendiente si existe
                if pending_payments:
                    test_payment = pending_payments[0]
                    print(f"\n🔄 Probando verificación con pago ID {test_payment.id}...")
                    print(f"   Referencia: {test_payment.payment_reference}")
                    
                    success, status, payment_data = processor.verify_payment(test_payment.payment_reference)
                    
                    if success:
                        print(f"   ✅ Verificación exitosa")
                        print(f"   Estado: {status}")
                        print(f"   Datos: {payment_data}")
                    else:
                        print(f"   ⚠️ No se pudo verificar: {payment_data.get('note', 'Error desconocido')}")
                else:
                    print("ℹ️ No hay pagos pendientes para probar")
                    
            except Exception as e:
                print(f"❌ Error inicializando procesador: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("⚠️ No se puede probar el procesador sin configuración")
        
        print()
        
        # 5. Verificar cron job
        print("5️⃣ VERIFICANDO CONFIGURACIÓN DE CRON JOB")
        print("-" * 70)
        
        import subprocess
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True, timeout=5)
            if 'verify_yappy' in result.stdout or 'verify_all_payments' in result.stdout:
                print("✅ Cron job configurado:")
                for line in result.stdout.split('\n'):
                    if 'verify' in line.lower() and 'yappy' in line.lower():
                        print(f"   {line}")
            else:
                print("❌ Cron job NO está configurado")
                print("   Debe ejecutarse cada 5 minutos:")
                print("   */5 * * * * python3 verify_yappy_payments_cron.py")
        except Exception as e:
            print(f"⚠️ No se pudo verificar cron job: {e}")
        
        print()
        
        # 6. Resumen y recomendaciones
        print("6️⃣ RESUMEN Y RECOMENDACIONES")
        print("-" * 70)
        
        if not payment_config or not payment_config.get_yappy_api_key():
            print("❌ PROBLEMA CRÍTICO: Yappy no está configurado")
            print("   → Configurar API Key y Merchant ID en /admin/payments")
        
        if pending_payments:
            print(f"⚠️ Hay {len(pending_payments)} pagos pendientes que requieren verificación")
            print("   → Ejecutar: python3 verify_yappy_payments_cron.py")
            print("   → O llamar: POST /api/payments/yappy/verify-all")
        
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True, timeout=5)
            if 'verify_yappy' not in result.stdout:
                print("❌ Cron job no configurado")
                print("   → Configurar cron job para verificación automática cada 5 minutos")
        except:
            pass
        
        print("\n" + "="*70)
        print("✅ Diagnóstico completado")
        print("="*70 + "\n")
        
except Exception as e:
    print(f"\n❌ Error en diagnóstico: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
