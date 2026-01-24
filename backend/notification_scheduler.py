#!/usr/bin/env python3
"""
Sistema de tareas programadas para notificaciones
Verifica membresías expirando, citas próximas, etc.
"""

from datetime import datetime, timedelta
from app import app, db, User, Subscription, Appointment, NotificationEngine, Notification


def check_expiring_memberships():
    """Verificar membresías que están por expirar y enviar notificaciones"""
    with app.app_context():
        try:
            # Buscar membresías que expiran en 30, 15, 7 y 1 día
            today = datetime.utcnow().date()
            check_dates = [
                (today + timedelta(days=30), 30),
                (today + timedelta(days=15), 15),
                (today + timedelta(days=7), 7),
                (today + timedelta(days=1), 1)
            ]
            
            for check_date, days_left in check_dates:
                # Buscar suscripciones activas que expiran en la fecha específica
                subscriptions = Subscription.query.filter(
                    Subscription.status == 'active',
                    db.func.date(Subscription.end_date) == check_date
                ).all()
                
                for subscription in subscriptions:
                    user = User.query.get(subscription.user_id)
                    if user:
                        # Verificar si ya se envió notificación para este día
                        existing_notification = Notification.query.filter(
                            Notification.user_id == user.id,
                            Notification.notification_type == 'membership_expiring',
                            Notification.created_at >= datetime.utcnow() - timedelta(days=1)
                        ).first()
                        
                        if not existing_notification:
                            NotificationEngine.notify_membership_expiring(user, subscription, days_left)
                            print(f"✅ Notificación enviada a {user.email}: membresía expira en {days_left} días")
            
            # Verificar membresías expiradas
            expired_subscriptions = Subscription.query.filter(
                Subscription.status == 'active',
                db.func.date(Subscription.end_date) < today
            ).all()
            
            for subscription in expired_subscriptions:
                user = User.query.get(subscription.user_id)
                if user:
                    # Marcar suscripción como expirada
                    subscription.status = 'expired'
                    
                    # Verificar si ya se envió notificación
                    existing_notification = Notification.query.filter(
                        Notification.user_id == user.id,
                        Notification.notification_type == 'membership_expired',
                        Notification.created_at >= datetime.utcnow() - timedelta(days=1)
                    ).first()
                    
                    if not existing_notification:
                        NotificationEngine.notify_membership_expired(user, subscription)
                        print(f"✅ Notificación enviada a {user.email}: membresía expirada")
            
            db.session.commit()
            print(f"✅ Verificación de membresías completada: {datetime.utcnow()}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error verificando membresías: {e}")


def check_appointment_reminders():
    """Verificar citas próximas y enviar recordatorios"""
    with app.app_context():
        try:
            from app import Appointment, User, AdvisorProfile
            
            # Buscar citas confirmadas en las próximas 24 y 48 horas
            now = datetime.utcnow()
            reminder_times = [
                (now + timedelta(hours=24), 24),
                (now + timedelta(hours=48), 48)
            ]
            
            for reminder_time, hours_before in reminder_times:
                # Buscar citas en el rango de tiempo (ventana de 1 hora)
                start_window = reminder_time - timedelta(minutes=30)
                end_window = reminder_time + timedelta(minutes=30)
                
                appointments = Appointment.query.filter(
                    Appointment.status == 'confirmed',
                    Appointment.start_datetime >= start_window,
                    Appointment.start_datetime <= end_window
                ).all()
                
                for appointment in appointments:
                    user = User.query.get(appointment.user_id)
                    advisor = User.query.get(appointment.advisor_id) if appointment.advisor_id else None
                    
                    if user and advisor:
                        # Verificar si ya se envió recordatorio para esta hora
                        existing_notification = Notification.query.filter(
                            Notification.user_id == user.id,
                            Notification.notification_type == 'appointment_reminder',
                            Notification.created_at >= datetime.utcnow() - timedelta(hours=2)
                        ).first()
                        
                        if not existing_notification:
                            NotificationEngine.notify_appointment_reminder(appointment, user, advisor, hours_before)
                            print(f"✅ Recordatorio enviado a {user.email}: cita en {hours_before} horas")
            
            db.session.commit()
            print(f"✅ Verificación de recordatorios de citas completada: {datetime.utcnow()}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error verificando recordatorios de citas: {e}")


