#!/usr/bin/env python3
"""
Script para verificar pagos pendientes de PayPal
Útil para procesar pagos que no fueron confirmados por el webhook
"""

import sys
import os

# Agregar el directorio del backend al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Payment, PaymentConfig, PAYMENT_PROCESSORS_AVAILABLE
from datetime import datetime, timedelta

def verify_pending_paypal_payments():
    """
    Verificar todos los pagos pendientes de PayPal y procesarlos si están confirmados
    """
    if not PAYMENT_PROCESSORS_AVAILABLE:
        print("❌ Sistema de pagos no disponible")
        return
    
    cfg_memo = {}
    proc_memo = {}

    # Buscar pagos pendientes de PayPal
    pending_payments = Payment.query.filter(
        Payment.payment_method == 'paypal',
        Payment.status.in_(['pending', 'awaiting_confirmation'])
    ).all()
    
    print(f"🔍 Encontrados {len(pending_payments)} pagos pendientes de PayPal")
    
    if not pending_payments:
        print("✅ No hay pagos pendientes")
        return
    
    processed_count = 0
    failed_count = 0
    still_pending_count = 0
    
    for payment in pending_payments:
        if not payment.payment_reference:
            print(f"⚠️ Pago {payment.id} no tiene order_id de PayPal, saltando...")
            continue
        
        print(f"\n📋 Verificando pago {payment.id} (Order ID: {payment.payment_reference})")
        print(f"   Usuario: {payment.user_id}, Monto: ${payment.amount/100:.2f}")
        
        try:
            processor, payment_config = PaymentConfig.processor_for_payment_user(
                payment, 'paypal', cfg_memo, proc_memo
            )
            if not processor or not payment_config:
                print("   ⚠️ Sin configuración de pagos para el tenant de este usuario, saltando...")
                failed_count += 1
                continue
            # Verificar el pago con PayPal
            success, status, payment_data = processor.verify_payment(payment.payment_reference)
            
            if success:
                print(f"   Estado en PayPal: {status}")
                
                if status == 'succeeded':
                    # Actualizar estado del pago
                    payment.status = 'succeeded'
                    payment.paid_at = datetime.utcnow()
                    db.session.commit()
                    
                    print(f"   ✅ Pago confirmado en PayPal")
                    
                    # Procesar carrito si aún no se ha procesado
                    from app import get_or_create_cart, process_cart_after_payment
                    cart = get_or_create_cart(payment.user_id)
                    process_cart_after_payment(cart, payment)
                    
                    print(f"   ✅ Carrito procesado y membresía activada")
                    
                    processed_count += 1
                elif status == 'pending':
                    print(f"   ⏳ Pago aún pendiente en PayPal")
                    still_pending_count += 1
                else:
                    print(f"   ❌ Pago falló o fue cancelado: {status}")
                    payment.status = 'failed'
                    db.session.commit()
                    failed_count += 1
            else:
                error_msg = payment_data.get('error', 'Error desconocido') if isinstance(payment_data, dict) else str(payment_data)
                print(f"   ❌ Error verificando pago: {error_msg}")
                failed_count += 1
                
        except Exception as e:
            print(f"   ❌ Excepción verificando pago: {e}")
            import traceback
            traceback.print_exc()
            failed_count += 1
    
    print(f"\n📊 Resumen:")
    print(f"   ✅ Procesados: {processed_count}")
    print(f"   ⏳ Aún pendientes: {still_pending_count}")
    print(f"   ❌ Fallidos: {failed_count}")
    print(f"   📋 Total verificados: {len(pending_payments)}")

def verify_specific_payment(payment_id):
    """
    Verificar un pago específico por su ID
    """
    payment = Payment.query.get(payment_id)
    
    if not payment:
        print(f"❌ Pago {payment_id} no encontrado")
        return
    
    if payment.payment_method != 'paypal':
        print(f"❌ Pago {payment_id} no es de PayPal (es {payment.payment_method})")
        return
    
    if payment.status == 'succeeded':
        print(f"✅ Pago {payment_id} ya está confirmado")
        return
    
    if not payment.payment_reference:
        print(f"❌ Pago {payment_id} no tiene order_id de PayPal")
        return
    
    print(f"🔍 Verificando pago {payment_id} (Order ID: {payment.payment_reference})")
    
    if not PAYMENT_PROCESSORS_AVAILABLE:
        print("❌ Sistema de pagos no disponible")
        return
    
    processor, payment_config = PaymentConfig.processor_for_payment_user(
        payment, 'paypal', None, None
    )
    if not processor or not payment_config:
        print("❌ Sin configuración de pagos para el tenant de este usuario")
        return

    try:
        success, status, payment_data = processor.verify_payment(payment.payment_reference)
        
        if success and status == 'succeeded':
            payment.status = 'succeeded'
            payment.paid_at = datetime.utcnow()
            db.session.commit()
            
            from app import get_or_create_cart, process_cart_after_payment
            cart = get_or_create_cart(payment.user_id)
            process_cart_after_payment(cart, payment)
            
            print(f"✅ Pago {payment_id} confirmado y procesado exitosamente")
        else:
            print(f"⚠️ Estado del pago: {status}")
            payment.status = status
            db.session.commit()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    with app.app_context():
        if len(sys.argv) > 1:
            # Verificar un pago específico
            payment_id = int(sys.argv[1])
            verify_specific_payment(payment_id)
        else:
            # Verificar todos los pendientes
            verify_pending_paypal_payments()
