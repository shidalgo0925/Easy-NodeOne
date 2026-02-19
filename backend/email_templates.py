#!/usr/bin/env python3
"""
Plantillas de correo electrónico para RelaticPanama
Sistema de templates HTML para diferentes tipos de notificaciones
"""

from datetime import datetime
from flask import render_template, request

def get_email_template_base():
    """Template base HTML para todos los correos"""
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{subject}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f4f4f4;
            }}
            .email-container {{
                background-color: #ffffff;
                border-radius: 8px;
                padding: 30px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .header {{
                text-align: center;
                border-bottom: 3px solid #0066cc;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            .header h1 {{
                color: #0066cc;
                margin: 0;
                font-size: 24px;
            }}
            .content {{
                margin-bottom: 30px;
            }}
            .content h2 {{
                color: #0066cc;
                font-size: 20px;
                margin-top: 0;
            }}
            .content p {{
                margin-bottom: 15px;
            }}
            .info-box {{
                background-color: #f8f9fa;
                border-left: 4px solid #0066cc;
                padding: 15px;
                margin: 20px 0;
            }}
            .info-box ul {{
                margin: 10px 0;
                padding-left: 20px;
            }}
            .info-box li {{
                margin-bottom: 8px;
            }}
            .button {{
                display: inline-block;
                padding: 12px 30px;
                background-color: #0066cc;
                color: #ffffff !important;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
                font-weight: bold;
            }}
            .button:hover {{
                background-color: #0052a3;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #e0e0e0;
                text-align: center;
                color: #666;
                font-size: 12px;
            }}
            .badge {{
                display: inline-block;
                padding: 5px 10px;
                background-color: #28a745;
                color: white;
                border-radius: 3px;
                font-size: 12px;
                font-weight: bold;
            }}
            .warning-badge {{
                background-color: #ffc107;
                color: #333;
            }}
            .danger-badge {{
                background-color: #dc3545;
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="header">
                <h1>RelaticPanama</h1>
                <p style="color: #666; margin: 5px 0;">Red Latinoamericana de Investigaciones Cualitativas</p>
            </div>
            <div class="content">
                {content}
            </div>
            <div class="footer">
                <p>Este es un correo automático de RelaticPanama. Por favor, no responda a este mensaje.</p>
                <p>Si tiene alguna consulta, contacte a: <a href="mailto:administracion@relaticpanama.org">administracion@relaticpanama.org</a></p>
                <p>&copy; {year} RelaticPanama. Todos los derechos reservados.</p>
            </div>
        </div>
    </body>
    </html>
    """


def get_membership_payment_confirmation_email(user, payment, subscription):
    """Template para confirmación de pago de membresía"""
    content = f"""
        <h2>¡Pago Confirmado!</h2>
        <p>Hola <strong>{user.first_name} {user.last_name}</strong>,</p>
        <p>Tu pago por la membresía <strong>{payment.membership_type.title()}</strong> ha sido procesado exitosamente.</p>
        
        <div class="info-box">
            <h3 style="margin-top: 0;">Detalles del Pago:</h3>
            <ul>
                <li><strong>Membresía:</strong> {payment.membership_type.title()}</li>
                <li><strong>Monto:</strong> ${payment.amount / 100:.2f}</li>
                <li><strong>Fecha de pago:</strong> {payment.created_at.strftime('%d/%m/%Y %H:%M')}</li>
                <li><strong>Válida hasta:</strong> {subscription.end_date.strftime('%d/%m/%Y')}</li>
                <li><strong>Estado:</strong> <span class="badge">Activa</span></li>
            </ul>
        </div>
        
        <p>Ya puedes acceder a todos los beneficios de tu membresía desde tu dashboard.</p>
        <p style="text-align: center;">
            <a href="https://relaticpanama.org/dashboard" class="button">Ir a mi Dashboard</a>
        </p>
        
        <p>¡Gracias por ser parte de RelaticPanama!</p>
    """
    return get_email_template_base().format(
        subject="Confirmación de Pago - RelaticPanama",
        content=content,
        year=datetime.now().year
    )


def get_membership_expiring_email(user, subscription, days_left):
    """Template para notificación de membresía por expirar"""
    content = f"""
        <h2>Tu Membresía Expirará Pronto</h2>
        <p>Hola <strong>{user.first_name} {user.last_name}</strong>,</p>
        <p>Te informamos que tu membresía <strong>{subscription.membership_type.title()}</strong> expirará en <strong>{days_left} días</strong>.</p>
        
        <div class="info-box">
            <h3 style="margin-top: 0;">Detalles:</h3>
            <ul>
                <li><strong>Membresía:</strong> {subscription.membership_type.title()}</li>
                <li><strong>Fecha de expiración:</strong> {subscription.end_date.strftime('%d/%m/%Y')}</li>
                <li><strong>Días restantes:</strong> <span class="badge warning-badge">{days_left} días</span></li>
            </ul>
        </div>
        
        <p>Para continuar disfrutando de todos los beneficios, te recomendamos renovar tu membresía antes de la fecha de expiración.</p>
        <p style="text-align: center;">
            <a href="https://relaticpanama.org/membership" class="button">Renovar Membresía</a>
        </p>
    """
    return get_email_template_base().format(
        subject=f"Tu Membresía Expirará en {days_left} Días - RelaticPanama",
        content=content,
        year=datetime.now().year
    )


def get_membership_expired_email(user, subscription):
    """Template para notificación de membresía expirada"""
    content = f"""
        <h2>Tu Membresía Ha Expirado</h2>
        <p>Hola <strong>{user.first_name} {user.last_name}</strong>,</p>
        <p>Te informamos que tu membresía <strong>{subscription.membership_type.title()}</strong> ha expirado.</p>
        
        <div class="info-box">
            <h3 style="margin-top: 0;">Detalles:</h3>
            <ul>
                <li><strong>Membresía:</strong> {subscription.membership_type.title()}</li>
                <li><strong>Fecha de expiración:</strong> {subscription.end_date.strftime('%d/%m/%Y')}</li>
                <li><strong>Estado:</strong> <span class="badge danger-badge">Expirada</span></li>
            </ul>
        </div>
        
        <p>Para reactivar tu membresía y continuar disfrutando de todos los beneficios, puedes renovarla ahora.</p>
        <p style="text-align: center;">
            <a href="https://relaticpanama.org/membership" class="button">Renovar Membresía</a>
        </p>
    """
    return get_email_template_base().format(
        subject="Tu Membresía Ha Expirado - RelaticPanama",
        content=content,
        year=datetime.now().year
    )


def get_membership_renewed_email(user, subscription):
    """Template para confirmación de renovación de membresía"""
    content = f"""
        <h2>¡Membresía Renovada Exitosamente!</h2>
        <p>Hola <strong>{user.first_name} {user.last_name}</strong>,</p>
        <p>Tu membresía <strong>{subscription.membership_type.title()}</strong> ha sido renovada exitosamente.</p>
        
        <div class="info-box">
            <h3 style="margin-top: 0;">Detalles:</h3>
            <ul>
                <li><strong>Membresía:</strong> {subscription.membership_type.title()}</li>
                <li><strong>Fecha de inicio:</strong> {subscription.start_date.strftime('%d/%m/%Y')}</li>
                <li><strong>Válida hasta:</strong> {subscription.end_date.strftime('%d/%m/%Y')}</li>
                <li><strong>Estado:</strong> <span class="badge">Activa</span></li>
            </ul>
        </div>
        
        <p>Gracias por continuar siendo parte de RelaticPanama.</p>
        <p style="text-align: center;">
            <a href="https://relaticpanama.org/dashboard" class="button">Ir a mi Dashboard</a>
        </p>
    """
    return get_email_template_base().format(
        subject="Membresía Renovada - RelaticPanama",
        content=content,
        year=datetime.now().year
    )


def get_event_registration_email(event, user, registration):
    """Template para confirmación de registro a evento"""
    content = f"""
        <h2>Registro Confirmado</h2>
        <p>Hola <strong>{user.first_name} {user.last_name}</strong>,</p>
        <p>Tu registro al evento <strong>"{event.title}"</strong> ha sido confirmado.</p>
        
        <div class="info-box">
            <h3 style="margin-top: 0;">Detalles del Evento:</h3>
            <ul>
                <li><strong>Evento:</strong> {event.title}</li>
                <li><strong>Fecha:</strong> {event.start_date.strftime('%d/%m/%Y') if event.start_date else 'Por definir'}</li>
                <li><strong>Hora:</strong> {event.start_time if event.start_time else 'Por definir'}</li>
                <li><strong>Estado:</strong> <span class="badge">{registration.registration_status.title()}</span></li>
                <li><strong>Precio pagado:</strong> ${registration.final_price:.2f} {event.currency if event.currency else 'USD'}</li>
            </ul>
        </div>
        
        <p>Te enviaremos más información sobre el evento próximamente.</p>
        <p style="text-align: center;">
            <a href="https://relaticpanama.org/events/{event.id}" class="button">Ver Detalles del Evento</a>
        </p>
    """
    return get_email_template_base().format(
        subject=f"Registro Confirmado: {event.title}",
        content=content,
        year=datetime.now().year
    )


def get_event_cancellation_email(event, user):
    """Template para cancelación de registro a evento"""
    content = f"""
        <h2>Registro Cancelado</h2>
        <p>Hola <strong>{user.first_name} {user.last_name}</strong>,</p>
        <p>Tu registro al evento <strong>"{event.title}"</strong> ha sido cancelado.</p>
        
        <div class="info-box">
            <h3 style="margin-top: 0;">Detalles:</h3>
            <ul>
                <li><strong>Evento:</strong> {event.title}</li>
                <li><strong>Fecha de cancelación:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</li>
            </ul>
        </div>
        
        <p>Si tienes alguna pregunta o necesitas asistencia, no dudes en contactarnos.</p>
    """
    return get_email_template_base().format(
        subject=f"Cancelación de Registro: {event.title}",
        content=content,
        year=datetime.now().year
    )


def get_event_update_email(event, user, changes=None):
    """Template para actualización de evento"""
    changes_text = ""
    if changes:
        changes_text = "<ul>"
        for change in changes:
            changes_text += f"<li>{change}</li>"
        changes_text += "</ul>"
    
    content = f"""
        <h2>Evento Actualizado</h2>
        <p>Hola <strong>{user.first_name} {user.last_name}</strong>,</p>
        <p>El evento <strong>"{event.title}"</strong> al que estás registrado ha sido actualizado.</p>
        
        <div class="info-box">
            <h3 style="margin-top: 0;">Cambios Realizados:</h3>
            {changes_text if changes_text else '<p>Se han realizado cambios en los detalles del evento.</p>'}
        </div>
        
        <p>Te recomendamos revisar los detalles actualizados del evento.</p>
        <p style="text-align: center;">
            <a href="https://relaticpanama.org/events/{event.id}" class="button">Ver Detalles Actualizados</a>
        </p>
    """
    return get_email_template_base().format(
        subject=f"Actualización: {event.title}",
        content=content,
        year=datetime.now().year
    )


def get_appointment_confirmation_email(appointment, user, advisor):
    """Template para confirmación de cita (soporta start_datetime o appointment_date/appointment_time)."""
    if getattr(appointment, 'start_datetime', None):
        fecha = appointment.start_datetime.strftime('%d/%m/%Y')
        hora = appointment.start_datetime.strftime('%H:%M')
    else:
        fecha = getattr(appointment, 'appointment_date', None)
        fecha = fecha.strftime('%d/%m/%Y') if fecha else 'Pendiente'
        hora = getattr(appointment, 'appointment_time', None) or 'Pendiente'
    tipo = getattr(appointment.appointment_type, 'name', None) if getattr(appointment, 'appointment_type', None) else getattr(appointment, 'appointment_type', 'Cita')
    content = f"""
        <h2>Cita Confirmada</h2>
        <p>Hola <strong>{user.first_name} {user.last_name}</strong>,</p>
        <p>Tu cita con <strong>{advisor.first_name} {advisor.last_name}</strong> ha sido confirmada.</p>
        
        <div class="info-box">
            <h3 style="margin-top: 0;">Detalles de la Cita:</h3>
            <ul>
                <li><strong>Asesor:</strong> {advisor.first_name} {advisor.last_name}</li>
                <li><strong>Fecha:</strong> {fecha}</li>
                <li><strong>Hora:</strong> {hora}</li>
                <li><strong>Tipo:</strong> {tipo}</li>
                <li><strong>Estado:</strong> <span class="badge">Confirmada</span></li>
            </ul>
        </div>
        
        <p>Te recordaremos la cita con anticipación.</p>
        <p style="text-align: center;">
            <a href="https://relaticpanama.org/appointments" class="button">Ver Mis Citas</a>
        </p>
    """
    return get_email_template_base().format(
        subject="Cita Confirmada - RelaticPanama",
        content=content,
        year=datetime.now().year
    )


def get_appointment_reminder_email(appointment, user, advisor, hours_before=24):
    """Template para recordatorio de cita"""
    content = f"""
        <h2>Recordatorio de Cita</h2>
        <p>Hola <strong>{user.first_name} {user.last_name}</strong>,</p>
        <p>Te recordamos que tienes una cita programada en <strong>{hours_before} horas</strong>.</p>
        
        <div class="info-box">
            <h3 style="margin-top: 0;">Detalles de la Cita:</h3>
            <ul>
                <li><strong>Asesor:</strong> {advisor.first_name} {advisor.last_name}</li>
                <li><strong>Fecha:</strong> {appointment.appointment_date.strftime('%d/%m/%Y')}</li>
                <li><strong>Hora:</strong> {appointment.appointment_time}</li>
                <li><strong>Duración:</strong> {appointment.duration} minutos</li>
            </ul>
        </div>
        
        <p>Por favor, asegúrate de estar disponible a la hora programada.</p>
        <p style="text-align: center;">
            <a href="https://relaticpanama.org/appointments" class="button">Ver Mis Citas</a>
        </p>
    """
    return get_email_template_base().format(
        subject=f"Recordatorio: Cita en {hours_before} horas - RelaticPanama",
        content=content,
        year=datetime.now().year
    )


def get_appointment_created_email(appointment, user, advisor, service):
    """Template para email al cliente cuando se crea la cita después del pago"""
    advisor_name = f"{advisor.first_name} {advisor.last_name}" if advisor else "Asesor asignado"
    service_name = service.name if service else appointment.appointment_type.name if appointment.appointment_type else "Servicio"
    start_date = appointment.start_datetime.strftime('%d/%m/%Y') if appointment.start_datetime else "Fecha pendiente"
    start_time = appointment.start_datetime.strftime('%H:%M') if appointment.start_datetime else "Hora pendiente"
    
    content = f"""
        <h2>Cita Agendada Exitosamente</h2>
        <p>Hola <strong>{user.first_name} {user.last_name}</strong>,</p>
        <p>Tu cita ha sido agendada exitosamente después del pago. La cita está <strong>pendiente de confirmación</strong> por parte del asesor.</p>
        
        <div class="info-box">
            <h3 style="margin-top: 0;">Detalles de la Cita:</h3>
            <ul>
                <li><strong>Servicio:</strong> {service_name}</li>
                <li><strong>Asesor:</strong> {advisor_name}</li>
                <li><strong>Fecha:</strong> {start_date}</li>
                <li><strong>Hora:</strong> {start_time}</li>
                <li><strong>Estado:</strong> Pendiente de confirmación</li>
                <li><strong>Referencia:</strong> {appointment.reference if hasattr(appointment, 'reference') else 'N/A'}</li>
            </ul>
        </div>
        
        <p><strong>Nota importante:</strong> Recibirás una notificación cuando el asesor confirme tu cita. Mientras tanto, puedes revisar el estado en tu panel.</p>
        
        <p style="text-align: center;">
            <a href="https://relaticpanama.org/appointments" class="button">Ver Mis Citas</a>
        </p>
    """
    return get_email_template_base().format(
        subject="Cita Agendada - RelaticPanama",
        content=content,
        year=datetime.now().year
    )


def get_appointment_new_advisor_email(appointment, user, advisor, service):
    """Template para email al asesor sobre nueva cita pendiente de confirmación"""
    service_name = service.name if service else appointment.appointment_type.name if appointment.appointment_type else "Servicio"
    start_date = appointment.start_datetime.strftime('%d/%m/%Y') if appointment.start_datetime else "Fecha pendiente"
    start_time = appointment.start_datetime.strftime('%H:%M') if appointment.start_datetime else "Hora pendiente"
    case_description = appointment.user_notes if hasattr(appointment, 'user_notes') and appointment.user_notes else "Sin descripción adicional"
    
    content = f"""
        <h2>Nueva Cita Pendiente de Confirmación</h2>
        <p>Hola <strong>{advisor.first_name} {advisor.last_name}</strong>,</p>
        <p>Has recibido una nueva solicitud de cita que requiere tu confirmación.</p>
        
        <div class="info-box">
            <h3 style="margin-top: 0;">Detalles de la Cita:</h3>
            <ul>
                <li><strong>Cliente:</strong> {user.first_name} {user.last_name} ({user.email})</li>
                <li><strong>Servicio:</strong> {service_name}</li>
                <li><strong>Fecha:</strong> {start_date}</li>
                <li><strong>Hora:</strong> {start_time}</li>
                <li><strong>Descripción del caso:</strong> {case_description[:200]}{'...' if len(case_description) > 200 else ''}</li>
                <li><strong>Referencia:</strong> {appointment.reference if hasattr(appointment, 'reference') else 'N/A'}</li>
            </ul>
        </div>
        
        <p><strong>Acción requerida:</strong> Por favor, confirma o cancela esta cita desde tu panel de administración.</p>
        
        <p style="text-align: center;">
            <a href="https://relaticpanama.org/admin/appointments" class="button">Gestionar Citas</a>
        </p>
    """
    return get_email_template_base().format(
        subject="Nueva Cita Pendiente de Confirmación - RelaticPanama",
        content=content,
        year=datetime.now().year
    )


def get_appointment_new_admin_email(appointment, user, advisor, service, admin):
    """Template para email a administradores sobre nueva cita creada"""
    advisor_name = f"{advisor.first_name} {advisor.last_name}" if advisor else "No asignado"
    service_name = service.name if service else appointment.appointment_type.name if appointment.appointment_type else "Servicio"
    start_date = appointment.start_datetime.strftime('%d/%m/%Y') if appointment.start_datetime else "Fecha pendiente"
    start_time = appointment.start_datetime.strftime('%H:%M') if appointment.start_datetime else "Hora pendiente"
    
    content = f"""
        <h2>Nueva Cita Creada en el Sistema</h2>
        <p>Hola <strong>{admin.first_name} {admin.last_name}</strong>,</p>
        <p>Se ha creado una nueva cita en el sistema después de un pago exitoso.</p>
        
        <div class="info-box">
            <h3 style="margin-top: 0;">Detalles de la Cita:</h3>
            <ul>
                <li><strong>Cliente:</strong> {user.first_name} {user.last_name} ({user.email})</li>
                <li><strong>Servicio:</strong> {service_name}</li>
                <li><strong>Asesor:</strong> {advisor_name}</li>
                <li><strong>Fecha:</strong> {start_date}</li>
                <li><strong>Hora:</strong> {start_time}</li>
                <li><strong>Estado:</strong> Pendiente de confirmación</li>
                <li><strong>Referencia:</strong> {appointment.reference if hasattr(appointment, 'reference') else 'N/A'}</li>
                <li><strong>Pago:</strong> Completado</li>
            </ul>
        </div>
        
        <p>Esta cita está pendiente de confirmación por parte del asesor asignado.</p>
        
        <p style="text-align: center;">
            <a href="https://relaticpanama.org/admin/appointments" class="button">Ver Todas las Citas</a>
        </p>
    """
    return get_email_template_base().format(
        subject="Nueva Cita Creada - RelaticPanama",
        content=content,
        year=datetime.now().year
    )


def get_welcome_email(user):
    """Template para email de bienvenida usando el nuevo template HTML"""
    try:
        # Importar get_public_image_url desde app
        from app import get_public_image_url, app
        import os
        from flask import has_request_context, request
        
        # Generar URLs absolutas (necesarias para emails)
        # Verificar si el logo existe en la ubicación esperada
        logo_path_png = os.path.join(os.path.dirname(__file__), '..', 'static', 'public', 'emails', 'logos', 'logo-relatic.png')
        logo_path_svg = os.path.join(os.path.dirname(__file__), '..', 'static', 'images', 'logo-relatic.svg')
        
        # Obtener base_url - usar request si está disponible, sino usar variable de entorno o default
        if has_request_context() and request:
            base_url = request.url_root.rstrip('/')
        else:
            base_url = os.getenv('BASE_URL', 'https://miembros.relatic.org')
        
        if os.path.exists(logo_path_png):
            # Usar logo PNG de la carpeta pública
            try:
                logo_url = get_public_image_url('emails/logos/logo-relatic.png', absolute=True)
            except Exception as e:
                # Si falla get_public_image_url (por falta de contexto), construir manualmente
                logo_url = f"{base_url}/static/public/emails/logos/logo-relatic.png"
        elif os.path.exists(logo_path_svg):
            # Fallback: usar logo SVG existente (convertir a URL absoluta)
            logo_url = f"{base_url}/static/images/logo-relatic.svg"
            print("⚠️ Usando logo SVG existente. Para mejor compatibilidad con emails, convierte a PNG y colócalo en static/public/emails/logos/logo-relatic.png")
        else:
            # No hay logo disponible
            logo_url = None
            print("⚠️ Logo no encontrado. Coloca logo-relatic.png en static/public/emails/logos/")
        
        login_url = f"{base_url}/login"
        
        # Renderizar el nuevo template HTML - usar app_context si no hay request context
        if has_request_context():
            html = render_template('emails/sistema/bienvenida.html',
                                  logo_url=logo_url,
                                  user_first_name=user.first_name,
                                  user_last_name=user.last_name,
                                  login_url=login_url,
                                  base_url=base_url,
                                  year=datetime.now().year,
                                  contact_email='administracion@relaticpanama.org')
        else:
            # Si no hay request context, usar app_context
            with app.app_context():
                html = render_template('emails/sistema/bienvenida.html',
                                      logo_url=logo_url,
                                      user_first_name=user.first_name,
                                      user_last_name=user.last_name,
                                      login_url=login_url,
                                      base_url=base_url,
                                      year=datetime.now().year,
                                      contact_email='administracion@relaticpanama.org')
        
        return html
    except Exception as e:
        # Fallback al template anterior si hay error
        import traceback
        traceback.print_exc()
        print(f"⚠️ Error al cargar template de bienvenida: {e}")
        content = f"""
            <h2>¡Bienvenido a RelaticPanama!</h2>
            <p>Hola <strong>{user.first_name} {user.last_name}</strong>,</p>
            <p>Te damos la bienvenida a RelaticPanama, la Red Latinoamericana de Investigaciones Cualitativas.</p>
            
            <div class="info-box">
                <h3 style="margin-top: 0;">¿Qué puedes hacer ahora?</h3>
                <ul>
                    <li>Explorar nuestros eventos y cursos</li>
                    <li>Acceder a recursos exclusivos</li>
                    <li>Conectar con otros investigadores</li>
                    <li>Gestionar tu membresía</li>
                </ul>
            </div>
            
            <p>Estamos aquí para apoyarte en tu investigación cualitativa.</p>
            <p style="text-align: center;">
                <a href="https://miembros.relatic.org/login" class="button">Ir a mi Dashboard</a>
            </p>
        """
        return get_email_template_base().format(
            subject="Bienvenido a RelaticPanama",
            content=content,
            year=datetime.now().year
        )


def get_password_reset_email(user, reset_token, reset_url):
    """Template para restablecimiento de contraseña"""
    content = f"""
        <h2>Restablecer Contraseña</h2>
        <p>Hola <strong>{user.first_name} {user.last_name}</strong>,</p>
        <p>Has solicitado restablecer tu contraseña. Haz clic en el botón siguiente para continuar:</p>
        
        <p style="text-align: center;">
            <a href="{reset_url}" class="button">Restablecer Contraseña</a>
        </p>
        
        <p>Si no solicitaste este cambio, puedes ignorar este correo. El enlace expirará en 1 hora.</p>
        
        <p><small>O copia y pega este enlace en tu navegador:</small><br>
        <small style="color: #666; word-break: break-all;">{reset_url}</small></p>
    """
    return get_email_template_base().format(
        subject="Restablecer Contraseña - RelaticPanama",
        content=content,
        year=datetime.now().year
    )


def get_email_verification_email(user, verification_url):
    """Template para verificación de email usando el nuevo template HTML"""
    try:
        # Importar get_public_image_url desde app
        from app import get_public_image_url, app
        import os
        from flask import has_request_context, request
        
        # Generar URLs absolutas (necesarias para emails)
        logo_path_png = os.path.join(os.path.dirname(__file__), '..', 'static', 'public', 'emails', 'logos', 'logo-relatic.png')
        logo_path_svg = os.path.join(os.path.dirname(__file__), '..', 'static', 'images', 'logo-relatic.svg')
        
        # Obtener base_url
        if has_request_context() and request:
            base_url = request.url_root.rstrip('/')
        else:
            base_url = os.getenv('BASE_URL', 'https://miembros.relatic.org')
        
        if os.path.exists(logo_path_png):
            try:
                logo_url = get_public_image_url('emails/logos/logo-relatic.png', absolute=True)
            except Exception:
                logo_url = f"{base_url}/static/public/emails/logos/logo-relatic.png"
        elif os.path.exists(logo_path_svg):
            logo_url = f"{base_url}/static/images/logo-relatic.svg"
        else:
            logo_url = None
        
        # Renderizar el template HTML
        if has_request_context():
            html = render_template('emails/sistema/verificacion_email.html',
                                  logo_url=logo_url,
                                  user_first_name=user.first_name,
                                  user_last_name=user.last_name,
                                  verification_url=verification_url,
                                  year=datetime.now().year,
                                  contact_email='administracion@relaticpanama.org')
        else:
            with app.app_context():
                html = render_template('emails/sistema/verificacion_email.html',
                                      logo_url=logo_url,
                                      user_first_name=user.first_name,
                                      user_last_name=user.last_name,
                                      verification_url=verification_url,
                                      year=datetime.now().year,
                                      contact_email='administracion@relaticpanama.org')
        
        return html
    except Exception as e:
        # Fallback al template anterior si hay error
        import traceback
        traceback.print_exc()
        content = f"""
            <h2>Verifica tu Correo Electrónico</h2>
            <p>Hola <strong>{user.first_name} {user.last_name}</strong>,</p>
            <p>Gracias por registrarte en RelaticPanama. Para completar tu registro, verifica tu email haciendo clic en el siguiente enlace:</p>
            <p style="text-align: center;">
                <a href="{verification_url}" class="button">Verificar mi Email</a>
            </p>
            <p>Este enlace expirará en 24 horas.</p>
            <p><small>O copia y pega este enlace en tu navegador:</small><br>
            <small style="color: #666; word-break: break-all;">{verification_url}</small></p>
        """
        return get_email_template_base().format(
            subject="Verifica tu Email - RelaticPanama",
            content=content,
            year=datetime.now().year
        )