def verify_yappy_payments():
    """
    Verificar automáticamente pagos pendientes de Yappy usando MATCH AUTOMÁTICO
    por atributos invariantes (sin depender del webhook)
    
    Estrategia:
    1. Buscar pagos pendientes de Yappy (últimas 24 horas)
    2. Para cada pago, intentar buscar en Yappy API por monto + fecha
    3. Si encuentra transacción COMPLETED, hacer match automático
    4. Usar ventana de ±15 minutos para cron (más amplia que verificación manual)
    """
    from app import Payment, PaymentConfig, Cart, User
    from payment_processors import get_payment_processor
    from app import process_cart_after_payment, get_or_create_cart
    from app import NotificationEngine, Subscription
    from datetime import timedelta
    
    with app.app_context():
        try:
            # Buscar pagos pendientes de Yappy (últimas 24 horas)
            time_limit = datetime.utcnow() - timedelta(hours=24)
            pending_payments = Payment.query.filter(
                Payment.payment_method == 'yappy',
                Payment.status.in_(['pending', 'awaiting_confirmation']),
                Payment.created_at >= time_limit
            ).all()
            
            if not pending_payments:
                print("✅ No hay pagos pendientes de Yappy para verificar (últimas 24h)")
                return
            
            print(f"🔍 Verificando {len(pending_payments)} pagos pendientes de Yappy (últimas 24h)...")
            
            # Obtener configuración de pagos
            payment_config = PaymentConfig.get_active_config()
            if not payment_config:
                print("⚠️ No hay configuración de pagos activa")
                return
            
            processor = get_payment_processor('yappy', payment_config)
            
            verified_count = 0
            failed_count = 0
            no_match_count = 0
            multiple_matches_count = 0
            
            for payment in pending_payments:
                try:
                    # Si ya tiene yappy_transaction_id, verificar directamente
                    yappy_transaction_id = None
                    if payment.payment_metadata:
                        try:
                            import json
                            metadata = json.loads(payment.payment_metadata) if isinstance(payment.payment_metadata, str) else payment.payment_metadata
                            yappy_transaction_id = metadata.get('yappy_transaction_id') or metadata.get('transaction_id')
                        except:
                            pass
                    
                    if yappy_transaction_id:
                        print(f"🔍 Verificando pago {payment.id} con transaction_id: {yappy_transaction_id}")
                        success, status, payment_data = processor.verify_payment(yappy_transaction_id)
                        
                        if success and status == 'succeeded' and payment.status != 'succeeded':
                            # Actualizar estado
                            payment.status = 'succeeded'
                            payment.paid_at = datetime.utcnow()
                            if payment_data.get('raw_response'):
                                import json
                                payment.yappy_raw_response = json.dumps(payment_data.get('raw_response'))
                            db.session.commit()
                            
                            # Procesar carrito
                            cart = get_or_create_cart(payment.user_id)
                            if cart.get_items_count() > 0:
                                process_cart_after_payment(cart, payment)
                                cart.clear()
                                db.session.commit()
                            
                            # Notificación
                            try:
                                user = User.query.get(payment.user_id)
                                if user:
                                    subscription = Subscription.query.filter_by(payment_id=payment.id).first()
                                    if subscription:
                                        NotificationEngine.notify_membership_payment(user, payment, subscription)
                            except Exception as e:
                                print(f"   ⚠️ Error enviando notificación: {e}")
                            
                            verified_count += 1
                            print(f"   ✅ Pago {payment.id} confirmado")
                        continue
                    
                    # Si no tiene transaction_id, intentar verificar por nuestra referencia
                    # NOTA: Esto generalmente falla porque Yappy no conoce nuestra referencia interna
                    # El usuario debe ingresar el código EBOWR-XXXXXXXX para vincular el pago
                    print(f"🔍 Verificando pago {payment.id} por referencia interna: {payment.payment_reference}")
                    print(f"   ⚠️ Advertencia: Si falla, el usuario debe ingresar el código EBOWR-XXXXXXXX de Yappy")
                    success, status, payment_data = processor.verify_payment(payment.payment_reference)
                    
                    # Si la verificación indica que necesita transaction_id, no continuar
                    if success and payment_data.get('needs_transaction_id'):
                        print(f"   ⚠️ Pago {payment.id} requiere código de transacción de Yappy (EBOWR-XXXXXXXX)")
                        print(f"   💡 El usuario debe ingresar el código en la interfaz o usar el endpoint /api/payments/yappy/verify-by-code")
                        no_match_count += 1
                        continue
                    
                    if success and status == 'succeeded':
                        # Obtener transaction_id de la respuesta
                        yappy_transaction_id = payment_data.get('transaction_id')
                        
                        if yappy_transaction_id:
                            # Intentar match automático (ventana de 15 min para cron)
                            from app import auto_match_yappy_payment
                            matched_payment, match_result = auto_match_yappy_payment(
                                yappy_transaction_id,
                                payment_data,
                                time_window_minutes=15  # Ventana más amplia para cron
                            )
                            
                            if match_result == 'auto_matched':
                                # Procesar carrito y notificaciones
                                cart = get_or_create_cart(matched_payment.user_id)
                                if cart.get_items_count() > 0:
                                    process_cart_after_payment(cart, matched_payment)
                                    cart.clear()
                                    db.session.commit()
                                
                                try:
                                    user = User.query.get(matched_payment.user_id)
                                    if user:
                                        subscription = Subscription.query.filter_by(payment_id=matched_payment.id).first()
                                        if subscription:
                                            NotificationEngine.notify_membership_payment(user, matched_payment, subscription)
                                except Exception as e:
                                    print(f"   ⚠️ Error enviando notificación: {e}")
                                
                                verified_count += 1
                                print(f"   ✅ Pago {matched_payment.id} confirmado (match automático)")
                            elif match_result == 'no_match':
                                no_match_count += 1
                                print(f"   ⚠️ No se encontró match para transaction_id {yappy_transaction_id}")
                            elif match_result == 'multiple_matches':
                                multiple_matches_count += 1
                                print(f"   ⚠️ Múltiples matches para transaction_id {yappy_transaction_id} - requiere revisión manual")
                        else:
                            # Si no hay transaction_id pero el pago está succeeded, actualizar directamente
                            if payment.status != 'succeeded':
                                payment.status = 'succeeded'
                                payment.paid_at = datetime.utcnow()
                                if payment_data.get('raw_response'):
                                    import json
                                    payment.yappy_raw_response = json.dumps(payment_data.get('raw_response'))
                                db.session.commit()
                                
                                cart = get_or_create_cart(payment.user_id)
                                if cart.get_items_count() > 0:
                                    process_cart_after_payment(cart, payment)
                                    cart.clear()
                                    db.session.commit()
                                
                                verified_count += 1
                                print(f"   ✅ Pago {payment.id} confirmado")
                    
                    elif status == 'failed' and payment.status != 'failed':
                        print(f"❌ Pago {payment.id} ({payment.payment_reference}) falló en Yappy")
                        payment.status = 'failed'
                        db.session.commit()
                        failed_count += 1
                    elif status in ['pending', 'awaiting_confirmation']:
                        print(f"⏳ Pago {payment.id} ({payment.payment_reference}) aún pendiente")
                    else:
                        print(f"⚠️ No se pudo verificar pago {payment.id}: {payment_data.get('note', 'Error desconocido')}")
                        
                except Exception as e:
                    print(f"❌ Error verificando pago {payment.id}: {e}")
                    import traceback
                    traceback.print_exc()
                    failed_count += 1
            
            print(f"\n📊 Yappy Cron Job:")
            print(f"   ✅ Confirmados: {verified_count}")
            print(f"   ❌ Fallidos: {failed_count}")
            print(f"   ⚠️ Sin match: {no_match_count}")
            print(f"   ⚠️ Múltiples matches: {multiple_matches_count}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error en verificación automática de Yappy: {e}")
            import traceback
            traceback.print_exc()

