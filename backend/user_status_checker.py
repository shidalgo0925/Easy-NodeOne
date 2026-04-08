#!/usr/bin/env python3
"""
Módulo de Verificación de Estado del Usuario
Verifica todas las actividades pendientes y acciones requeridas del usuario
"""

from datetime import datetime, timedelta
from flask import current_app

class UserStatusChecker:
    """Clase para verificar el estado completo del usuario"""
    
    @staticmethod
    def _get_yappy_transaction_id(payment):
        """Obtener yappy_transaction_id desde payment_metadata"""
        if not payment.payment_metadata:
            return None
        try:
            import json
            metadata = json.loads(payment.payment_metadata) if isinstance(payment.payment_metadata, str) else payment.payment_metadata
            return metadata.get('yappy_transaction_id') or metadata.get('transaction_id')
        except:
            return None
    
    @staticmethod
    def check_user_status(user_id, db_session):
        """
        Verificar estado completo del usuario y retornar información de acciones pendientes
        
        Retorna un diccionario con:
        - pending_payments: Pagos pendientes de confirmación
        - upcoming_events: Eventos próximos
        - upcoming_appointments: Citas próximas
        - expiring_membership: Membresía por vencer
        - pending_notifications: Notificaciones no leídas
        - cart_items: Items en carrito
        - action_required: Acciones que el usuario debe realizar
        """
        # Importar modelos desde app
        # Nota: Se importan dentro de la función para evitar imports circulares
        try:
            from app import (
                Payment, Event, EventRegistration, Appointment, 
                Subscription, Notification, Cart, CartItem
            )
        except ImportError:
            # Si falla el import, intentar importar desde el contexto de Flask
            from flask import current_app
            with current_app.app_context():
                from app import (
                    Payment, Event, EventRegistration, Appointment, 
                    Subscription, Notification, Cart, CartItem
                )
        
        status = {
            'user_id': user_id,
            'checked_at': datetime.utcnow().isoformat(),
            'pending_payments': [],
            'upcoming_events': [],
            'upcoming_appointments': [],
            'expiring_membership': None,
            'pending_notifications': [],
            'cart_items': [],
            'action_required': [],
            'summary': {
                'total_pending_actions': 0,
                'urgent_actions': 0,
                'warnings': 0,
                'info': 0
            }
        }
        
        try:
            # ========== 1. VERIFICAR PAGOS PENDIENTES ==========
            pending_payments = Payment.query.filter(
                Payment.user_id == user_id,
                Payment.status.in_(['pending', 'awaiting_confirmation'])
            ).order_by(Payment.created_at.desc()).all()
            
            for payment in pending_payments:
                time_elapsed = (datetime.utcnow() - payment.created_at).total_seconds() / 60 if payment.created_at else 0
                minutes_elapsed = int(time_elapsed)
                
                payment_info = {
                    'id': payment.id,
                    'amount': payment.amount / 100.0,
                    'currency': payment.currency,
                    'payment_method': payment.payment_method,
                    'payment_reference': payment.payment_reference,
                    'yappy_transaction_id': UserStatusChecker._get_yappy_transaction_id(payment),
                    'status': payment.status,
                    'created_at': payment.created_at.isoformat() if payment.created_at else None,
                    'minutes_elapsed': minutes_elapsed,
                    'hours_elapsed': int(minutes_elapsed / 60),
                    'is_urgent': minutes_elapsed > 30,  # Más de 30 minutos es urgente
                    'can_verify_manually': minutes_elapsed > 5 and payment.payment_method == 'yappy',
                    'action': 'verify_payment' if payment.payment_method == 'yappy' and minutes_elapsed > 5 else 'wait'
                }
                
                status['pending_payments'].append(payment_info)
                
                # Agregar a acciones requeridas
                if minutes_elapsed > 5:
                    if payment.payment_method == 'yappy':
                        status['action_required'].append({
                            'type': 'payment_verification',
                            'priority': 'urgent' if minutes_elapsed > 30 else 'normal',
                            'title': f'Verificar pago de ${payment.amount/100:.2f}',
                            'message': f'Tu pago lleva {minutes_elapsed} minutos pendiente. Verifica con tu código de comprobante.',
                            'payment_id': payment.id,
                            'action_url': f'/payments/history'
                        })
                        status['summary']['urgent_actions'] += 1 if minutes_elapsed > 30 else 0
                        status['summary']['total_pending_actions'] += 1
            
            # ========== 2. VERIFICAR EVENTOS PRÓXIMOS ==========
            # Eventos en los próximos 7 días
            next_week = datetime.utcnow() + timedelta(days=7)
            
            upcoming_registrations = EventRegistration.query.join(Event).filter(
                EventRegistration.user_id == user_id,
                EventRegistration.registration_status == 'confirmed',
                Event.start_date >= datetime.utcnow(),
                Event.start_date <= next_week
            ).order_by(Event.start_date.asc()).limit(10).all()
            
            for registration in upcoming_registrations:
                event = registration.event
                days_until = (event.start_date - datetime.utcnow()).days if event.start_date else None
                
                event_info = {
                    'id': event.id,
                    'title': event.title,
                    'start_date': event.start_date.isoformat() if event.start_date else None,
                    'end_date': event.end_date.isoformat() if event.end_date else None,
                    'location': event.location,
                    'days_until': days_until,
                    'registration_id': registration.id,
                    'registration_status': registration.registration_status,
                    'is_today': days_until == 0 if days_until is not None else False,
                    'is_tomorrow': days_until == 1 if days_until is not None else False
                }
                
                status['upcoming_events'].append(event_info)
                
                # Agregar recordatorio si es hoy o mañana
                if days_until is not None and days_until <= 1:
                    status['action_required'].append({
                        'type': 'event_reminder',
                        'priority': 'normal',
                        'title': f'Evento próximo: {event.title}',
                        'message': f'Tu evento es {"hoy" if days_until == 0 else "mañana"}.',
                        'event_id': event.id,
                        'action_url': f'/events/{event.id}'
                    })
                    status['summary']['info'] += 1
            
            # ========== 3. VERIFICAR CITAS PRÓXIMAS ==========
            # Citas en las próximas 48 horas
            next_48h = datetime.utcnow() + timedelta(hours=48)
            
            upcoming_appointments = Appointment.query.filter(
                Appointment.user_id == user_id,
                Appointment.status.in_(['confirmed', 'pending', 'CONFIRMADA', 'PENDIENTE']),
                Appointment.start_datetime >= datetime.utcnow(),
                Appointment.start_datetime <= next_48h
            ).order_by(Appointment.start_datetime.asc()).limit(10).all()
            
            for appointment in upcoming_appointments:
                hours_until = (appointment.start_datetime - datetime.utcnow()).total_seconds() / 3600 if appointment.start_datetime else None
                
                appointment_info = {
                    'id': appointment.id,
                    'appointment_type': appointment.appointment_type.name if appointment.appointment_type else 'N/A',
                    'start_datetime': appointment.start_datetime.isoformat() if appointment.start_datetime else None,
                    'end_datetime': appointment.end_datetime.isoformat() if appointment.end_datetime else None,
                    'advisor_name': f"{appointment.advisor.first_name} {appointment.advisor.last_name}" if appointment.advisor else 'N/A',
                    'status': appointment.status,
                    'hours_until': round(hours_until, 1) if hours_until else None,
                    'is_today': hours_until is not None and hours_until < 24 and hours_until >= 0,
                    'is_tomorrow': hours_until is not None and hours_until >= 24 and hours_until < 48
                }
                
                status['upcoming_appointments'].append(appointment_info)
                
                # Agregar recordatorio si es en las próximas 24 horas
                if hours_until is not None and hours_until < 24 and hours_until >= 0:
                    status['action_required'].append({
                        'type': 'appointment_reminder',
                        'priority': 'normal',
                        'title': f'Cita programada: {appointment.appointment_type.name if appointment.appointment_type else "Cita"}',
                        'message': f'Tu cita es en {int(hours_until)} horas.',
                        'appointment_id': appointment.id,
                        'action_url': f'/appointments/{appointment.id}'
                    })
                    status['summary']['info'] += 1
            
            # ========== 4. VERIFICAR MEMBRESÍA POR VENCER ==========
            active_subscription = Subscription.query.filter(
                Subscription.user_id == user_id,
                Subscription.status == 'active',
                Subscription.end_date > datetime.utcnow()
            ).order_by(Subscription.end_date.asc()).first()
            
            if active_subscription:
                days_until_expiry = (active_subscription.end_date - datetime.utcnow()).days
                
                if days_until_expiry <= 30:  # Por vencer en 30 días o menos
                    status['expiring_membership'] = {
                        'subscription_id': active_subscription.id,
                        'membership_type': active_subscription.membership_type,
                        'end_date': active_subscription.end_date.isoformat(),
                        'days_until_expiry': days_until_expiry,
                        'is_expiring_soon': days_until_expiry <= 7,
                        'is_expired': False
                    }
                    
                    if days_until_expiry <= 7:
                        status['action_required'].append({
                            'type': 'membership_expiring',
                            'priority': 'urgent' if days_until_expiry <= 3 else 'normal',
                            'title': 'Membresía por vencer',
                            'message': f'Tu membresía vence en {days_until_expiry} días. Renueva ahora para continuar disfrutando de los beneficios.',
                            'subscription_id': active_subscription.id,
                            'action_url': '/membership'
                        })
                        status['summary']['urgent_actions'] += 1 if days_until_expiry <= 3 else 0
                        status['summary']['total_pending_actions'] += 1
            
            # Verificar si la membresía ya expiró
            expired_subscription = Subscription.query.filter(
                Subscription.user_id == user_id,
                Subscription.status == 'active',
                Subscription.end_date <= datetime.utcnow()
            ).first()
            
            if expired_subscription:
                status['expiring_membership'] = {
                    'subscription_id': expired_subscription.id,
                    'membership_type': expired_subscription.membership_type,
                    'end_date': expired_subscription.end_date.isoformat(),
                    'days_until_expiry': 0,
                    'is_expiring_soon': True,
                    'is_expired': True
                }
                
                status['action_required'].append({
                    'type': 'membership_expired',
                    'priority': 'urgent',
                    'title': 'Membresía expirada',
                    'message': 'Tu membresía ha expirado. Renueva ahora para reactivar tu cuenta.',
                    'subscription_id': expired_subscription.id,
                    'action_url': '/membership'
                })
                status['summary']['urgent_actions'] += 1
                status['summary']['total_pending_actions'] += 1
            
            # ========== 5. VERIFICAR NOTIFICACIONES PENDIENTES ==========
            unread_notifications = Notification.query.filter(
                Notification.user_id == user_id,
                Notification.is_read == False
            ).order_by(Notification.created_at.desc()).limit(20).all()
            
            for notification in unread_notifications:
                notification_info = {
                    'id': notification.id,
                    'type': notification.notification_type,
                    'title': notification.title,
                    'message': notification.message,
                    'created_at': notification.created_at.isoformat() if notification.created_at else None,
                    'is_read': notification.is_read,
                    'related_entity_type': getattr(notification, 'related_entity_type', None),
                    'related_entity_id': getattr(notification, 'related_entity_id', None),
                }
                
                status['pending_notifications'].append(notification_info)
            
            status['summary']['info'] += len(unread_notifications)
            
            # ========== 6. VERIFICAR ITEMS EN CARRITO ==========
            cart = Cart.query.filter_by(user_id=user_id).first()
            if cart:
                items = CartItem.query.filter_by(cart_id=cart.id).all()
                for item in items:
                    item_info = {
                        'id': item.id,
                        'product_type': item.product_type,
                        'product_name': item.product_name,
                        'quantity': item.quantity,
                        'price': item.price / 100.0 if item.price else 0,
                        'added_at': item.created_at.isoformat() if item.created_at else None
                    }
                    status['cart_items'].append(item_info)
                
                if items:
                    status['action_required'].append({
                        'type': 'cart_items',
                        'priority': 'normal',
                        'title': f'{len(items)} item(s) en tu carrito',
                        'message': 'Tienes items pendientes en tu carrito. Completa tu compra.',
                        'action_url': '/cart'
                    })
                    status['summary']['total_pending_actions'] += 1
            
            # ========== 7. CALCULAR RESUMEN FINAL ==========
            status['summary']['total_pending_actions'] = len(status['action_required'])
            status['summary']['warnings'] = len([a for a in status['action_required'] if a['priority'] == 'normal'])
            
        except Exception as e:
            print(f"❌ Error verificando estado del usuario {user_id}: {e}")
            import traceback
            traceback.print_exc()
            status['error'] = str(e)
        
        return status
    
    @staticmethod
    def get_user_dashboard_data(user_id, db_session):
        """
        Obtener datos completos para el dashboard del usuario
        Incluye estadísticas, resumen y acciones pendientes
        """
        from app import (
            Payment, Event, EventRegistration, Appointment,
            Subscription, Notification, Cart, Invoice
        )
        
        dashboard = {
            'user_id': user_id,
            'generated_at': datetime.utcnow().isoformat(),
            'statistics': {},
            'recent_activity': [],
            'status_check': UserStatusChecker.check_user_status(user_id, db_session)
        }
        
        try:
            # Estadísticas generales
            total_payments = Payment.query.filter_by(user_id=user_id).count()
            successful_payments = Payment.query.filter_by(user_id=user_id, status='succeeded').count()
            total_events = EventRegistration.query.filter_by(user_id=user_id).count()
            total_appointments = Appointment.query.filter_by(user_id=user_id).count()
            active_membership = Subscription.query.filter(
                Subscription.user_id == user_id,
                Subscription.status == 'active',
                Subscription.end_date > datetime.utcnow()
            ).first()
            
            dashboard['statistics'] = {
                'total_payments': total_payments,
                'successful_payments': successful_payments,
                'total_events_registered': total_events,
                'total_appointments': total_appointments,
                'has_active_membership': active_membership is not None,
                'membership_type': active_membership.membership_type if active_membership else None,
                'membership_expires': active_membership.end_date.isoformat() if active_membership else None
            }
            
            # Actividad reciente (últimos 10 pagos)
            recent_payments = Payment.query.filter_by(user_id=user_id).order_by(
                Payment.created_at.desc()
            ).limit(10).all()
            
            for payment in recent_payments:
                dashboard['recent_activity'].append({
                    'type': 'payment',
                    'id': payment.id,
                    'amount': payment.amount / 100.0,
                    'status': payment.status,
                    'method': payment.payment_method,
                    'date': payment.created_at.isoformat() if payment.created_at else None,
                    'paid_at': payment.paid_at.isoformat() if payment.paid_at else None
                })
            
        except Exception as e:
            print(f"❌ Error generando dashboard para usuario {user_id}: {e}")
            dashboard['error'] = str(e)
        
        return dashboard
