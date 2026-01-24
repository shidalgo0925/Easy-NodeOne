#!/usr/bin/env python3
"""
Script para procesar el carrito de un pago confirmado
Útil cuando un pago se confirma manualmente y necesita procesar el carrito
"""

import sys
import os
from pathlib import Path

# Agregar el directorio del backend al path
backend_dir = Path(__file__).parent
project_dir = backend_dir.parent
sys.path.insert(0, str(backend_dir))

os.chdir(backend_dir)

try:
    # Importar solo lo necesario
    from app import app, db, Payment, Cart, User, Subscription
    
    def process_cart_for_payment(payment_id):
        """Procesar carrito para un pago específico"""
        with app.app_context():
            payment = Payment.query.get(payment_id)
            
            if not payment:
                print(f"❌ Pago {payment_id} no encontrado")
                return False
            
            if payment.status != 'succeeded':
                print(f"⚠️ El pago {payment_id} no está confirmado (estado: {payment.status})")
                print(f"   Confirma el pago primero")
                return False
            
            print(f"📊 Procesando carrito para Payment ID: {payment_id}")
            print(f"   Usuario: {payment.user_id}")
            print(f"   Monto: ${payment.amount/100:.2f}")
            print(f"   Estado: {payment.status}")
            
            # Obtener carrito del usuario
            cart = Cart.query.filter_by(user_id=payment.user_id).first()
            
            if not cart:
                print(f"⚠️ No se encontró carrito para el usuario {payment.user_id}")
                # Verificar si ya hay suscripciones (puede que ya se procesó)
                subscriptions = Subscription.query.filter_by(payment_id=payment_id).count()
                if subscriptions > 0:
                    print(f"✅ Ya hay {subscriptions} suscripción(es) creada(s). El carrito ya fue procesado.")
                return False
            
            items_count = cart.get_items_count()
            print(f"   Items en carrito: {items_count}")
            
            if items_count == 0:
                print(f"ℹ️ El carrito ya está vacío. Verificando si ya se procesó...")
                subscriptions = Subscription.query.filter_by(payment_id=payment_id).count()
                if subscriptions > 0:
                    print(f"✅ Ya hay {subscriptions} suscripción(es). El carrito ya fue procesado.")
                return True
            
            # Procesar el carrito
            try:
                from app import process_cart_after_payment
                
                print(f"\n🔄 Procesando carrito...")
                subscriptions_created = process_cart_after_payment(cart, payment)
                
                print(f"✅ Carrito procesado exitosamente")
                print(f"   Suscripciones creadas: {len(subscriptions_created) if subscriptions_created else 0}")
                
                # Verificar notificaciones
                try:
                    from app import NotificationEngine
                    user = User.query.get(payment.user_id)
                    if user:
                        subscription = Subscription.query.filter_by(payment_id=payment.id).first()
                        if subscription:
                            print(f"\n📧 Enviando notificación de membresía...")
                            NotificationEngine.notify_membership_payment(user, payment, subscription)
                            print(f"✅ Correo de confirmación enviado a {user.email}")
                except Exception as e:
                    print(f"⚠️ Error enviando notificación: {e}")
                
                return True
                
            except Exception as e:
                print(f"❌ Error procesando carrito: {e}")
                import traceback
                traceback.print_exc()
                db.session.rollback()
                return False
    
    if __name__ == '__main__':
        if len(sys.argv) < 2:
            print("Uso: python3 process_cart_for_payment.py <payment_id>")
            sys.exit(1)
        
        payment_id = int(sys.argv[1])
        process_cart_for_payment(payment_id)

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