def verify_paypal_payments():
    """Verificar automáticamente pagos pendientes de PayPal"""
    from app import Payment, PaymentConfig
    from payment_processors import get_payment_processor
    from app import process_cart_after_payment, get_or_create_cart
    from app import NotificationEngine, Subscription
    
    with app.app_context():
        try:
            # Buscar pagos pendientes de PayPal
            pending_payments = Payment.query.filter(
                Payment.payment_method == 'paypal',
                Payment.status.in_(['pending', 'awaiting_confirmation'])
            ).all()
            
            if not pending_payments:
                print("✅ No hay pagos pendientes de PayPal para verificar")
                return
            
            print(f"🔍 Verificando {len(pending_payments)} pagos pendientes de PayPal...")
            
            # Obtener configuración de pagos
            payment_config = PaymentConfig.get_active_config()
            if not payment_config:
                print("⚠️ No hay configuración de pagos activa")
                return
            
            processor = get_payment_processor('paypal', payment_config)
            
            verified_count = 0
            failed_count = 0
            
            for payment in pending_payments:
                if not payment.payment_reference:
                    print(f"⚠️ Pago {payment.id} no tiene order_id de PayPal, saltando...")
                    continue
                
                try:
                    # Verificar el pago con la API de PayPal
                    success, status, payment_data = processor.verify_payment(payment.payment_reference)
                    
                    if success:
                        # Si el pago fue confirmado
                        if status == 'succeeded' and payment.status != 'succeeded':
                            print(f"✅ Pago {payment.id} ({payment.payment_reference}) confirmado por PayPal")
                            
                            # Actualizar estado del pago
                            payment.status = 'succeeded'
                            payment.paid_at = datetime.utcnow()
                            db.session.commit()
                            
                            # Procesar carrito si aún no se ha procesado
                            cart = get_or_create_cart(payment.user_id)
                            if cart.get_items_count() > 0:
                                process_cart_after_payment(cart, payment)
                                cart.clear()
                                db.session.commit()
                                print(f"   ✅ Carrito procesado para usuario {payment.user_id}")
                            
                            # Enviar notificación al usuario
                            try:
                                from app import User
                                user = User.query.get(payment.user_id)
                                if user:
                                    subscription = Subscription.query.filter_by(payment_id=payment.id).first()
                                    if subscription:
                                        NotificationEngine.notify_membership_payment(user, payment, subscription)
                                        print(f"   ✅ Notificación enviada a {user.email}")
                            except Exception as e:
                                print(f"   ⚠️ Error enviando notificación: {e}")
                            
                            verified_count += 1
                            
                        elif status == 'failed' and payment.status != 'failed':
                            print(f"❌ Pago {payment.id} ({payment.payment_reference}) falló en PayPal")
                            payment.status = 'failed'
                            db.session.commit()
                            failed_count += 1
                            
                        # Si sigue pendiente, no hacer nada (solo log)
                        elif status == 'pending' or status == 'awaiting_confirmation':
                            print(f"⏳ Pago {payment.id} ({payment.payment_reference}) aún pendiente")
                    else:
                        print(f"⚠️ No se pudo verificar pago {payment.id}: {payment_data.get('error', 'Error desconocido') if isinstance(payment_data, dict) else str(payment_data)}")
                        
                except Exception as e:
                    print(f"❌ Error verificando pago {payment.id}: {e}")
                    import traceback
                    traceback.print_exc()
                    failed_count += 1
            
            print(f"\n📊 PayPal: {verified_count} confirmados, {failed_count} con errores")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error en verificación automática de PayPal: {e}")
            import traceback
            traceback.print_exc()

