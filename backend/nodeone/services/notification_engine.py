"""Motor de notificaciones (extraído de app.py). Importa `app` en cada método para evitar ciclos."""
from datetime import datetime


class NotificationEngine:
    """Motor de notificaciones para eventos y movimientos del sistema"""

    @staticmethod
    def _coerce_org_id(*candidates):
        import app as M

        for c in candidates:
            if c is not None:
                try:
                    v = int(c)
                    if v >= 1:
                        return v
                except (TypeError, ValueError):
                    pass
        return int(M.default_organization_id())

    @staticmethod
    def _event_tenant_org_id(event, registrant_user, recipient_user=None):
        import app as M

        cand = [
            getattr(event, 'organization_id', None),
            getattr((recipient_user or registrant_user), 'organization_id', None),
            getattr(registrant_user, 'organization_id', None),
        ]
        if event is not None and getattr(event, 'created_by', None):
            cr = M.User.query.get(event.created_by)
            if cr is not None:
                cand.append(getattr(cr, 'organization_id', None))
        return NotificationEngine._coerce_org_id(*cand)

    @staticmethod
    def _smtp_ready(org_id, last_cfg_ref):
        import app as M

        ok, cid = M.apply_transactional_smtp_for_organization(
            int(org_id), skip_if_config_id=last_cfg_ref[0]
        )
        if ok and cid is not None:
            last_cfg_ref[0] = cid
        return ok and bool(M.email_service)

    @staticmethod
    def _is_notification_enabled(notification_type):
        """Verificar si una notificación está habilitada en la configuración"""
        import app as M
        return M.NotificationSettings.is_enabled(notification_type)
    
    @staticmethod
    def notify_event_registration(event, user, registration):
        """Notificar a moderador, administrador y expositor del evento sobre un nuevo registro"""
        import app as M
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('event_registration'):
            print(f"⚠️ Notificación 'event_registration' está deshabilitada. No se enviará correo.")
            return
        
        try:
            # Obtener todos los responsables del evento
            recipients = event.get_notification_recipients()
            
            if not recipients:
                print(f"⚠️ No se encontraron responsables para el evento {event.id}")
                return

            last_smtp = [None]
            for recipient in recipients:
                # Crear notificación en la base de datos
                notification = M.Notification(
                    user_id=recipient.id,
                    event_id=event.id,
                    notification_type='event_registration',
                    title=f'Nuevo registro al evento: {event.title}',
                    message=f'El usuario {user.first_name} {user.last_name} ({user.email}) se ha registrado al evento "{event.title}". Estado: {registration.registration_status}.'
                )
                M.db.session.add(notification)
                # Hacer commit de la notificación primero
                M.db.session.flush()  # Para obtener el ID de la notificación
                
                # Enviar email al responsable
                try:
                    # Determinar el rol del destinatario
                    role = "Responsable"
                    if event.moderator_id == recipient.id:
                        role = "Moderador"
                    elif event.administrator_id == recipient.id:
                        role = "Administrador"
                    elif event.speaker_id == recipient.id:
                        role = "Expositor"
                    elif event.created_by == recipient.id:
                        role = "Creador"
                    
                    html_content = f"""
                        <h2>Nuevo Registro al Evento</h2>
                        <p>Hola {recipient.first_name},</p>
                        <p>Como <strong>{role}</strong> del evento, te informamos que se ha registrado un nuevo participante:</p>
                        <ul>
                            <li><strong>Evento:</strong> {event.title}</li>
                            <li><strong>Participante:</strong> {user.first_name} {user.last_name}</li>
                            <li><strong>Email:</strong> {user.email}</li>
                            <li><strong>Estado:</strong> {registration.registration_status}</li>
                            <li><strong>Fecha de registro:</strong> {registration.registration_date.strftime('%d/%m/%Y %H:%M')}</li>
                            <li><strong>Precio pagado:</strong> ${registration.final_price:.2f} {event.currency}</li>
                        </ul>
                        <p>Puedes gestionar los registros desde el panel de administración.</p>
                        <p>Saludos,<br>Equipo Easy NodeOne</p>
                        """
                    oid = NotificationEngine._event_tenant_org_id(event, user, recipient)
                    if not NotificationEngine._smtp_ready(oid, last_smtp):
                        raise Exception('SMTP no disponible para la organización del evento')
                    M.email_service.send_email(
                        subject=f'[Easy NodeOne] Nuevo registro: {event.title}',
                        recipients=[recipient.email],
                        html_content=html_content,
                        email_type='event_registration_notification',
                        related_entity_type='event',
                        related_entity_id=event.id,
                        recipient_id=recipient.id,
                        recipient_name=f"{recipient.first_name} {recipient.last_name}",
                    )
                    notification.email_sent = True
                    notification.email_sent_at = datetime.utcnow()
                    print(f"✅ Email de notificación enviado a {recipient.email} para evento {event.id}")
                except Exception as e:
                    print(f"❌ Error enviando email de notificación a {recipient.email}: {e}")
                    import traceback
                    traceback.print_exc()
                    notification.email_sent = False
                    # Registrar fallo en EmailLog ANTES del commit
                    M.log_email_sent(
                        recipient_email=recipient.email,
                        subject=f'[Easy NodeOne] Nuevo registro: {event.title}',
                        html_content='',
                        email_type='event_registration_notification',
                        related_entity_type='event',
                        related_entity_id=event.id,
                        recipient_id=recipient.id,
                        recipient_name=f"{recipient.first_name} {recipient.last_name}",
                        status='failed',
                        error_message=str(e)[:1000]  # Limitar tamaño del error
                    )
            
            M.db.session.commit()

        except Exception as e:
            print(f"Error en notify_event_registration: {e}")
            M.db.session.rollback()
        finally:
            M.apply_email_config_from_db()

    @staticmethod
    def notify_event_cancellation(event, user, registration):
        """Notificar a moderador, administrador y expositor sobre una cancelación"""
        import app as M
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('event_cancellation'):
            print(f"⚠️ Notificación 'event_cancellation' está deshabilitada. No se enviará correo.")
            return
        
        try:
            recipients = event.get_notification_recipients()
            
            if not recipients:
                return

            last_smtp = [None]
            for recipient in recipients:
                role = "Responsable"
                if event.moderator_id == recipient.id:
                    role = "Moderador"
                elif event.administrator_id == recipient.id:
                    role = "Administrador"
                elif event.speaker_id == recipient.id:
                    role = "Expositor"
                elif event.created_by == recipient.id:
                    role = "Creador"
                
                notification = M.Notification(
                    user_id=recipient.id,
                    event_id=event.id,
                    notification_type='event_cancellation',
                    title=f'Cancelación de registro: {event.title}',
                    message=f'El usuario {user.first_name} {user.last_name} ({user.email}) ha cancelado su registro al evento "{event.title}".'
                )
                M.db.session.add(notification)
                
                try:
                    html_content = f"""
                        <h2>Cancelación de Registro</h2>
                        <p>Hola {recipient.first_name},</p>
                        <p>Como <strong>{role}</strong> del evento, te informamos que un participante ha cancelado su registro:</p>
                        <ul>
                            <li><strong>Evento:</strong> {event.title}</li>
                            <li><strong>Participante:</strong> {user.first_name} {user.last_name}</li>
                            <li><strong>Email:</strong> {user.email}</li>
                            <li><strong>Fecha de cancelación:</strong> {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}</li>
                        </ul>
                        <p>Saludos,<br>Equipo Easy NodeOne</p>
                        """
                    oid = NotificationEngine._event_tenant_org_id(event, user, recipient)
                    if not NotificationEngine._smtp_ready(oid, last_smtp):
                        raise RuntimeError('SMTP no disponible para la organización del evento')
                    M.email_service.send_email(
                        subject=f'[Easy NodeOne] Cancelación de registro: {event.title}',
                        recipients=[recipient.email],
                        html_content=html_content,
                        email_type='event_cancellation_notification',
                        related_entity_type='event',
                        related_entity_id=event.id,
                        recipient_id=recipient.id,
                        recipient_name=f"{recipient.first_name} {recipient.last_name}",
                    )
                    notification.email_sent = True
                    notification.email_sent_at = datetime.utcnow()
                except Exception as e:
                    print(f"Error enviando email de cancelación a {recipient.email}: {e}")
                    M.log_email_sent(
                        recipient_email=recipient.email,
                        subject=f'[Easy NodeOne] Cancelación de registro: {event.title}',
                        html_content='',
                        email_type='event_cancellation_notification',
                        related_entity_type='event',
                        related_entity_id=event.id,
                        recipient_id=recipient.id,
                        recipient_name=f"{recipient.first_name} {recipient.last_name}",
                        status='failed',
                        error_message=str(e)
                    )
            
            M.db.session.commit()

        except Exception as e:
            print(f"Error en notify_event_cancellation: {e}")
            M.db.session.rollback()
        finally:
            M.apply_email_config_from_db()

    @staticmethod
    def notify_event_confirmation(event, user, registration):
        """Notificar a moderador, administrador y expositor cuando se confirma un registro"""
        import app as M
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('event_confirmation'):
            print(f"⚠️ Notificación 'event_confirmation' está deshabilitada. No se enviará correo.")
            return
        
        try:
            recipients = event.get_notification_recipients()
            
            if not recipients:
                return

            last_smtp = [None]
            for recipient in recipients:
                role = "Responsable"
                if event.moderator_id == recipient.id:
                    role = "Moderador"
                elif event.administrator_id == recipient.id:
                    role = "Administrador"
                elif event.speaker_id == recipient.id:
                    role = "Expositor"
                elif event.created_by == recipient.id:
                    role = "Creador"
                
                notification = M.Notification(
                    user_id=recipient.id,
                    event_id=event.id,
                    notification_type='event_confirmation',
                    title=f'Registro confirmado: {event.title}',
                    message=f'El registro de {user.first_name} {user.last_name} al evento "{event.title}" ha sido confirmado.'
                )
                M.db.session.add(notification)
                
                try:
                    html_content = f"""
                        <h2>Registro Confirmado</h2>
                        <p>Hola {recipient.first_name},</p>
                        <p>Como <strong>{role}</strong> del evento, te informamos que un registro ha sido confirmado:</p>
                        <ul>
                            <li><strong>Evento:</strong> {event.title}</li>
                            <li><strong>Participante:</strong> {user.first_name} {user.last_name}</li>
                            <li><strong>Email:</strong> {user.email}</li>
                            <li><strong>Estado:</strong> Confirmado</li>
                        </ul>
                        <p>Saludos,<br>Equipo Easy NodeOne</p>
                        """
                    oid = NotificationEngine._event_tenant_org_id(event, user, recipient)
                    if not NotificationEngine._smtp_ready(oid, last_smtp):
                        raise RuntimeError('SMTP no disponible para la organización del evento')
                    M.email_service.send_email(
                        subject=f'[Easy NodeOne] Registro confirmado: {event.title}',
                        recipients=[recipient.email],
                        html_content=html_content,
                        email_type='event_confirmation_notification',
                        related_entity_type='event',
                        related_entity_id=event.id,
                        recipient_id=recipient.id,
                        recipient_name=f"{recipient.first_name} {recipient.last_name}",
                    )
                    notification.email_sent = True
                    notification.email_sent_at = datetime.utcnow()
                    print(f"✅ Email de confirmación enviado a {recipient.email} para evento {event.id}")
                except Exception as e:
                    print(f"❌ Error enviando email de confirmación a {recipient.email}: {e}")
                    import traceback
                    traceback.print_exc()
                    notification.email_sent = False
                    # Registrar fallo en EmailLog
                    M.log_email_sent(
                        recipient_email=recipient.email,
                        subject=f'[Easy NodeOne] Registro confirmado: {event.title}',
                        html_content='',
                        email_type='event_confirmation_notification',
                        related_entity_type='event',
                        related_entity_id=event.id,
                        recipient_id=recipient.id,
                        recipient_name=f"{recipient.first_name} {recipient.last_name}",
                        status='failed',
                        error_message=str(e)
                    )
            
            M.db.session.commit()

        except Exception as e:
            print(f"Error en notify_event_confirmation: {e}")
            M.db.session.rollback()
        finally:
            M.apply_email_config_from_db()

    @staticmethod
    def notify_event_update(event, changes=None):
        """Notificar cambios en un evento a todos los registrados"""
        import app as M
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('event_update'):
            print(f"⚠️ Notificación 'event_update' está deshabilitada. No se enviará correo.")
            return
        
        try:
            event_creator = M.User.query.get(event.created_by) if event.created_by else None
            
            if not event_creator:
                return
            
            # Notificar al creador
            notification = M.Notification(
                user_id=event_creator.id,
                event_id=event.id,
                notification_type='event_update',
                title=f'Evento actualizado: {event.title}',
                message=f'Se han realizado cambios en el evento "{event.title}".'
            )
            M.db.session.add(notification)
            
            # Notificar a todos los registrados
            registrations = M.EventRegistration.query.filter_by(
                event_id=event.id,
                registration_status='confirmed'
            ).all()

            last_smtp = [None]
            for reg in registrations:
                user = M.User.query.get(reg.user_id)
                if user:
                    user_notification = M.Notification(
                        user_id=user.id,
                        event_id=event.id,
                        notification_type='event_update',
                        title=f'Actualización del evento: {event.title}',
                        message=f'El evento "{event.title}" al que estás registrado ha sido actualizado. Revisa los detalles en la plataforma.'
                    )
                    M.db.session.add(user_notification)
                    
                    try:
                        html_content = f"""
                            <h2>Evento Actualizado</h2>
                            <p>Hola {user.first_name},</p>
                            <p>El evento "{event.title}" al que estás registrado ha sido actualizado.</p>
                            <p>Te recomendamos revisar los detalles del evento en la plataforma.</p>
                            <p>Saludos,<br>Equipo Easy NodeOne</p>
                            """
                        oid = NotificationEngine._event_tenant_org_id(event, user, user)
                        if not NotificationEngine._smtp_ready(oid, last_smtp):
                            raise RuntimeError('SMTP no disponible para la organización del evento')
                        M.email_service.send_email(
                            subject=f'[Easy NodeOne] Actualización: {event.title}',
                            recipients=[user.email],
                            html_content=html_content,
                            email_type='event_update',
                            related_entity_type='event',
                            related_entity_id=event.id,
                            recipient_id=user.id,
                            recipient_name=f"{user.first_name} {user.last_name}",
                        )
                        user_notification.email_sent = True
                        user_notification.email_sent_at = datetime.utcnow()
                    except Exception as e:
                        print(f"Error enviando email de actualización a {user.email}: {e}")
                        M.log_email_sent(
                            recipient_email=user.email,
                            subject=f'[Easy NodeOne] Actualización: {event.title}',
                            html_content='',
                            email_type='event_update',
                            related_entity_type='event',
                            related_entity_id=event.id,
                            recipient_id=user.id,
                            recipient_name=f"{user.first_name} {user.last_name}",
                            status='failed',
                            error_message=str(e)
                        )
            
            M.db.session.commit()

        except Exception as e:
            print(f"Error en notify_event_update: {e}")
            M.db.session.rollback()
        finally:
            M.apply_email_config_from_db()

    @staticmethod
    def notify_membership_payment(user, payment, subscription):
        """Notificar confirmación de pago de membresía"""
        import app as M
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('membership_payment'):
            print(f"⚠️ Notificación 'membership_payment' está deshabilitada. No se enviará correo a {user.email}")
            return
        
        try:
            # Crear notificación
            notification = M.Notification(
                user_id=user.id,
                notification_type='membership_payment',
                title='Pago de Membresía Confirmado',
                message=f'Tu pago por la membresía {payment.membership_type.title()} ha sido procesado exitosamente. Válida hasta {subscription.end_date.strftime("%d/%m/%Y")}.'
            )
            M.db.session.add(notification)

            last_smtp = [None]
            oid_mail = NotificationEngine._coerce_org_id(
                getattr(user, 'organization_id', None), M._infra_org_id_for_runtime()
            )
            if M.email_service:
                if M.EMAIL_TEMPLATES_AVAILABLE:
                    html_content, subj_mail = M.render_membership_payment_email_for_org(
                        user, payment, subscription, oid_mail, strict_tenant_logo=False
                    )
                else:
                    html_content, subj_mail = None, None
                if html_content and NotificationEngine._smtp_ready(oid_mail, last_smtp):
                    M.email_service.send_email(
                        subject=subj_mail,
                        recipients=[user.email],
                        html_content=html_content,
                        email_type='membership_payment',
                        related_entity_type='payment',
                        related_entity_id=payment.id,
                        recipient_id=user.id,
                        recipient_name=f"{user.first_name} {user.last_name}",
                    )
                    notification.email_sent = True
                    notification.email_sent_at = datetime.utcnow()
                elif not html_content and NotificationEngine._smtp_ready(oid_mail, last_smtp):
                    M.send_payment_confirmation_email(user, payment, subscription)
                    notification.email_sent = True
                    notification.email_sent_at = datetime.utcnow()

            M.db.session.commit()
        except Exception as e:
            print(f"Error en notify_membership_payment: {e}")
            M.db.session.rollback()
        finally:
            M.apply_email_config_from_db()

    @staticmethod
    def notify_membership_expiring(user, subscription, days_left):
        """Notificar que la membresía está por expirar"""
        import app as M
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('membership_expiring'):
            print(f"⚠️ Notificación 'membership_expiring' está deshabilitada. No se enviará correo a {user.email}")
            return
        
        try:
            notification = M.Notification(
                user_id=user.id,
                notification_type='membership_expiring',
                title=f'Membresía Expirará en {days_left} Días',
                message=f'Tu membresía {subscription.membership_type.title()} expirará el {subscription.end_date.strftime("%d/%m/%Y")}. Renueva ahora para continuar disfrutando de todos los beneficios.'
            )
            M.db.session.add(notification)

            last_smtp = [None]
            oid_mail = NotificationEngine._coerce_org_id(
                getattr(user, 'organization_id', None), M._infra_org_id_for_runtime()
            )
            if (
                M.email_service
                and M.EMAIL_TEMPLATES_AVAILABLE
                and NotificationEngine._smtp_ready(oid_mail, last_smtp)
            ):
                html_content, subj_mail = M.render_membership_expiring_email_for_org(
                    user, subscription, days_left, oid_mail, strict_tenant_logo=False
                )
                M.email_service.send_email(
                    subject=subj_mail,
                    recipients=[user.email],
                    html_content=html_content,
                    email_type='membership_expiring',
                    related_entity_type='subscription',
                    related_entity_id=subscription.id,
                    recipient_id=user.id,
                    recipient_name=f"{user.first_name} {user.last_name}",
                )
                notification.email_sent = True
                notification.email_sent_at = datetime.utcnow()

            M.db.session.commit()
        except Exception as e:
            print(f"Error en notify_membership_expiring: {e}")
            M.db.session.rollback()
        finally:
            M.apply_email_config_from_db()

    @staticmethod
    def notify_membership_expired(user, subscription):
        """Notificar que la membresía ha expirado"""
        import app as M
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('membership_expired'):
            print(f"⚠️ Notificación 'membership_expired' está deshabilitada. No se enviará correo a {user.email}")
            return
        
        try:
            notification = M.Notification(
                user_id=user.id,
                notification_type='membership_expired',
                title='Membresía Expirada',
                message=f'Tu membresía {subscription.membership_type.title()} ha expirado. Renueva ahora para reactivar tus beneficios.'
            )
            M.db.session.add(notification)

            last_smtp = [None]
            oid_mail = NotificationEngine._coerce_org_id(
                getattr(user, 'organization_id', None), M._infra_org_id_for_runtime()
            )
            if (
                M.email_service
                and M.EMAIL_TEMPLATES_AVAILABLE
                and NotificationEngine._smtp_ready(oid_mail, last_smtp)
            ):
                html_content, subj_mail = M.render_membership_expired_email_for_org(
                    user, subscription, oid_mail, strict_tenant_logo=False
                )
                M.email_service.send_email(
                    subject=subj_mail,
                    recipients=[user.email],
                    html_content=html_content,
                    email_type='membership_expired',
                    related_entity_type='subscription',
                    related_entity_id=subscription.id,
                    recipient_id=user.id,
                    recipient_name=f"{user.first_name} {user.last_name}",
                )
                notification.email_sent = True
                notification.email_sent_at = datetime.utcnow()

            M.db.session.commit()
        except Exception as e:
            print(f"Error en notify_membership_expired: {e}")
            M.db.session.rollback()
        finally:
            M.apply_email_config_from_db()

    @staticmethod
    def notify_membership_renewed(user, subscription):
        """Notificar renovación de membresía"""
        import app as M
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('membership_renewed'):
            print(f"⚠️ Notificación 'membership_renewed' está deshabilitada. No se enviará correo a {user.email}")
            return
        
        try:
            notification = M.Notification(
                user_id=user.id,
                notification_type='membership_renewed',
                title='Membresía Renovada',
                message=f'Tu membresía {subscription.membership_type.title()} ha sido renovada exitosamente. Válida hasta {subscription.end_date.strftime("%d/%m/%Y")}.'
            )
            M.db.session.add(notification)

            last_smtp = [None]
            oid_mail = NotificationEngine._coerce_org_id(
                getattr(user, 'organization_id', None), M._infra_org_id_for_runtime()
            )
            if (
                M.email_service
                and M.EMAIL_TEMPLATES_AVAILABLE
                and NotificationEngine._smtp_ready(oid_mail, last_smtp)
            ):
                html_content, subj_mail = M.render_membership_renewed_email_for_org(
                    user, subscription, oid_mail, strict_tenant_logo=False
                )
                M.email_service.send_email(
                    subject=subj_mail,
                    recipients=[user.email],
                    html_content=html_content,
                    email_type='membership_renewed',
                    related_entity_type='subscription',
                    related_entity_id=subscription.id,
                    recipient_id=user.id,
                    recipient_name=f"{user.first_name} {user.last_name}",
                )
                notification.email_sent = True
                notification.email_sent_at = datetime.utcnow()

            M.db.session.commit()
        except Exception as e:
            print(f"Error en notify_membership_renewed: {e}")
            M.db.session.rollback()
        finally:
            M.apply_email_config_from_db()

    @staticmethod
    def notify_appointment_confirmation(appointment, user, advisor):
        """Notificar confirmación de cita"""
        import app as M
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('appointment_confirmation'):
            print(f"⚠️ Notificación 'appointment_confirmation' está deshabilitada. No se enviará correo a {user.email}")
            return
        
        try:
            notification = M.Notification(
                user_id=user.id,
                notification_type='appointment_confirmation',
                title='Cita Confirmada',
                message=f'Tu cita con {advisor.first_name} {advisor.last_name} ha sido confirmada para el {(appointment.start_datetime.strftime("%d/%m/%Y %H:%M") if getattr(appointment, "start_datetime", None) else "próximo")}.'
            )
            M.db.session.add(notification)

            last_smtp = [None]
            oid_ap = NotificationEngine._coerce_org_id(
                getattr(appointment, 'organization_id', None),
                getattr(user, 'organization_id', None),
                M._infra_org_id_for_runtime(),
            )
            if (
                M.email_service
                and M.EMAIL_TEMPLATES_AVAILABLE
                and NotificationEngine._smtp_ready(oid_ap, last_smtp)
            ):
                _ab = M._email_branding_from_organization_id(oid_ap)
                html_content, subj_mail = M.render_appointment_communication_email(
                    'appointment_confirmation',
                    appointment,
                    user,
                    {'advisor': advisor},
                    lambda: M.get_appointment_confirmation_email(appointment, user, advisor, **_ab),
                    f'Cita Confirmada - {_ab["organization_name"]}',
                    strict_tenant_logo=False,
                )
                M.email_service.send_email(
                    subject=subj_mail,
                    recipients=[user.email],
                    html_content=html_content,
                    email_type='appointment_confirmation',
                    related_entity_type='appointment',
                    related_entity_id=appointment.id,
                    recipient_id=user.id,
                    recipient_name=f"{user.first_name} {user.last_name}",
                )
                notification.email_sent = True
                notification.email_sent_at = datetime.utcnow()

            M.db.session.commit()
        except Exception as e:
            print(f"Error en notify_appointment_confirmation: {e}")
            M.db.session.rollback()
        finally:
            M.apply_email_config_from_db()

    @staticmethod
    def notify_appointment_reminder(appointment, user, advisor, hours_before=24):
        """Notificar recordatorio de cita"""
        import app as M
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('appointment_reminder'):
            print(f"⚠️ Notificación 'appointment_reminder' está deshabilitada. No se enviará correo a {user.email}")
            return
        
        try:
            st = getattr(appointment, 'start_datetime', None)
            if st:
                rem_msg = (
                    f'Recuerda que tienes una cita con {advisor.first_name} {advisor.last_name} '
                    f'el {st.strftime("%d/%m/%Y %H:%M")}.'
                )
            else:
                rem_msg = (
                    f'Recuerda que tienes una cita con {advisor.first_name} {advisor.last_name} '
                    f'(fecha por confirmar).'
                )
            notification = M.Notification(
                user_id=user.id,
                notification_type='appointment_reminder',
                title=f'Recordatorio: Cita en {hours_before} horas',
                message=rem_msg,
            )
            M.db.session.add(notification)

            last_smtp = [None]
            oid_appt = NotificationEngine._coerce_org_id(
                getattr(appointment, 'organization_id', None),
                getattr(user, 'organization_id', None),
                M._infra_org_id_for_runtime(),
            )
            if (
                M.email_service
                and M.EMAIL_TEMPLATES_AVAILABLE
                and NotificationEngine._smtp_ready(oid_appt, last_smtp)
            ):
                _ab = M._email_branding_from_organization_id(oid_appt)
                hb = int(hours_before)
                html_content, subj_mail = M.render_appointment_communication_email(
                    'appointment_reminder',
                    appointment,
                    user,
                    {'advisor': advisor, 'hours_before': hb},
                    lambda: M.get_appointment_reminder_email(appointment, user, advisor, hb, **_ab),
                    f'Recordatorio: Cita en {hb} horas - {_ab["organization_name"]}',
                    strict_tenant_logo=False,
                )
                ok = M.email_service.send_email(
                    subject=subj_mail,
                    recipients=[user.email],
                    html_content=html_content,
                    email_type='appointment_reminder',
                    related_entity_type='appointment',
                    related_entity_id=appointment.id,
                    recipient_id=user.id,
                    recipient_name=f"{user.first_name} {user.last_name}",
                )
                if ok:
                    notification.email_sent = True
                    notification.email_sent_at = datetime.utcnow()
                    if hb == 24:
                        appointment.reminder_24h_sent_at = datetime.utcnow()
                    elif hb == 1:
                        appointment.reminder_1h_sent_at = datetime.utcnow()

            M.db.session.commit()
        except Exception as e:
            print(f"Error en notify_appointment_reminder: {e}")
            M.db.session.rollback()
        finally:
            M.apply_email_config_from_db()

    @staticmethod
    def notify_appointment_cancelled(appointment, user, cancellation_reason=None, cancelled_by='member'):
        """Correo al miembro cuando se cancela una cita."""
        import app as M
        if not NotificationEngine._is_notification_enabled('appointment_cancellation'):
            print(f"⚠️ Notificación 'appointment_cancellation' está deshabilitada. No se enviará correo a {getattr(user, 'email', '')}")
            return
        try:
            ap = M.Appointment.query.get(getattr(appointment, 'id', None))
            if not ap or not user:
                return
            reason = cancellation_reason if cancellation_reason is not None else (ap.cancellation_reason or '')
            notification = M.Notification(
                user_id=user.id,
                notification_type='appointment_cancellation',
                title='Cita cancelada',
                message=f'Tu cita ha sido cancelada. Motivo: {(reason or "—")[:500]}',
            )
            M.db.session.add(notification)
            last_smtp = [None]
            oid_ap = NotificationEngine._coerce_org_id(
                getattr(ap, 'organization_id', None),
                getattr(user, 'organization_id', None),
                M._infra_org_id_for_runtime(),
            )
            if (
                M.email_service
                and M.EMAIL_TEMPLATES_AVAILABLE
                and NotificationEngine._smtp_ready(oid_ap, last_smtp)
            ):
                _ab = M._email_branding_from_organization_id(oid_ap)
                html_content, subj_mail = M.render_appointment_communication_email(
                    'appointment_cancellation',
                    ap,
                    user,
                    {'cancellation_reason': reason, 'cancelled_by': cancelled_by or 'member'},
                    lambda: M.get_appointment_cancellation_email(
                        ap,
                        user,
                        cancellation_reason=reason,
                        cancelled_by=cancelled_by or 'member',
                        **_ab,
                    ),
                    f'Cancelación de cita - {_ab["organization_name"]}',
                    strict_tenant_logo=False,
                )
                ok = M.email_service.send_email(
                    subject=subj_mail,
                    recipients=[user.email],
                    html_content=html_content,
                    email_type='appointment_cancellation',
                    related_entity_type='appointment',
                    related_entity_id=ap.id,
                    recipient_id=user.id,
                    recipient_name=f"{user.first_name} {user.last_name}",
                )
                if ok:
                    notification.email_sent = True
                    notification.email_sent_at = datetime.utcnow()
                    ap.cancellation_sent = True
                    ap.cancellation_sent_at = datetime.utcnow()
            M.db.session.commit()
        except Exception as e:
            print(f"Error en notify_appointment_cancelled: {e}")
            M.db.session.rollback()
        finally:
            M.apply_email_config_from_db()

    @staticmethod
    def notify_appointment_created(appointment, user, advisor, service):
        """Notificar al cliente que su cita fue creada después del pago"""
        import app as M
        try:
            # Crear notificación para el cliente
            notification = M.Notification(
                user_id=user.id,
                notification_type='appointment_created',
                title='Cita Agendada - Pendiente de Confirmación',
                message=f'Tu cita para "{service.name if service else appointment.appointment_type.name}" ha sido agendada para el {appointment.start_datetime.strftime("%d/%m/%Y")} a las {appointment.start_datetime.strftime("%H:%M")}. Está pendiente de confirmación por el asesor.'
            )
            M.db.session.add(notification)
            M.db.session.flush()
            
            last_smtp = [None]
            oid_ac = NotificationEngine._coerce_org_id(
                getattr(appointment, 'organization_id', None),
                getattr(user, 'organization_id', None),
                M._infra_org_id_for_runtime(),
            )
            if M.email_service and NotificationEngine._smtp_ready(oid_ac, last_smtp):
                try:
                    from email_templates import get_appointment_created_email

                    _ab = M._email_branding_from_organization_id(oid_ac)
                    html_content = get_appointment_created_email(appointment, user, advisor, service, **_ab)
                    M.email_service.send_email(
                        subject=f'Cita Agendada - {_ab["organization_name"]}',
                        recipients=[user.email],
                        html_content=html_content,
                        email_type='appointment_created',
                        related_entity_type='appointment',
                        related_entity_id=appointment.id,
                        recipient_id=user.id,
                        recipient_name=f"{user.first_name} {user.last_name}",
                    )
                    notification.email_sent = True
                    notification.email_sent_at = datetime.utcnow()
                    print(f"✅ Email de cita creada enviado a cliente {user.email}")
                except Exception as e:
                    print(f"⚠️ Error enviando email de cita creada a cliente: {e}")

            M.db.session.commit()
        except Exception as e:
            print(f"Error en notify_appointment_created: {e}")
            M.db.session.rollback()
        finally:
            M.apply_email_config_from_db()

    @staticmethod
    def notify_appointment_new_to_advisor(appointment, user, advisor, service):
        """Notificar al asesor sobre nueva cita que requiere confirmación"""
        import app as M
        if not advisor:
            return
        
        try:
            # Crear notificación para el asesor
            notification = M.Notification(
                user_id=advisor.id,
                notification_type='appointment_new',
                title='Nueva Cita Pendiente de Confirmación',
                message=f'Nueva cita solicitada por {user.first_name} {user.last_name} para "{service.name if service else appointment.appointment_type.name}" el {appointment.start_datetime.strftime("%d/%m/%Y")} a las {appointment.start_datetime.strftime("%H:%M")}. Requiere tu confirmación.'
            )
            M.db.session.add(notification)
            M.db.session.flush()
            
            last_smtp = [None]
            oid_aa = NotificationEngine._coerce_org_id(
                getattr(user, 'organization_id', None),
                getattr(appointment, 'organization_id', None),
                M._infra_org_id_for_runtime(),
            )
            if M.email_service and NotificationEngine._smtp_ready(oid_aa, last_smtp):
                try:
                    from email_templates import get_appointment_new_advisor_email

                    _ab = M._email_branding_from_organization_id(oid_aa)
                    html_content = get_appointment_new_advisor_email(appointment, user, advisor, service, **_ab)
                    M.email_service.send_email(
                        subject=f'Nueva Cita Pendiente de Confirmación - {_ab["organization_name"]}',
                        recipients=[advisor.email],
                        html_content=html_content,
                        email_type='appointment_new_advisor',
                        related_entity_type='appointment',
                        related_entity_id=appointment.id,
                        recipient_id=advisor.id,
                        recipient_name=f"{advisor.first_name} {advisor.last_name}",
                    )
                    notification.email_sent = True
                    notification.email_sent_at = datetime.utcnow()
                    print(f"✅ Email de nueva cita enviado a asesor {advisor.email}")
                except Exception as e:
                    print(f"⚠️ Error enviando email de nueva cita a asesor: {e}")

            M.db.session.commit()
        except Exception as e:
            print(f"Error en notify_appointment_new_to_advisor: {e}")
            M.db.session.rollback()
        finally:
            M.apply_email_config_from_db()

    @staticmethod
    def notify_appointment_new_to_admins(appointment, user, advisor, service):
        """Notificar a administradores sobre nueva cita creada"""
        import app as M
        try:
            # Obtener todos los administradores activos
            admins = M.User.query.filter_by(is_admin=True, is_active=True).all()
            
            if not admins:
                print("⚠️ No se encontraron administradores para notificar")
                return
            
            advisor_name = f"{advisor.first_name} {advisor.last_name}" if advisor else "No asignado"

            last_smtp = [None]
            oid_am = NotificationEngine._coerce_org_id(
                getattr(appointment, 'organization_id', None),
                getattr(user, 'organization_id', None),
                M._infra_org_id_for_runtime(),
            )
            for admin in admins:
                # Crear notificación para cada administrador
                notification = M.Notification(
                    user_id=admin.id,
                    notification_type='appointment_new_admin',
                    title='Nueva Cita Creada',
                    message=f'Nueva cita creada: {user.first_name} {user.last_name} ({user.email}) solicitó "{service.name if service else appointment.appointment_type.name}" con {advisor_name} para el {appointment.start_datetime.strftime("%d/%m/%Y")} a las {appointment.start_datetime.strftime("%H:%M")}.'
                )
                M.db.session.add(notification)
                M.db.session.flush()
                
                if M.email_service and NotificationEngine._smtp_ready(oid_am, last_smtp):
                    try:
                        from email_templates import get_appointment_new_admin_email

                        _ab = M._email_branding_from_organization_id(oid_am)
                        html_content = get_appointment_new_admin_email(
                            appointment, user, advisor, service, admin, **_ab
                        )
                        M.email_service.send_email(
                            subject=f'Nueva Cita Creada - {_ab["organization_name"]}',
                            recipients=[admin.email],
                            html_content=html_content,
                            email_type='appointment_new_admin',
                            related_entity_type='appointment',
                            related_entity_id=appointment.id,
                            recipient_id=admin.id,
                            recipient_name=f"{admin.first_name} {admin.last_name}",
                        )
                        notification.email_sent = True
                        notification.email_sent_at = datetime.utcnow()
                        print(f"✅ Email de nueva cita enviado a administrador {admin.email}")
                    except Exception as e:
                        print(f"⚠️ Error enviando email de nueva cita a administrador {admin.email}: {e}")

            M.db.session.commit()
        except Exception as e:
            print(f"Error en notify_appointment_new_to_admins: {e}")
            M.db.session.rollback()
        finally:
            M.apply_email_config_from_db()

    @staticmethod
    def notify_welcome(user):
        """Notificar bienvenida a nuevo usuario"""
        import app as M
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('welcome'):
            print(f"⚠️ Notificación 'welcome' está deshabilitada. No se enviará correo a {user.email}")
            return
        
        try:
            notification = M.Notification(
                user_id=user.id,
                notification_type='welcome',
                title='¡Bienvenido a Easy NodeOne!',
                message='Te damos la bienvenida a Easy NodeOne. Explora nuestros eventos, recursos y servicios disponibles.'
            )
            M.db.session.add(notification)

            if not M.email_service:
                print(f"⚠️ email_service es None. No se enviará correo a {user.email}")
                M.db.session.commit()
                return

            last_smtp = [None]
            oid_mail = NotificationEngine._coerce_org_id(
                getattr(user, 'organization_id', None), M._infra_org_id_for_runtime()
            )
            try:
                html_content, subj_mail = M.render_welcome_email_for_org(
                    user, oid_mail, strict_tenant_logo=False
                )
            except Exception as e:
                print(f"❌ Error al generar template de bienvenida: {e}")
                import traceback

                traceback.print_exc()
                M.db.session.commit()
                return

            try:
                if NotificationEngine._smtp_ready(oid_mail, last_smtp):
                    success = M.email_service.send_email(
                        subject=subj_mail,
                        recipients=[user.email],
                        html_content=html_content,
                        email_type='welcome',
                        related_entity_type='user',
                        related_entity_id=user.id,
                        recipient_id=user.id,
                        recipient_name=f"{user.first_name} {user.last_name}",
                    )
                    if success:
                        notification.email_sent = True
                        notification.email_sent_at = datetime.utcnow()
                        print(f"✅ Email de bienvenida enviado exitosamente a {user.email}")
                    else:
                        print(f"❌ Error al enviar email de bienvenida a {user.email}")
            except Exception as e:
                print(f"❌ Error al enviar email de bienvenida: {e}")
                import traceback

                traceback.print_exc()

            M.db.session.commit()
        except Exception as e:
            print(f"❌ Error en notify_welcome: {e}")
            import traceback

            traceback.print_exc()
            M.db.session.rollback()
        finally:
            M.apply_email_config_from_db()

    @staticmethod
    def notify_event_registration_to_user(event, user, registration):
        """Notificar al usuario sobre su registro a evento"""
        import app as M
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('event_registration_user'):
            print(f"⚠️ Notificación 'event_registration_user' está deshabilitada. No se enviará correo a {user.email}")
            return
        
        try:
            notification = M.Notification(
                user_id=user.id,
                event_id=event.id,
                notification_type='event_registration_user',
                title=f'Registro Confirmado: {event.title}',
                message=f'Tu registro al evento "{event.title}" ha sido confirmado. Estado: {registration.registration_status}.'
            )
            M.db.session.add(notification)

            last_smtp = [None]
            oid_er = NotificationEngine._event_tenant_org_id(event, user, user)
            if (
                M.email_service
                and M.EMAIL_TEMPLATES_AVAILABLE
                and NotificationEngine._smtp_ready(oid_er, last_smtp)
            ):
                _ab = M._email_branding_from_organization_id(oid_er)
                html_content = M.get_event_registration_email(event, user, registration, **_ab)
                M.email_service.send_email(
                    subject=f'Registro Confirmado: {event.title}',
                    recipients=[user.email],
                    html_content=html_content,
                    email_type='event_registration',
                    related_entity_type='event',
                    related_entity_id=event.id,
                    recipient_id=user.id,
                    recipient_name=f"{user.first_name} {user.last_name}",
                )
                notification.email_sent = True
                notification.email_sent_at = datetime.utcnow()

            M.db.session.commit()
        except Exception as e:
            print(f"Error en notify_event_registration_to_user: {e}")
            M.db.session.rollback()
        finally:
            M.apply_email_config_from_db()

    @staticmethod
    def notify_event_cancellation_to_user(event, user):
        """Notificar al usuario sobre cancelación de registro"""
        import app as M
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('event_cancellation_user'):
            print(f"⚠️ Notificación 'event_cancellation_user' está deshabilitada. No se enviará correo a {user.email}")
            return
        
        try:
            notification = M.Notification(
                user_id=user.id,
                event_id=event.id,
                notification_type='event_cancellation_user',
                title=f'Registro Cancelado: {event.title}',
                message=f'Tu registro al evento "{event.title}" ha sido cancelado.'
            )
            M.db.session.add(notification)

            last_smtp = [None]
            oid_mail = NotificationEngine._event_tenant_org_id(event, user, user)
            if (
                M.email_service
                and M.EMAIL_TEMPLATES_AVAILABLE
                and NotificationEngine._smtp_ready(oid_mail, last_smtp)
            ):
                html_content, subj_mail = M.render_event_cancellation_email_for_org(
                    event, user, oid_mail, strict_tenant_logo=False
                )
                M.email_service.send_email(
                    subject=subj_mail,
                    recipients=[user.email],
                    html_content=html_content,
                    email_type='event_cancellation',
                    related_entity_type='event',
                    related_entity_id=event.id,
                    recipient_id=user.id,
                    recipient_name=f"{user.first_name} {user.last_name}",
                )
                notification.email_sent = True
                notification.email_sent_at = datetime.utcnow()

            M.db.session.commit()
        except Exception as e:
            print(f"Error en notify_event_cancellation_to_user: {e}")
            M.db.session.rollback()
        finally:
            M.apply_email_config_from_db()