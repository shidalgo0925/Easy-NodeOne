"""Post-proceso de carrito tras pago y webhook Odoo."""

from datetime import datetime, timedelta

def send_payment_to_odoo(payment, user, cart=None):
    """
    Envía webhook a Odoo cuando se confirma un pago
    Esta función no debe interrumpir el flujo principal si falla
    """
    try:
        from odoo_integration_service import get_odoo_service
        
        # Obtener items del carrito si está disponible
        cart_items = None
        if cart:
            cart_items = list(cart.items)
        
        # Enviar webhook a Odoo
        odoo_service = get_odoo_service()
        success, error_msg, response_data = odoo_service.send_payment_webhook(
            payment=payment,
            user=user,
            cart_items=cart_items
        )
        
        if success:
            print(f"✅ Pago {payment.id} sincronizado exitosamente con Odoo")
        else:
            print(f"⚠️ Error sincronizando pago {payment.id} con Odoo: {error_msg}")
        
        return success, error_msg
        
    except ImportError:
        print("⚠️ Servicio de integración Odoo no disponible")
        return False, "Servicio no disponible"
    except Exception as e:
        print(f"⚠️ Error enviando pago a Odoo: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)


def process_cart_after_payment(cart, payment):
    """Procesar carrito después de un pago exitoso y registrar uso de códigos de descuento"""
    import app as M

    import json
    subscriptions_created = []
    events_registered = []
    user_services_created = []
    
    # Obtener desglose de descuentos antes de procesar
    discount_breakdown = cart.get_discount_breakdown()
    original_amount = discount_breakdown['subtotal']
    final_amount = discount_breakdown['final_total']
    total_discount = discount_breakdown['total_discount']
    
    # Registrar uso del código de descuento si existe
    if cart.discount_code_id:
        discount_code = M.DiscountCode.query.get(cart.discount_code_id)
        if discount_code:
            # Incrementar contador de usos
            discount_code.current_uses = (discount_code.current_uses or 0) + 1
            
            # Crear registro de aplicación
            code_discount_amount = discount_breakdown['code_discount']['amount'] if discount_breakdown['code_discount'] else 0
            discount_application = M.DiscountApplication(
                discount_code_id=discount_code.id,
                user_id=payment.user_id,
                payment_id=payment.id,
                cart_id=cart.id,
                original_amount=original_amount,
                discount_amount=code_discount_amount,
                final_amount=final_amount
            )
            M.db.session.add(discount_application)
    
    # Procesar items del carrito
    for item in cart.items:
        if item.product_type == 'membership':
            metadata = json.loads(item.item_metadata) if item.item_metadata else {}
            membership_type = metadata.get('membership_type', 'basic')
            
            # Crear suscripción
            end_date = datetime.utcnow() + timedelta(days=365)
            subscription = M.Subscription(
                user_id=payment.user_id,
                payment_id=payment.id,
                membership_type=membership_type,
                status='active',
                end_date=end_date
            )
            M.db.session.add(subscription)
            subscriptions_created.append(subscription)
        
        elif item.product_type == 'event':
            # Registrar al evento
            metadata = json.loads(item.item_metadata) if item.item_metadata else {}
            event_id = metadata.get('event_id')
            if event_id:
                # Verificar si el evento existe
                event = M.Event.query.get(event_id)
                if event:
                    # Verificar si ya está registrado
                    existing_registration = M.EventRegistration.query.filter_by(
                        event_id=event_id,
                        user_id=payment.user_id
                    ).first()
                    
                    if not existing_registration:
                        # Calcular precio con descuentos
                        base_price = item.unit_price
                        discount_amount = 0
                        
                        # Aplicar descuento del código si aplica a eventos
                        if cart.discount_code_id:
                            discount_code = M.DiscountCode.query.get(cart.discount_code_id)
                            if discount_code and discount_code.applies_to in ['all', 'events']:
                                discount_amount = discount_code.apply_discount(base_price)
                        
                        final_price = base_price - discount_amount
                        
                        # Crear registro de evento
                        event_registration = M.EventRegistration(
                            event_id=event_id,
                            user_id=payment.user_id,
                            registration_status='confirmed',
                            base_price=base_price / 100.0,  # Convertir de centavos a dólares
                            discount_applied=discount_amount / 100.0,
                            final_price=final_price / 100.0,
                            payment_status='paid',
                            payment_method=payment.payment_method,
                            payment_reference=payment.payment_reference or str(payment.id),
                            payment_date=payment.paid_at or datetime.utcnow(),
                            confirmation_email_sent=False
                        )
                        M.db.session.add(event_registration)
                    else:
                        # Actualizar registro existente con información de pago
                        existing_registration.payment_status = 'paid'
                        existing_registration.payment_method = payment.payment_method
                        existing_registration.payment_reference = payment.payment_reference
                        existing_registration.payment_date = payment.paid_at or datetime.utcnow()
                        existing_registration.registration_status = 'confirmed'
                        event_registration = existing_registration
                    
                    if event_registration:
                        events_registered.append(event_registration)
        
        elif item.product_type == 'service':
            # Procesar servicio
            metadata = json.loads(item.item_metadata) if item.item_metadata else {}
            service_id = metadata.get('service_id') or item.product_id
            
            if service_id:
                _pu = M.User.query.get(payment.user_id)
                _cart_org = int(getattr(_pu, 'organization_id', None) or 1) if _pu else 1
                service = M.Service.query.filter_by(id=service_id, organization_id=_cart_org).first()
                user_service = None
                if service:
                    user_service = M.UserService.query.filter_by(
                        user_id=payment.user_id,
                        service_id=service.id,
                        order_id=payment.id,
                    ).first()
                if service and not user_service:
                    # Fuente de verdad para "Mis servicios" (compras del cliente).
                    user_service = M.UserService(
                        user_id=payment.user_id,
                        service_id=service.id,
                        order_id=payment.id,
                        status='active',
                        created_at=payment.paid_at or datetime.utcnow(),
                    )
                    M.db.session.add(user_service)
                    M.db.session.flush()
                    user_services_created.append(user_service)
                
                # Verificar si es un servicio con cita agendada (tiene slot_id en metadata)
                slot_id = metadata.get('slot_id')
                if slot_id and metadata.get('requires_appointment'):
                    # Crear appointment con el slot seleccionado
                    try:
                        slot = M.AppointmentSlot.query.get(slot_id)
                        if not slot:
                            print(f"⚠️ Slot {slot_id} no encontrado para servicio {service_id}")
                            continue
                        
                        # Verificar disponibilidad del slot
                        if not slot.is_available or slot.remaining_seats() <= 0:
                            print(f"⚠️ Slot {slot_id} ya no está disponible para servicio {service_id}")
                            continue
                        
                        # Obtener información de la metadata
                        case_description = metadata.get('case_description', '')
                        advisor_id = metadata.get('advisor_id') or slot.advisor_id
                        appointment_type_id = metadata.get('appointment_type_id') or service.appointment_type_id
                        
                        # Obtener membresía del usuario
                        user = M.User.query.get(payment.user_id)
                        membership = user.get_active_membership() if user else None
                        membership_type = membership.membership_type if membership else 'basic'
                        
                        pricing_calc = service.pricing_for_membership(membership_type)
                        base_price = float(metadata.get('base_price', pricing_calc['base_price']))
                        if metadata.get('final_price') is not None:
                            final_price = float(metadata['final_price'])
                        else:
                            final_price = float(pricing_calc['final_price'])
                        discount_applied_meta = max(0.0, base_price - final_price)
                        
                        # Determinar estado de pago
                        deposit_amount = metadata.get('deposit_amount', final_price)
                        if deposit_amount >= final_price:
                            payment_status = 'paid'
                        else:
                            payment_status = 'partial'
                        
                        # Crear Appointment (flujo agendable: slot + pago → confirmación directa)
                        appointment = M.Appointment(
                            appointment_type_id=appointment_type_id,
                            organization_id=int(getattr(service, 'organization_id', None) or 1),
                            advisor_id=advisor_id,
                            slot_id=slot.id,
                            service_id=service.id,
                            payment_id=payment.id,
                            user_id=payment.user_id,
                            membership_type=membership_type,
                            start_datetime=slot.start_datetime,
                            end_datetime=slot.end_datetime,
                            status='CONFIRMADA',
                            is_initial_consult=False,
                            base_price=base_price,
                            final_price=final_price,
                            discount_applied=discount_applied_meta,
                            payment_status=payment_status,
                            payment_method=payment.payment_method,
                            user_notes=case_description
                        )
                        
                        # Reservar slot
                        slot.reserved_seats = (slot.reserved_seats or 0) + 1
                        if slot.remaining_seats() == 0:
                            slot.is_available = False
                        
                        M.db.session.add(appointment)
                        M.db.session.flush()  # Para obtener el ID de la cita
                        if user_service:
                            user_service.status = 'scheduled'
                            user_service.appointment_id = appointment.id
                        print(f"✅ Cita creada: {appointment.reference} para servicio {service.name} en slot {slot_id}")
                        
                        # Enviar notificaciones
                        try:
                            from nodeone.services.notification_engine import NotificationEngine
                            # Obtener el usuario del asesor
                            advisor_user = None
                            if advisor_id:
                                advisor_obj = M.Advisor.query.get(advisor_id)
                                if advisor_obj and advisor_obj.user:
                                    advisor_user = advisor_obj.user
                            
                            # Notificar al cliente (usuario que compró)
                            NotificationEngine.notify_appointment_created(appointment, user, advisor_user, service)
                            
                            # Notificar al asesor
                            if advisor_user:
                                NotificationEngine.notify_appointment_new_to_advisor(appointment, user, advisor_user, service)
                            
                            # Notificar a administradores
                            NotificationEngine.notify_appointment_new_to_admins(appointment, user, advisor_user, service)
                            from nodeone.services.communication_dispatch import (
                                dispatch_appointment_slot_payment_communication_engine,
                            )

                            dispatch_appointment_slot_payment_communication_engine(
                                appointment, user, advisor_user, service
                            )
                        except Exception as e:
                            print(f"⚠️ Error enviando notificaciones de cita: {e}")
                            import traceback
                            traceback.print_exc()
                        
                    except Exception as e:
                        print(f"⚠️ Error creando cita para servicio {service_id} con slot {slot_id}: {e}")
                        import traceback
                        traceback.print_exc()
                        # No fallar el pago si falla la creación de la cita
                        # Se puede crear manualmente después
                
                elif service and service.requires_diagnostic_appointment:
                    # Crear cita de diagnóstico en cola
                    try:
                        from service_diagnostic_validation import create_diagnostic_appointment_from_payment
                        user = M.User.query.get(payment.user_id)
                        if user:
                            appointment = create_diagnostic_appointment_from_payment(service, user, payment)
                            if user_service:
                                user_service.status = 'pending'
                                user_service.appointment_id = getattr(appointment, 'id', None)
                            print(f"✅ Cita de diagnóstico creada en cola: {appointment.reference} para servicio {service.name}")
                            
                            # TODO: Enviar email al usuario informando que está en cola
                            # TODO: Enviar notificación al asesor sobre nueva cita en cola
                    except Exception as e:
                        print(f"⚠️ Error creando cita de diagnóstico para servicio {service_id}: {e}")
                        import traceback
                        traceback.print_exc()
                        # No fallar el pago si falla la creación de la cita
                        # Se puede crear manualmente después
        
        elif item.product_type == 'course':
            metadata = json.loads(item.item_metadata) if item.item_metadata else {}
            cohort_id = metadata.get('cohort_id')
            if cohort_id:
                try:
                    coh = M.CourseCohort.query.get(int(cohort_id))
                    if coh:
                        coh.capacity_reserved = int(coh.capacity_reserved or 0) + int(item.quantity or 1)
                        M.db.session.add(coh)
                        print(f"✅ Cupo registrado para cohorte {cohort_id} (course)")
                except Exception as e:
                    print(f"⚠️ Error actualizando cupo de cohorte: {e}")

        elif item.product_type == 'proposal':
            # Fase 8: Pago de propuesta aceptada (flujo consultivo)
            metadata = json.loads(item.item_metadata) if item.item_metadata else {}
            proposal_id = metadata.get('proposal_id') or item.product_id
            if proposal_id:
                prop = M.Proposal.query.get(proposal_id)
                if prop and prop.client_id == payment.user_id and prop.status == 'ENVIADA':
                    prop.status = 'ACEPTADA'
                    M.db.session.add(prop)

    try:
        from nodeone.modules.academic_enrollment.service import process_academic_program_items_after_payment
    except ImportError:
        process_academic_program_items_after_payment = None
    if process_academic_program_items_after_payment:
        process_academic_program_items_after_payment(cart, payment)

    M.db.session.commit()

    # Registrar compra detallada en historial
    try:
        from history_module import HistoryLogger
        import json
        
        # Preparar detalles de los items comprados
        purchased_items = []
        for item in cart.items:
            item_data = {
                'product_type': item.product_type,
                'product_id': item.product_id,
                'product_name': item.product_name,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'total_price': item.unit_price * item.quantity
            }
            
            # Agregar metadata específica según el tipo
            if item.item_metadata:
                metadata = json.loads(item.item_metadata) if isinstance(item.item_metadata, str) else item.item_metadata
                item_data['metadata'] = metadata
            
            purchased_items.append(item_data)
        
        # Preparar información de suscripciones creadas
        subscriptions_info = []
        for sub in subscriptions_created:
            subscriptions_info.append({
                'subscription_id': sub.id,
                'membership_type': sub.membership_type,
                'status': sub.status,
                'end_date': sub.end_date.isoformat() if sub.end_date else None
            })
        
        # Preparar información de eventos registrados
        events_info = []
        for event_reg in events_registered:
            event_info = {
                'registration_id': event_reg.id,
                'event_id': event_reg.event_id,
                'event_name': event_reg.event.title if event_reg.event else 'N/A',
                'status': event_reg.registration_status,
                'final_price': event_reg.final_price
            }
            events_info.append(event_info)

        from nodeone.services.communication_dispatch import (
            dispatch_cart_checkout_communication_engine,
            request_base_url_optional,
        )

        base_url = request_base_url_optional()

        # Automatización marketing
        try:
            from _app.modules.marketing.service import trigger_automation

            if subscriptions_created:
                trigger_automation('membership_renewed', payment.user_id, base_url=base_url)
            for event_reg in events_registered:
                trigger_automation('event_registered', event_reg.user_id, base_url=base_url, event_id=event_reg.event_id)
        except Exception as e:
            print(f"Marketing automation error: {e}")

        dispatch_cart_checkout_communication_engine(
            payment.user_id,
            subscriptions_created,
            events_registered,
            base_url,
        )

        HistoryLogger.log_user_action(
            user_id=payment.user_id,
            action=f"Compra realizada - {len(purchased_items)} item(s) - ${final_amount/100:.2f}",
            status="success",
            context={"app": "web", "screen": "payment", "module": "cart"},
            payload={
                "payment_id": payment.id,
                "cart_id": cart.id,
                "items": purchased_items,
                "original_amount": original_amount,
                "total_discount": total_discount,
                "final_amount": final_amount,
                "discount_code_id": cart.discount_code_id
            },
            result={
                "subscriptions_created": len(subscriptions_created),
                "subscriptions": subscriptions_info,
                "events_registered": len(events_registered),
                "events": events_info,
                "payment_id": payment.id,
                "total_paid": final_amount
            },
            visibility="both"
        )
    except Exception as e:
        print(f"⚠️ Error registrando compra en historial: {e}")
        import traceback
        traceback.print_exc()
    
    return subscriptions_created
