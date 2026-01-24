#!/usr/bin/env python3
"""
Script para verificar manualmente un pago de Yappy usando el código de referencia
Uso: python3 verify_yappy_payment_manual.py EBOWR-38807178
"""

import sys
import os

# Agregar el directorio del backend al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from payment_processors import get_payment_processor
from models import Payment, PaymentConfig

def verify_payment_by_code(receipt_code):
    """Verificar un pago usando el código de referencia de Yappy"""
    with app.app_context():
        try:
            print(f"🔍 Buscando pago con código: {receipt_code}")
            
            # Buscar el pago en la base de datos
            payment = Payment.query.filter(
                Payment.payment_method == 'yappy',
                db.or_(
                    Payment.payment_reference == receipt_code,
                    Payment.payment_reference.like(f'%{receipt_code}%')
                )
            ).first()
            
            if not payment:
                # Buscar en todos los pagos pendientes de Yappy
                print("⚠️ No se encontró pago con ese código exacto. Buscando en pagos pendientes...")
                pending_payments = Payment.query.filter(
                    Payment.payment_method == 'yappy',
                    Payment.status.in_(['pending', 'awaiting_confirmation'])
                ).all()
                
                print(f"📋 Encontrados {len(pending_payments)} pagos pendientes de Yappy")
                for p in pending_payments:
                    print(f"   - Payment ID: {p.id}, Reference: {p.payment_reference}, Amount: ${p.amount/100:.2f}, User: {p.user_id}")
                
                if not pending_payments:
                    print("❌ No se encontró ningún pago pendiente de Yappy")
                    return False
                
                # Usar el primer pago pendiente si hay varios
                payment = pending_payments[0]
                print(f"✅ Usando Payment ID: {payment.id}")
            else:
                print(f"✅ Pago encontrado: Payment ID: {payment.id}, Status: {payment.status}, Amount: ${payment.amount/100:.2f}")
            
            # Si ya está confirmado, informar
            if payment.status == 'succeeded':
                print(f"✅ El pago ya está confirmado (Status: {payment.status})")
                return True
            
            # Obtener configuración y procesador
            payment_config = PaymentConfig.get_active_config()
            if not payment_config:
                print("❌ No hay configuración de pagos activa")
                return False
            
            processor = get_payment_processor('yappy', payment_config)
            
            # Intentar verificar con el código
            print(f"🔄 Verificando pago con API de Yappy usando código: {receipt_code}")
            success, status, payment_data = processor.verify_payment(receipt_code)
            
            if success:
                print(f"📊 Resultado de la verificación:")
                print(f"   - Success: {success}")
                print(f"   - Status: {status}")
                print(f"   - Payment Data: {payment_data}")
                
                if status == 'succeeded':
                    # Actualizar estado del pago
                    old_status = payment.status
                    payment.status = 'succeeded'
                    payment.paid_at = db.datetime.utcnow()
                    payment.payment_reference = receipt_code  # Actualizar con el código real
                    db.session.commit()
                    
                    print(f"✅ Pago confirmado exitosamente!")
                    print(f"   - Estado anterior: {old_status} → Nuevo estado: {status}")
                    print(f"   - Payment ID: {payment.id}")
                    print(f"   - Reference actualizado: {payment.payment_reference}")
                    
                    # Procesar carrito
                    try:
                        from app import get_or_create_cart, process_cart_after_payment
                        cart = get_or_create_cart(payment.user_id)
                        process_cart_after_payment(cart, payment)
                        print(f"✅ Carrito procesado para usuario {payment.user_id}")
                    except Exception as e:
                        print(f"⚠️ Error procesando carrito: {e}")
                        import traceback
                        traceback.print_exc()
                    
                    return True
                else:
                    print(f"⚠️ El pago no está completado aún. Estado: {status}")
                    if payment_data:
                        print(f"   - Nota: {payment_data.get('note', 'N/A')}")
                    return False
            else:
                print(f"❌ No se pudo verificar el pago")
                if payment_data:
                    print(f"   - Error: {payment_data.get('note', 'N/A')}")
                return False
                
        except Exception as e:
            print(f"❌ Error verificando pago: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python3 verify_yappy_payment_manual.py <codigo_referencia>")
        print("Ejemplo: python3 verify_yappy_payment_manual.py EBOWR-38807178")
        sys.exit(1)
    
    receipt_code = sys.argv[1].strip()
    print(f"🔍 Verificando pago de Yappy con código: {receipt_code}\n")
    
    success = verify_payment_by_code(receipt_code)
    sys.exit(0 if success else 1)
