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
                            try:
                                from nodeone.services.communication_dispatch import dispatch_membership_expiring

                                dispatch_membership_expiring(user, subscription, days_left)
                            except Exception:
                                pass
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
                        try:
                            from nodeone.services.communication_dispatch import dispatch_membership_expired

                            dispatch_membership_expired(user, subscription)
                        except Exception:
                            pass
                        print(f"✅ Notificación enviada a {user.email}: membresía expirada")
            
            db.session.commit()
            print(f"✅ Verificación de membresías completada: {datetime.utcnow()}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error verificando membresías: {e}")


def check_appointment_reminders():
    """Citas confirmadas: recordatorios ~24h y ~1h antes (start interpretado con APPOINTMENT_NAIVE_DATETIME_AS)."""
    with app.app_context():
        try:
            from app import Appointment, User, Advisor, appointment_start_datetime_as_utc_naive
            
            now = datetime.utcnow()
            reminder_specs = [
                (24, timedelta(hours=24), lambda a: not getattr(a, 'reminder_24h_sent_at', None)),
                (1, timedelta(hours=1), lambda a: not getattr(a, 'reminder_1h_sent_at', None)),
            ]
            # No filtrar por start_datetime en SQL: naive puede ser UTC o hora local (ver app.appointment_start_datetime_as_utc_naive).
            candidates = Appointment.query.filter(
                Appointment.status.in_(['CONFIRMADA', 'confirmed']),
                Appointment.start_datetime.isnot(None),
            ).all()
            
            for appointment in candidates:
                st_utc = appointment_start_datetime_as_utc_naive(appointment)
                if st_utc is None:
                    continue
                if st_utc < now - timedelta(days=1) or st_utc > now + timedelta(days=2):
                    continue
                user = User.query.get(appointment.user_id)
                adv = Advisor.query.get(appointment.advisor_id) if appointment.advisor_id else None
                advisor_user = adv.user if adv and getattr(adv, 'user', None) else None
                if not user or not advisor_user:
                    continue
                for hours_before, delta, should_send in reminder_specs:
                    if not should_send(appointment):
                        continue
                    target = now + delta
                    start_window = target - timedelta(minutes=30)
                    end_window = target + timedelta(minutes=30)
                    if not (start_window <= st_utc <= end_window):
                        continue
                    NotificationEngine.notify_appointment_reminder(
                        appointment, user, advisor_user, hours_before
                    )
                    try:
                        from nodeone.services.communication_dispatch import dispatch_appointment_reminder_member

                        dispatch_appointment_reminder_member(
                            appointment, user, advisor_user, hours_before, base_url=None
                        )
                    except Exception:
                        pass
                    print(f"✅ Recordatorio ({hours_before}h) para {user.email} cita id={appointment.id}")
            
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
            
            cfg_memo = {}
            proc_memo = {}
            verified_count = 0
            failed_count = 0
            no_match_count = 0
            multiple_matches_count = 0
            
            for payment in pending_payments:
                try:
                    processor, payment_config = PaymentConfig.processor_for_payment_user(
                        payment, 'yappy', cfg_memo, proc_memo
                    )
                    if not payment_config or not processor:
                        print(f"   ⚠️ Pago {payment.id}: sin configuración de pagos para el tenant del usuario")
                        continue
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
                                        try:
                                            from nodeone.services.communication_dispatch import (
                                                dispatch_membership_payment_confirmation,
                                            )

                                            dispatch_membership_payment_confirmation(
                                                user, payment, subscription
                                            )
                                        except Exception:
                                            pass
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
                                            NotificationEngine.notify_membership_payment(
                                                user, matched_payment, subscription
                                            )
                                            try:
                                                from nodeone.services.communication_dispatch import (
                                                    dispatch_membership_payment_confirmation,
                                                )

                                                dispatch_membership_payment_confirmation(
                                                    user, matched_payment, subscription
                                                )
                                            except Exception:
                                                pass
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
            
            cfg_memo = {}
            proc_memo = {}
            verified_count = 0
            failed_count = 0
            
            for payment in pending_payments:
                if not payment.payment_reference:
                    print(f"⚠️ Pago {payment.id} no tiene order_id de PayPal, saltando...")
                    continue
                
                try:
                    processor, payment_config = PaymentConfig.processor_for_payment_user(
                        payment, 'paypal', cfg_memo, proc_memo
                    )
                    if not payment_config or not processor:
                        print(f"⚠️ Pago {payment.id}: sin configuración de pagos para el tenant del usuario, saltando...")
                        continue
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
                                        try:
                                            from nodeone.services.communication_dispatch import (
                                                dispatch_membership_payment_confirmation,
                                            )

                                            dispatch_membership_payment_confirmation(
                                                user, payment, subscription
                                            )
                                        except Exception:
                                            pass
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
            
            cfg_memo = {}
            proc_memo = {}
            verified_count = 0
            failed_count = 0
            
            for payment in pending_payments:
                if not payment.payment_reference:
                    print(f"⚠️ Pago {payment.id} no tiene payment_intent_id de Stripe, saltando...")
                    continue
                
                try:
                    processor, payment_config = PaymentConfig.processor_for_payment_user(
                        payment, 'stripe', cfg_memo, proc_memo
                    )
                    if not payment_config or not processor:
                        print(f"⚠️ Pago {payment.id}: sin configuración de pagos para el tenant del usuario, saltando...")
                        continue
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
                                        try:
                                            from nodeone.services.communication_dispatch import (
                                                dispatch_membership_payment_confirmation,
                                            )

                                            dispatch_membership_payment_confirmation(
                                                user, payment, subscription
                                            )
                                        except Exception:
                                            pass
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
    verify_yappy_payments()
    verify_paypal_payments()
    verify_stripe_payments()
    print(f"\n{'='*60}")
    print(f"✅ Verificación de pagos completada: {datetime.utcnow()}")
    print(f"{'='*60}\n")


