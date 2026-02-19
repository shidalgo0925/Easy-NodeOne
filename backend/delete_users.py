#!/usr/bin/env python3
"""
Script para eliminar usuarios y todas sus transacciones relacionadas
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import (
    app, db, User, Membership, Subscription, Payment, EventRegistration, EventParticipant,
    Appointment, Advisor, Notification, EmailLog, ActivityLog, Event,
    Cart, CartItem, SocialAuth, DiscountApplication, HistoryTransaction,
)

# IDs de usuarios a eliminar (Lista de Usuarios: 47, 44, 9, 4)
USER_IDS_TO_DELETE = [47, 44, 9, 4]

# Emails (legacy): si se quieren eliminar por email, añadir aquí
USERS_TO_DELETE_BY_EMAIL = []


def _delete_user_and_related(user):
    """Elimina un usuario y todas sus relaciones. user ya cargado."""
    user_id = user.id
    user_name = f"{user.first_name} {user.last_name}"
    email = user.email
    print(f"\n📋 Eliminando usuario: {user_name} ({email}) ID: {user_id}")

    try:
        # 1. Eliminar membresías
        memberships = Membership.query.filter_by(user_id=user_id).all()
        if memberships:
            print(f"   🗑️  Eliminando {len(memberships)} membresía(s)...")
            for membership in memberships:
                db.session.delete(membership)
        
        # 2. Eliminar suscripciones
        subscriptions = Subscription.query.filter_by(user_id=user_id).all()
        if subscriptions:
            print(f"   🗑️  Eliminando {len(subscriptions)} suscripción(es)...")
            for subscription in subscriptions:
                db.session.delete(subscription)
        
        # 3. Eliminar pagos
        payments = Payment.query.filter_by(user_id=user_id).all()
        if payments:
            print(f"   🗑️  Eliminando {len(payments)} pago(s)...")
            for payment in payments:
                db.session.delete(payment)
        
        # 4. Eliminar registros de eventos
        event_registrations = EventRegistration.query.filter_by(user_id=user_id).all()
        if event_registrations:
            print(f"   🗑️  Eliminando {len(event_registrations)} registro(s) de evento(s)...")
            for registration in event_registrations:
                # Actualizar contador del evento si estaba confirmado
                if registration.registration_status == 'confirmed':
                    event = Event.query.get(registration.event_id)
                    if event and event.registered_count and event.registered_count > 0:
                        event.registered_count -= 1
                db.session.delete(registration)
        
        # 5. Eliminar participantes de eventos
        event_participants = EventParticipant.query.filter_by(user_id=user_id).all()
        if event_participants:
            print(f"   🗑️  Eliminando {len(event_participants)} participante(s) de evento(s)...")
            for participant in event_participants:
                db.session.delete(participant)
        
        # 6. Eliminar citas
        appointments = Appointment.query.filter_by(user_id=user_id).all()
        if appointments:
            print(f"   🗑️  Eliminando {len(appointments)} cita(s)...")
            for appointment in appointments:
                db.session.delete(appointment)
        
        # 7. Eliminar perfil de asesor
        if user.advisor_profile:
            print(f"   🗑️  Eliminando perfil de asesor...")
            db.session.delete(user.advisor_profile)
        
        # 8. Eliminar notificaciones
        notifications = Notification.query.filter_by(user_id=user_id).all()
        if notifications:
            print(f"   🗑️  Eliminando {len(notifications)} notificación(es)...")
            for notification in notifications:
                db.session.delete(notification)
        
        # 9. Eliminar logs de email (solo los relacionados con el usuario)
        email_logs = EmailLog.query.filter_by(recipient_id=user_id).all()
        if email_logs:
            print(f"   🗑️  Eliminando {len(email_logs)} log(s) de email...")
            for email_log in email_logs:
                db.session.delete(email_log)
        
        # 10. Eliminar logs de actividad
        activity_logs = ActivityLog.query.filter_by(user_id=user_id).all()
        if activity_logs:
            print(f"   🗑️  Eliminando {len(activity_logs)} log(s) de actividad...")
            for activity_log in activity_logs:
                db.session.delete(activity_log)

        # 10b. Carrito y items
        cart = Cart.query.filter_by(user_id=user_id).first()
        if cart:
            CartItem.query.filter_by(cart_id=cart.id).delete()
            db.session.delete(cart)
        # 10c. OAuth
        SocialAuth.query.filter_by(user_id=user_id).delete()
        # 10d. Aplicaciones de descuento
        DiscountApplication.query.filter_by(user_id=user_id).delete()
        # 10e. Historial: anular referencias
        HistoryTransaction.query.filter_by(owner_user_id=user_id).update({'owner_user_id': None})
        HistoryTransaction.query.filter(HistoryTransaction.actor_id == user_id).update({'actor_id': None})
        
        # 11. Limpiar referencias en eventos (no eliminar eventos, solo limpiar referencias)
        events_created = Event.query.filter_by(created_by=user_id).all()
        if events_created:
            print(f"   🔧 Limpiando referencias en {len(events_created)} evento(s) creado(s)...")
            for event in events_created:
                event.created_by = None
        
        events_moderated = Event.query.filter_by(moderator_id=user_id).all()
        if events_moderated:
            print(f"   🔧 Limpiando referencias en {len(events_moderated)} evento(s) moderado(s)...")
            for event in events_moderated:
                event.moderator_id = None
        
        events_administered = Event.query.filter_by(administrator_id=user_id).all()
        if events_administered:
            print(f"   🔧 Limpiando referencias en {len(events_administered)} evento(s) administrado(s)...")
            for event in events_administered:
                event.administrator_id = None
        
        events_speaker = Event.query.filter_by(speaker_id=user_id).all()
        if events_speaker:
            print(f"   🔧 Limpiando referencias en {len(events_speaker)} evento(s) como expositor...")
            for event in events_speaker:
                event.speaker_id = None
        
        # 12. Eliminar el usuario
        print(f"   🗑️  Eliminando usuario...")
        db.session.delete(user)
        
        # Confirmar cambios
        db.session.commit()
        print(f"   ✅ Usuario {user_name} eliminado exitosamente")
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"   ❌ Error al eliminar usuario: {e}")
        import traceback
        traceback.print_exc()
        return False


def delete_user_by_id(user_id):
    """Elimina usuario por ID."""
    user = User.query.get(user_id)
    if not user:
        print(f"⚠️  Usuario no encontrado ID: {user_id}")
        return False
    return _delete_user_and_related(user)


def delete_user_and_transactions(email):
    """Elimina usuario por email."""
    user = User.query.filter_by(email=email).first()
    if not user:
        print(f"⚠️  Usuario no encontrado: {email}")
        return False
    return _delete_user_and_related(user)


def main():
    """Función principal"""
    import sys

    to_delete_ids = USER_IDS_TO_DELETE
    to_delete_emails = USERS_TO_DELETE_BY_EMAIL
    total = len(to_delete_ids) + len(to_delete_emails)
    if total == 0:
        print("No hay usuarios configurados para eliminar (USER_IDS_TO_DELETE / USERS_TO_DELETE_BY_EMAIL).")
        return

    print("="*70)
    print("ELIMINACIÓN DE USUARIOS Y TRANSACCIONES")
    print("="*70)
    print(f"\n📋 Usuarios a eliminar: {total}")
    for uid in to_delete_ids:
        print(f"   - ID {uid}")
    for email in to_delete_emails:
        print(f"   - {email}")
    print("\n⚠️  ADVERTENCIA: Esta acción eliminará permanentemente usuarios y datos relacionados.")
    print("⚠️  Esta acción NO se puede deshacer!")

    if '--confirm' not in sys.argv:
        print("\n⚠️  Para ejecutar: python3 delete_users.py --confirm")
        return

    print("\n✅ Confirmación recibida. Procediendo...")
    print("\n" + "="*70)

    with app.app_context():
        deleted_count = 0
        failed_count = 0
        for uid in to_delete_ids:
            if delete_user_by_id(uid):
                deleted_count += 1
            else:
                failed_count += 1
        for email in to_delete_emails:
            if delete_user_and_transactions(email):
                deleted_count += 1
            else:
                failed_count += 1

        print("\n" + "="*70)
        print("RESUMEN")
        print("="*70)
        print(f"✅ Eliminados: {deleted_count}")
        if failed_count > 0:
            print(f"❌ Con errores: {failed_count}")
        print("\n✨ Proceso completado")

if __name__ == '__main__':
    main()