def verify_stripe_payments():
    """Verificar automáticamente pagos pendientes de Stripe/TCR"""
    from app import Payment, PaymentConfig
    from payment_processors import get_payment_processor
    from app import process_cart_after_payment, get_or_create_cart
    from app import NotificationEngine, Subscription
    
    with app.app_context():
        try:
            # Buscar pagos pendientes de Stripe/TCR
            pending_payments = Payment.query.filter(
                Payment.payment_method.in_(['stripe', 'tcr']),
                Payment.status.in_(['pending', 'awaiting_confirmation'])
            ).all()
            
            if not pending_payments:
                print("✅ No hay pagos pendientes de Stripe/TCR para verificar")
                return
            
            print(f"🔍 Verificando {len(pending_payments)} pagos pendientes de Stripe/TCR...")
            
            # Obtener configuración de pagos
            payment_config = PaymentConfig.get_active_config()
            if not payment_config:
                print("⚠️ No hay configuración de pagos activa")
                return
            
            processor = get_payment_processor('stripe', payment_config)
            
            verified_count = 0
            failed_count = 0
            
            for payment in pending_payments:
                if not payment.payment_reference:
                    print(f"⚠️ Pago {payment.id} no tiene payment_intent_id de Stripe, saltando...")
                    continue
                
                try:
                    # Verificar el pago con la API de Stripe
                    success, status, payment_data = processor.verify_payment(payment.payment_reference)
                    
                    if success:
                        # Si el pago fue confirmado
                        if status == 'succeeded' and payment.status != 'succeeded':
                            print(f"✅ Pago {payment.id} ({payment.payment_reference}) confirmado por Stripe")
                            
                            # Actualizar estado del pago
                            payment.status = 'succeeded'
                            payment.paid_at = datetime.utcnow()
                            db.session.commit()
                            
                            # Procesar carrito si aún no se ha procesado
                            cart = get_or_create_cart(payment.user_id)
                            if cart.get_items_count() > 0:
                                process_cart_after_payment(cart, payment)
                                cart.clear()
                                db.session.commit()
                                print(f"   ✅ Carrito procesado para usuario {payment.user_id}")
                            
                            # Enviar notificación al usuario
                            try:
                                from app import User
                                user = User.query.get(payment.user_id)
                                if user:
                                    subscription = Subscription.query.filter_by(payment_id=payment.id).first()
                                    if subscription:
                                        NotificationEngine.notify_membership_payment(user, payment, subscription)
                                        print(f"   ✅ Notificación enviada a {user.email}")
                            except Exception as e:
                                print(f"   ⚠️ Error enviando notificación: {e}")
                            
                            verified_count += 1
                            
                        elif status == 'failed' and payment.status != 'failed':
                            print(f"❌ Pago {payment.id} ({payment.payment_reference}) falló en Stripe")
                            payment.status = 'failed'
                            db.session.commit()
                            failed_count += 1
                            
                        # Si sigue pendiente, no hacer nada (solo log)
                        elif status == 'pending' or status == 'awaiting_confirmation':
                            print(f"⏳ Pago {payment.id} ({payment.payment_reference}) aún pendiente")
                    else:
                        error_msg = payment_data.get('error', 'Error desconocido') if isinstance(payment_data, dict) else str(payment_data)
                        print(f"⚠️ No se pudo verificar pago {payment.id}: {error_msg}")
                        
                except Exception as e:
                    print(f"❌ Error verificando pago {payment.id}: {e}")
                    import traceback
                    traceback.print_exc()
                    failed_count += 1
            
            print(f"\n📊 Stripe/TCR: {verified_count} confirmados, {failed_count} con errores")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error en verificación automática de Stripe: {e}")
            import traceback
            traceback.print_exc()

def verify_all_payments():
    """Verificar automáticamente pagos pendientes de TODOS los métodos de pago"""
    print(f"\n{'='*60}")
    print(f"🔍 Verificación automática de pagos - {datetime.utcnow()}")
    print(f"{'='*60}\n")
    
    verify_yappy_payments()  # Verificar pagos de Yappy
    verify_paypal_payments()  # Verificar pagos de PayPal
    verify_stripe_payments()  # Verificar pagos de Stripe/TCR
    
    print(f"\n{'='*60}")
    print(f"✅ Verificación de pagos completada: {datetime.utcnow()}")
    print(f"{'='*60}\n")

def run_scheduled_tasks():
    """Ejecutar todas las tareas programadas"""
    print(f"\n{'='*60}")
    print(f"Ejecutando tareas programadas: {datetime.utcnow()}")
    print(f"{'='*60}\n")
    
    check_expiring_memberships()
    check_appointment_reminders()
    verify_all_payments()  # Verificar pagos de TODOS los métodos automáticamente
    
    print(f"\n{'='*60}")
    print(f"Tareas programadas completadas: {datetime.utcnow()}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    run_scheduled_tasks()