def verify_all_payments_stats():
    """
    Ejecuta verify_all_payments() y devuelve conteos de pendientes antes/después por canal.
    Usado por POST /api/admin/payments/verify-pending.
    Cada “confirmado” en la ejecución = pagos que dejaron de estar pendientes (succeeded o failed).
    """
    from app import Payment

    def _pending_counts():
        return {
            'yappy': Payment.query.filter(
                Payment.payment_method == 'yappy',
                Payment.status.in_(['pending', 'awaiting_confirmation']),
            ).count(),
            'paypal': Payment.query.filter(
                Payment.payment_method == 'paypal',
                Payment.status.in_(['pending', 'awaiting_confirmation']),
            ).count(),
            'stripe': Payment.query.filter(
                Payment.payment_method.in_(['stripe', 'tcr']),
                Payment.status.in_(['pending', 'awaiting_confirmation']),
            ).count(),
        }

    before = _pending_counts()
    verify_all_payments()
    after = _pending_counts()
    confirmed = {
        'yappy': max(0, before['yappy'] - after['yappy']),
        'paypal': max(0, before['paypal'] - after['paypal']),
        'stripe': max(0, before['stripe'] - after['stripe']),
    }
    return {
        'success': True,
        'summary': {
            'confirmed_in_this_run': confirmed,
            'pending_after': after,
            'total_confirmed': sum(confirmed.values()),
        },
    }


def send_crm_activity_email_alerts():
    """Enviar alertas por email para actividades CRM vencidas/por vencer."""
    with app.app_context():
        try:
            from app import (
                EmailLog,
                Mail,
                apply_email_config_from_db,
                apply_transactional_smtp_for_organization,
                email_service,
            )
            from utils.organization import default_organization_id
            from nodeone.modules.crm_api.models import CrmActivity, CrmLead
            from email_templates import _default_base_url, get_crm_activity_reminder_email
            from nodeone.services.crm_email import (
                build_crm_activity_reminder_email,
                crm_email_context_reminder_plain_esc,
            )

            if not Mail:
                print('⚠️ CRM alerts email: Flask-Mail no instalado')
                return

            last_smtp = [None]
            now = datetime.utcnow()
            next_24h = now + timedelta(hours=24)
            rows = CrmActivity.query.filter(
                CrmActivity.status.in_(('pending', 'overdue')),
                CrmActivity.assigned_to.isnot(None),
            ).order_by(CrmActivity.due_date.asc()).limit(1000).all()

            sent = 0
            skipped = 0
            for a in rows:
                due = a.due_date
                if due is None:
                    continue
                if due < now:
                    alert_kind = 'overdue'
                    alert_label = 'Actividad vencida'
                elif due.date() == now.date():
                    alert_kind = 'due_today'
                    alert_label = 'Actividad vence hoy'
                elif due <= next_24h:
                    alert_kind = 'due_soon'
                    alert_label = 'Actividad vence en próximas 24h'
                else:
                    continue

                user = User.query.get(int(a.assigned_to))
                if not user or not getattr(user, 'email', None):
                    continue
                lead = CrmLead.query.get(int(a.lead_id))
                lead_name = (lead.name if lead else f'Lead #{a.lead_id}')

                # Deduplicación por actividad/usuario/tipo de alerta en las últimas 20 horas.
                exists = EmailLog.query.filter(
                    EmailLog.recipient_id == user.id,
                    EmailLog.email_type == f'crm_activity_alert_{alert_kind}',
                    EmailLog.related_entity_type == 'crm_activity',
                    EmailLog.related_entity_id == int(a.id),
                    EmailLog.status == 'sent',
                    EmailLog.created_at >= now - timedelta(hours=20),
                ).first()
                if exists:
                    skipped += 1
                    continue

                due_text = due.strftime('%Y-%m-%d %H:%M UTC')
                crm_url = f"{_default_base_url().rstrip('/')}/admin/crm"
                recipient_name = (
                    f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip() or user.email
                )
                plain, esc = crm_email_context_reminder_plain_esc(
                    lead_name=lead_name,
                    activity_summary=a.summary,
                    activity_type=a.type,
                    due_text=due_text,
                    alert_label=alert_label,
                    alert_kind=alert_kind,
                    crm_url=crm_url,
                    assignee_name=recipient_name,
                )
                default_subject = f"[CRM] {alert_label}: {a.summary}"
                default_html = get_crm_activity_reminder_email(
                    lead_name,
                    a.summary,
                    a.type,
                    due_text,
                    alert_label,
                    crm_url,
                )
                default_text = f"{alert_label} | Lead: {lead_name} | Actividad: {a.summary} | Vence: {due_text}"
                org_id = int(getattr(a, 'organization_id', None) or 1)
                subject, html, text = build_crm_activity_reminder_email(
                    org_id,
                    plain,
                    esc,
                    default_subject=default_subject,
                    default_html=default_html,
                    default_text=default_text,
                )
                smtp_oid = int(
                    getattr(a, 'organization_id', None)
                    or getattr(user, 'organization_id', None)
                    or default_organization_id()
                )
                ok_smtp, cfg_id = apply_transactional_smtp_for_organization(
                    smtp_oid, skip_if_config_id=last_smtp[0]
                )
                if ok_smtp and cfg_id is not None:
                    last_smtp[0] = cfg_id
                if not ok_smtp or not email_service:
                    skipped += 1
                    continue
                ok = email_service.send_email(
                    subject=subject,
                    recipients=[user.email],
                    html_content=html,
                    text_content=text,
                    email_type=f'crm_activity_alert_{alert_kind}',
                    related_entity_type='crm_activity',
                    related_entity_id=int(a.id),
                    recipient_id=user.id,
                    recipient_name=recipient_name,
                )
                if ok:
                    sent += 1

            print(f"✅ CRM alerts email: enviados={sent}, omitidos={skipped}")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error CRM alerts email: {e}")
        finally:
            apply_email_config_from_db()


def run_scheduled_tasks():
    """Ejecutar todas las tareas programadas"""
    print(f"\n{'='*60}")
    print(f"Ejecutando tareas programadas: {datetime.utcnow()}")
    print(f"{'='*60}\n")
    
    check_expiring_memberships()
    check_appointment_reminders()
    send_crm_activity_email_alerts()
    verify_all_payments()  # Verificar pagos de TODOS los métodos automáticamente
    
    print(f"\n{'='*60}")
    print(f"Tareas programadas completadas: {datetime.utcnow()}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    run_scheduled_tasks()

