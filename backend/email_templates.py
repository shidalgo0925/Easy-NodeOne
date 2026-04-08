#!/usr/bin/env python3
"""
Plantillas de correo HTML por defecto (fallback cuando email_template no es custom).
Branding: organization_name, base_url, contact_email vía kwargs o variables de entorno.
"""

import html as html_module
import os
from datetime import datetime
from flask import render_template, request


def _default_platform_display_name():
    return (os.environ.get('PLATFORM_DISPLAY_NAME') or 'Easy NodeOne').strip() or 'Easy NodeOne'


def _default_base_url():
    u = (os.environ.get('BASE_URL') or '').strip().rstrip('/')
    return u or 'https://app.easynodeone.com'


def _default_contact_email():
    return (os.environ.get('PLATFORM_CONTACT_EMAIL') or os.environ.get('SUPPORT_EMAIL') or '').strip() or 'noreply@localhost'


def _appointment_org_service_lines_html(appointment, branding_organization_name):
    """Marca (tenant) y nombre de servicio por separado para correos."""
    org_esc = html_module.escape(str(branding_organization_name or '').strip() or '—')
    at = getattr(appointment, 'appointment_type', None)
    if at is not None and hasattr(at, 'public_service_label'):
        svc_esc = html_module.escape(at.public_service_label())
    else:
        svc_esc = html_module.escape(str(getattr(at, 'name', None) or 'Servicio'))
    return org_esc, svc_esc


def _merge_branding(organization_name=None, base_url=None, contact_email=None, org_tagline=None):
    """Valores sin escapar; escapar al insertar en HTML."""
    return {
        'organization_name': (organization_name if organization_name is not None else _default_platform_display_name())
        or _default_platform_display_name(),
        'base_url': ((base_url if base_url is not None else _default_base_url()) or _default_base_url()).rstrip('/'),
        'contact_email': (contact_email if contact_email is not None else _default_contact_email())
        or _default_contact_email(),
        'org_tagline': (org_tagline if org_tagline is not None else (os.environ.get('PLATFORM_TAGLINE') or '')).strip(),
    }


def get_email_template_base(subject, content, year=None, *, organization_name=None, base_url=None, contact_email=None, org_tagline=None):
    """Shell HTML: cabecera/pie con nombre de organización y contacto dinámicos."""
    b = _merge_branding(organization_name, base_url, contact_email, org_tagline)
    year = year or datetime.now().year
    oname = html_module.escape(str(b['organization_name']))
    cmail = html_module.escape(str(b['contact_email']))
    subj_esc = html_module.escape(str(subject))
    tagline_html = ''
    if b['org_tagline']:
        tagline_html = f'<p style="color: #666; margin: 5px 0;">{html_module.escape(b["org_tagline"])}</p>'
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{subj_esc}</title>
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
                <h1>{oname}</h1>
                {tagline_html}
            </div>
            <div class="content">
                {content}
            </div>
            <div class="footer">
                <p>Este es un correo automático de {oname}. Por favor, no responda a este mensaje.</p>
                <p>Si tiene alguna consulta, contacte a: <a href="mailto:{cmail}">{cmail}</a></p>
                <p>&copy; {year} {oname}. Todos los derechos reservados.</p>
            </div>
        </div>
    </body>
    </html>
    """


def get_membership_payment_confirmation_email(user, payment, subscription, *, organization_name=None, base_url=None, contact_email=None, org_tagline=None):
    """Template para confirmación de pago de membresía"""
    b = _merge_branding(organization_name, base_url, contact_email, org_tagline)
    bu, on = b['base_url'], html_module.escape(b['organization_name'])
    content = f"""
        <h2>¡Pago Confirmado!</h2>
        <p>Hola <strong>{html_module.escape(str(user.first_name))} {html_module.escape(str(user.last_name))}</strong>,</p>
        <p>Tu pago por la membresía <strong>{html_module.escape(str(payment.membership_type).title())}</strong> ha sido procesado exitosamente.</p>
        
        <div class="info-box">
            <h3 style="margin-top: 0;">Detalles del Pago:</h3>
            <ul>
                <li><strong>Membresía:</strong> {html_module.escape(str(payment.membership_type).title())}</li>
                <li><strong>Monto:</strong> ${payment.amount / 100:.2f}</li>
                <li><strong>Fecha de pago:</strong> {payment.created_at.strftime('%d/%m/%Y %H:%M')}</li>
                <li><strong>Válida hasta:</strong> {subscription.end_date.strftime('%d/%m/%Y')}</li>
                <li><strong>Estado:</strong> <span class="badge">Activa</span></li>
            </ul>
        </div>
        
        <p>Ya puedes acceder a todos los beneficios de tu membresía desde tu dashboard.</p>
        <p style="text-align: center;">
            <a href="{html_module.escape(bu)}/dashboard" class="button">Ir a mi Dashboard</a>
        </p>
        
        <p>¡Gracias por ser parte de {on}!</p>
    """
    return get_email_template_base(
        f"Confirmación de Pago - {b['organization_name']}",
        content,
        year=datetime.now().year,
        organization_name=b['organization_name'],
        base_url=b['base_url'],
        contact_email=b['contact_email'],
        org_tagline=b['org_tagline'] or None,
    )


def get_membership_expiring_email(user, subscription, days_left, *, organization_name=None, base_url=None, contact_email=None, org_tagline=None):
    """Template para notificación de membresía por expirar"""
    b = _merge_branding(organization_name, base_url, contact_email, org_tagline)
    bu = b['base_url']
    content = f"""
        <h2>Tu Membresía Expirará Pronto</h2>
        <p>Hola <strong>{html_module.escape(str(user.first_name))} {html_module.escape(str(user.last_name))}</strong>,</p>
        <p>Te informamos que tu membresía <strong>{html_module.escape(str(subscription.membership_type).title())}</strong> expirará en <strong>{int(days_left)} días</strong>.</p>
        
        <div class="info-box">
            <h3 style="margin-top: 0;">Detalles:</h3>
            <ul>
                <li><strong>Membresía:</strong> {html_module.escape(str(subscription.membership_type).title())}</li>
                <li><strong>Fecha de expiración:</strong> {subscription.end_date.strftime('%d/%m/%Y')}</li>
                <li><strong>Días restantes:</strong> <span class="badge warning-badge">{int(days_left)} días</span></li>
            </ul>
        </div>
        
        <p>Para continuar disfrutando de todos los beneficios, te recomendamos renovar tu membresía antes de la fecha de expiración.</p>
        <p style="text-align: center;">
            <a href="{html_module.escape(bu)}/membership" class="button">Renovar Membresía</a>
        </p>
    """
    return get_email_template_base(
        f"Tu Membresía Expirará en {days_left} Días - {b['organization_name']}",
        content,
        year=datetime.now().year,
        organization_name=b['organization_name'],
        base_url=b['base_url'],
        contact_email=b['contact_email'],
        org_tagline=b['org_tagline'] or None,
    )


def get_membership_expired_email(user, subscription, *, organization_name=None, base_url=None, contact_email=None, org_tagline=None):
    """Template para notificación de membresía expirada"""
    b = _merge_branding(organization_name, base_url, contact_email, org_tagline)
    bu = b['base_url']
    content = f"""
        <h2>Tu Membresía Ha Expirado</h2>
        <p>Hola <strong>{html_module.escape(str(user.first_name))} {html_module.escape(str(user.last_name))}</strong>,</p>
        <p>Te informamos que tu membresía <strong>{html_module.escape(str(subscription.membership_type).title())}</strong> ha expirado.</p>
        
        <div class="info-box">
            <h3 style="margin-top: 0;">Detalles:</h3>
            <ul>
                <li><strong>Membresía:</strong> {html_module.escape(str(subscription.membership_type).title())}</li>
                <li><strong>Fecha de expiración:</strong> {subscription.end_date.strftime('%d/%m/%Y')}</li>
                <li><strong>Estado:</strong> <span class="badge danger-badge">Expirada</span></li>
            </ul>
        </div>
        
        <p>Para reactivar tu membresía y continuar disfrutando de todos los beneficios, puedes renovarla ahora.</p>
        <p style="text-align: center;">
            <a href="{html_module.escape(bu)}/membership" class="button">Renovar Membresía</a>
        </p>
    """
    return get_email_template_base(
        f"Tu Membresía Ha Expirado - {b['organization_name']}",
        content,
        year=datetime.now().year,
        organization_name=b['organization_name'],
        base_url=b['base_url'],
        contact_email=b['contact_email'],
        org_tagline=b['org_tagline'] or None,
    )


def get_membership_renewed_email(user, subscription, *, organization_name=None, base_url=None, contact_email=None, org_tagline=None):
    """Template para confirmación de renovación de membresía"""
    b = _merge_branding(organization_name, base_url, contact_email, org_tagline)
    bu, on = b['base_url'], html_module.escape(b['organization_name'])
    content = f"""
        <h2>¡Membresía Renovada Exitosamente!</h2>
        <p>Hola <strong>{html_module.escape(str(user.first_name))} {html_module.escape(str(user.last_name))}</strong>,</p>
        <p>Tu membresía <strong>{html_module.escape(str(subscription.membership_type).title())}</strong> ha sido renovada exitosamente.</p>
        
        <div class="info-box">
            <h3 style="margin-top: 0;">Detalles:</h3>
            <ul>
                <li><strong>Membresía:</strong> {html_module.escape(str(subscription.membership_type).title())}</li>
                <li><strong>Fecha de inicio:</strong> {subscription.start_date.strftime('%d/%m/%Y')}</li>
                <li><strong>Válida hasta:</strong> {subscription.end_date.strftime('%d/%m/%Y')}</li>
                <li><strong>Estado:</strong> <span class="badge">Activa</span></li>
            </ul>
        </div>
        
        <p>Gracias por continuar siendo parte de {on}.</p>
        <p style="text-align: center;">
            <a href="{html_module.escape(bu)}/dashboard" class="button">Ir a mi Dashboard</a>
        </p>
    """
    return get_email_template_base(
        f"Membresía Renovada - {b['organization_name']}",
        content,
        year=datetime.now().year,
        organization_name=b['organization_name'],
        base_url=b['base_url'],
        contact_email=b['contact_email'],
        org_tagline=b['org_tagline'] or None,
    )


def get_event_registration_email(event, user, registration, *, organization_name=None, base_url=None, contact_email=None, org_tagline=None):
    """Template para confirmación de registro a evento"""
    b = _merge_branding(organization_name, base_url, contact_email, org_tagline)
    bu = b['base_url']
    etitle = html_module.escape(str(event.title))
    content = f"""
        <h2>Registro Confirmado</h2>
        <p>Hola <strong>{html_module.escape(str(user.first_name))} {html_module.escape(str(user.last_name))}</strong>,</p>
        <p>Tu registro al evento <strong>"{etitle}"</strong> ha sido confirmado.</p>
        
        <div class="info-box">
            <h3 style="margin-top: 0;">Detalles del Evento:</h3>
            <ul>
                <li><strong>Evento:</strong> {etitle}</li>
                <li><strong>Fecha:</strong> {event.start_date.strftime('%d/%m/%Y') if event.start_date else 'Por definir'}</li>
                <li><strong>Hora:</strong> {html_module.escape(str(event.start_time)) if event.start_time else 'Por definir'}</li>
                <li><strong>Estado:</strong> <span class="badge">{html_module.escape(str(registration.registration_status).title())}</span></li>
                <li><strong>Precio pagado:</strong> ${registration.final_price:.2f} {html_module.escape(str(event.currency or 'USD'))}</li>
            </ul>
        </div>
        
        <p>Te enviaremos más información sobre el evento próximamente.</p>
        <p style="text-align: center;">
            <a href="{html_module.escape(bu)}/events/{int(event.id)}" class="button">Ver Detalles del Evento</a>
        </p>
    """
    return get_email_template_base(
        f"Registro Confirmado: {event.title}",
        content,
        year=datetime.now().year,
        organization_name=b['organization_name'],
        base_url=b['base_url'],
        contact_email=b['contact_email'],
        org_tagline=b['org_tagline'] or None,
    )


def get_event_cancellation_email(event, user, *, organization_name=None, base_url=None, contact_email=None, org_tagline=None):
    """Template para cancelación de registro a evento"""
    b = _merge_branding(organization_name, base_url, contact_email, org_tagline)
    etitle = html_module.escape(str(event.title))
    content = f"""
        <h2>Registro Cancelado</h2>
        <p>Hola <strong>{html_module.escape(str(user.first_name))} {html_module.escape(str(user.last_name))}</strong>,</p>
        <p>Tu registro al evento <strong>"{etitle}"</strong> ha sido cancelado.</p>
        
        <div class="info-box">
            <h3 style="margin-top: 0;">Detalles:</h3>
            <ul>
                <li><strong>Evento:</strong> {etitle}</li>
                <li><strong>Fecha de cancelación:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</li>
            </ul>
        </div>
        
        <p>Si tienes alguna pregunta o necesitas asistencia, no dudes en contactarnos.</p>
    """
    return get_email_template_base(
        f"Cancelación de Registro: {event.title}",
        content,
        year=datetime.now().year,
        organization_name=b['organization_name'],
        base_url=b['base_url'],
        contact_email=b['contact_email'],
        org_tagline=b['org_tagline'] or None,
    )


def get_event_update_email(event, user, changes=None, *, organization_name=None, base_url=None, contact_email=None, org_tagline=None):
    """Template para actualización de evento"""
    b = _merge_branding(organization_name, base_url, contact_email, org_tagline)
    bu = b['base_url']
    changes_text = ""
    if changes:
        changes_text = "<ul>"
        for change in changes:
            changes_text += f"<li>{html_module.escape(str(change))}</li>"
        changes_text += "</ul>"
    etitle = html_module.escape(str(event.title))
    content = f"""
        <h2>Evento Actualizado</h2>
        <p>Hola <strong>{html_module.escape(str(user.first_name))} {html_module.escape(str(user.last_name))}</strong>,</p>
        <p>El evento <strong>"{etitle}"</strong> al que estás registrado ha sido actualizado.</p>
        
        <div class="info-box">
            <h3 style="margin-top: 0;">Cambios Realizados:</h3>
            {changes_text if changes_text else '<p>Se han realizado cambios en los detalles del evento.</p>'}
        </div>
        
        <p>Te recomendamos revisar los detalles actualizados del evento.</p>
        <p style="text-align: center;">
            <a href="{html_module.escape(bu)}/events/{int(event.id)}" class="button">Ver Detalles Actualizados</a>
        </p>
    """
    return get_email_template_base(
        f"Actualización: {event.title}",
        content,
        year=datetime.now().year,
        organization_name=b['organization_name'],
        base_url=b['base_url'],
        contact_email=b['contact_email'],
        org_tagline=b['org_tagline'] or None,
    )


def get_appointment_confirmation_email(appointment, user, advisor, *, organization_name=None, base_url=None, contact_email=None, org_tagline=None):
    """Template para confirmación de cita (soporta start_datetime o appointment_date/appointment_time)."""
    b = _merge_branding(organization_name, base_url, contact_email, org_tagline)
    bu = b['base_url']
    org_esc, svc_esc = _appointment_org_service_lines_html(appointment, b['organization_name'])
    if getattr(appointment, 'start_datetime', None):
        fecha = appointment.start_datetime.strftime('%d/%m/%Y')
        hora = appointment.start_datetime.strftime('%H:%M')
    else:
        fecha = getattr(appointment, 'appointment_date', None)
        fecha = fecha.strftime('%d/%m/%Y') if fecha else 'Pendiente'
        hora = getattr(appointment, 'appointment_time', None) or 'Pendiente'
    afn = html_module.escape(f'{advisor.first_name} {advisor.last_name}')
    content = f"""
        <h2>Cita Confirmada</h2>
        <p>Hola <strong>{html_module.escape(str(user.first_name))} {html_module.escape(str(user.last_name))}</strong>,</p>
        <p>Tu cita con <strong>{afn}</strong> ha sido confirmada.</p>
        
        <div class="info-box">
            <h3 style="margin-top: 0;">Detalles de la Cita:</h3>
            <ul>
                <li><strong>Organización:</strong> {org_esc}</li>
                <li><strong>Servicio:</strong> {svc_esc}</li>
                <li><strong>Asesor:</strong> {afn}</li>
                <li><strong>Fecha:</strong> {fecha}</li>
                <li><strong>Hora:</strong> {hora}</li>
                <li><strong>Estado:</strong> <span class="badge">Confirmada</span></li>
            </ul>
        </div>
        
        <p>Te recordaremos la cita con anticipación.</p>
        <p style="text-align: center;">
            <a href="{html_module.escape(bu)}/appointments" class="button">Ver Mis Citas</a>
        </p>
    """
    return get_email_template_base(
        f"Cita Confirmada - {b['organization_name']}",
        content,
        year=datetime.now().year,
        organization_name=b['organization_name'],
        base_url=b['base_url'],
        contact_email=b['contact_email'],
        org_tagline=b['org_tagline'] or None,
    )


def get_appointment_reminder_email(appointment, user, advisor, hours_before=24, *, organization_name=None, base_url=None, contact_email=None, org_tagline=None):
    """Template para recordatorio de cita"""
    b = _merge_branding(organization_name, base_url, contact_email, org_tagline)
    bu = b['base_url']
    org_esc, svc_esc = _appointment_org_service_lines_html(appointment, b['organization_name'])
    afn = html_module.escape(f'{advisor.first_name} {advisor.last_name}')
    if getattr(appointment, 'start_datetime', None):
        fecha_rem = appointment.start_datetime.strftime('%d/%m/%Y')
        hora_rem = appointment.start_datetime.strftime('%H:%M')
    else:
        ad = getattr(appointment, 'appointment_date', None)
        fecha_rem = ad.strftime('%d/%m/%Y') if ad else 'Pendiente'
        hora_rem = html_module.escape(str(getattr(appointment, 'appointment_time', None) or 'Pendiente'))
    dur_min = getattr(appointment, 'duration_minutes', None)
    if dur_min is None and callable(getattr(appointment, 'get_duration_minutes', None)):
        try:
            dur_min = appointment.get_duration_minutes()
        except Exception:
            dur_min = None
    if dur_min is None:
        at = getattr(appointment, 'appointment_type', None)
        if at is not None:
            dur_min = getattr(at, 'duration_minutes', None) or 60
        else:
            dur_min = 60
    content = f"""
        <h2>Recordatorio de Cita</h2>
        <p>Hola <strong>{html_module.escape(str(user.first_name))} {html_module.escape(str(user.last_name))}</strong>,</p>
        <p>Te recordamos que tienes una cita programada en <strong>{int(hours_before)} horas</strong>.</p>
        
        <div class="info-box">
            <h3 style="margin-top: 0;">Detalles de la Cita:</h3>
            <ul>
                <li><strong>Organización:</strong> {org_esc}</li>
                <li><strong>Servicio:</strong> {svc_esc}</li>
                <li><strong>Asesor:</strong> {afn}</li>
                <li><strong>Fecha:</strong> {fecha_rem}</li>
                <li><strong>Hora:</strong> {hora_rem}</li>
                <li><strong>Duración:</strong> {int(dur_min)} minutos</li>
            </ul>
        </div>
        
        <p>Por favor, asegúrate de estar disponible a la hora programada.</p>
        <p style="text-align: center;">
            <a href="{html_module.escape(bu)}/appointments" class="button">Ver Mis Citas</a>
        </p>
    """
    return get_email_template_base(
        f"Recordatorio: Cita en {hours_before} horas - {b['organization_name']}",
        content,
        year=datetime.now().year,
        organization_name=b['organization_name'],
        base_url=b['base_url'],
        contact_email=b['contact_email'],
        org_tagline=b['org_tagline'] or None,
    )


def get_appointment_cancellation_email(
    appointment,
    user,
    *,
    cancellation_reason=None,
    cancelled_by='member',
    organization_name=None,
    base_url=None,
    contact_email=None,
    org_tagline=None,
):
    """Correo al miembro cuando se cancela una cita."""
    b = _merge_branding(organization_name, base_url, contact_email, org_tagline)
    bu = b['base_url']
    org_esc, svc_esc = _appointment_org_service_lines_html(appointment, b['organization_name'])
    ref = html_module.escape(str(getattr(appointment, 'reference', None) or 'N/A'))
    reason = html_module.escape(str(cancellation_reason or '').strip() or '—')
    _cb = str(cancelled_by or '').lower()
    by_msg = (
        'Has cancelado esta cita.'
        if _cb in ('member', 'user', 'miembro')
        else 'Un administrador ha cancelado esta cita.'
    )
    fecha_txt = ''
    if getattr(appointment, 'start_datetime', None):
        fecha_txt = appointment.start_datetime.strftime('%d/%m/%Y %H:%M')
    fecha_esc = html_module.escape(fecha_txt or 'Por definir')
    content = f"""
        <h2>Cita cancelada</h2>
        <p>Hola <strong>{html_module.escape(str(user.first_name))} {html_module.escape(str(user.last_name))}</strong>,</p>
        <p>{by_msg}</p>
        <div class="info-box">
            <h3 style="margin-top: 0;">Detalles</h3>
            <ul>
                <li><strong>Organización:</strong> {org_esc}</li>
                <li><strong>Servicio:</strong> {svc_esc}</li>
                <li><strong>Referencia:</strong> {ref}</li>
                <li><strong>Fecha prevista:</strong> {fecha_esc}</li>
                <li><strong>Motivo / nota:</strong> {reason}</li>
            </ul>
        </div>
        <p style="text-align: center;">
            <a href="{html_module.escape(bu)}/appointments" class="button">Ver citas</a>
        </p>
    """
    return get_email_template_base(
        f"Cancelación de cita - {b['organization_name']}",
        content,
        year=datetime.now().year,
        organization_name=b['organization_name'],
        base_url=b['base_url'],
        contact_email=b['contact_email'],
        org_tagline=b['org_tagline'] or None,
    )


def get_appointment_created_email(appointment, user, advisor, service, *, organization_name=None, base_url=None, contact_email=None, org_tagline=None):
    """Template para email al cliente cuando se crea la cita después del pago"""
    b = _merge_branding(organization_name, base_url, contact_email, org_tagline)
    bu = b['base_url']
    advisor_name = f"{advisor.first_name} {advisor.last_name}" if advisor else "Asesor asignado"
    if appointment.appointment_type is not None and hasattr(appointment.appointment_type, 'public_service_label'):
        service_name = appointment.appointment_type.public_service_label()
    elif service:
        service_name = service.name
    elif appointment.appointment_type:
        service_name = appointment.appointment_type.name
    else:
        service_name = "Servicio"
    start_date = appointment.start_datetime.strftime('%d/%m/%Y') if appointment.start_datetime else "Fecha pendiente"
    start_time = appointment.start_datetime.strftime('%H:%M') if appointment.start_datetime else "Hora pendiente"
    advisor_name_e = html_module.escape(advisor_name)
    service_name_e = html_module.escape(str(service_name))
    org_esc, _ = _appointment_org_service_lines_html(appointment, b['organization_name'])
    ref = html_module.escape(str(appointment.reference if hasattr(appointment, 'reference') and appointment.reference else 'N/A'))
    content = f"""
        <h2>Cita Agendada Exitosamente</h2>
        <p>Hola <strong>{html_module.escape(str(user.first_name))} {html_module.escape(str(user.last_name))}</strong>,</p>
        <p>Tu cita ha sido agendada exitosamente después del pago. La cita está <strong>pendiente de confirmación</strong> por parte del asesor.</p>
        
        <div class="info-box">
            <h3 style="margin-top: 0;">Detalles de la Cita:</h3>
            <ul>
                <li><strong>Organización:</strong> {org_esc}</li>
                <li><strong>Servicio:</strong> {service_name_e}</li>
                <li><strong>Asesor:</strong> {advisor_name_e}</li>
                <li><strong>Fecha:</strong> {start_date}</li>
                <li><strong>Hora:</strong> {start_time}</li>
                <li><strong>Estado:</strong> Pendiente de confirmación</li>
                <li><strong>Referencia:</strong> {ref}</li>
            </ul>
        </div>
        
        <p><strong>Nota importante:</strong> Recibirás una notificación cuando el asesor confirme tu cita. Mientras tanto, puedes revisar el estado en tu panel.</p>
        
        <p style="text-align: center;">
            <a href="{html_module.escape(bu)}/appointments" class="button">Ver Mis Citas</a>
        </p>
    """
    return get_email_template_base(
        f"Cita Agendada - {b['organization_name']}",
        content,
        year=datetime.now().year,
        organization_name=b['organization_name'],
        base_url=b['base_url'],
        contact_email=b['contact_email'],
        org_tagline=b['org_tagline'] or None,
    )


def get_appointment_new_advisor_email(appointment, user, advisor, service, *, organization_name=None, base_url=None, contact_email=None, org_tagline=None):
    """Template para email al asesor sobre nueva cita pendiente de confirmación"""
    b = _merge_branding(organization_name, base_url, contact_email, org_tagline)
    bu = b['base_url']
    service_name = service.name if service else appointment.appointment_type.name if appointment.appointment_type else "Servicio"
    start_date = appointment.start_datetime.strftime('%d/%m/%Y') if appointment.start_datetime else "Fecha pendiente"
    start_time = appointment.start_datetime.strftime('%H:%M') if appointment.start_datetime else "Hora pendiente"
    case_description = appointment.user_notes if hasattr(appointment, 'user_notes') and appointment.user_notes else "Sin descripción adicional"
    case_short = html_module.escape(case_description[:200] + ('...' if len(case_description) > 200 else ''))
    ref = html_module.escape(str(appointment.reference if hasattr(appointment, 'reference') and appointment.reference else 'N/A'))
    content = f"""
        <h2>Nueva Cita Pendiente de Confirmación</h2>
        <p>Hola <strong>{html_module.escape(str(advisor.first_name))} {html_module.escape(str(advisor.last_name))}</strong>,</p>
        <p>Has recibido una nueva solicitud de cita que requiere tu confirmación.</p>
        
        <div class="info-box">
            <h3 style="margin-top: 0;">Detalles de la Cita:</h3>
            <ul>
                <li><strong>Cliente:</strong> {html_module.escape(str(user.first_name))} {html_module.escape(str(user.last_name))} ({html_module.escape(str(user.email))})</li>
                <li><strong>Servicio:</strong> {html_module.escape(str(service_name))}</li>
                <li><strong>Fecha:</strong> {start_date}</li>
                <li><strong>Hora:</strong> {start_time}</li>
                <li><strong>Descripción del caso:</strong> {case_short}</li>
                <li><strong>Referencia:</strong> {ref}</li>
            </ul>
        </div>
        
        <p><strong>Acción requerida:</strong> Por favor, confirma o cancela esta cita desde tu panel de administración.</p>
        
        <p style="text-align: center;">
            <a href="{html_module.escape(bu)}/admin/appointments" class="button">Gestionar Citas</a>
        </p>
    """
    return get_email_template_base(
        f"Nueva Cita Pendiente de Confirmación - {b['organization_name']}",
        content,
        year=datetime.now().year,
        organization_name=b['organization_name'],
        base_url=b['base_url'],
        contact_email=b['contact_email'],
        org_tagline=b['org_tagline'] or None,
    )


def get_appointment_new_admin_email(appointment, user, advisor, service, admin, *, organization_name=None, base_url=None, contact_email=None, org_tagline=None):
    """Template para email a administradores sobre nueva cita creada"""
    b = _merge_branding(organization_name, base_url, contact_email, org_tagline)
    bu = b['base_url']
    advisor_name = f"{advisor.first_name} {advisor.last_name}" if advisor else "No asignado"
    service_name = service.name if service else appointment.appointment_type.name if appointment.appointment_type else "Servicio"
    start_date = appointment.start_datetime.strftime('%d/%m/%Y') if appointment.start_datetime else "Fecha pendiente"
    start_time = appointment.start_datetime.strftime('%H:%M') if appointment.start_datetime else "Hora pendiente"
    ref = html_module.escape(str(appointment.reference if hasattr(appointment, 'reference') and appointment.reference else 'N/A'))
    content = f"""
        <h2>Nueva Cita Creada en el Sistema</h2>
        <p>Hola <strong>{html_module.escape(str(admin.first_name))} {html_module.escape(str(admin.last_name))}</strong>,</p>
        <p>Se ha creado una nueva cita en el sistema después de un pago exitoso.</p>
        
        <div class="info-box">
            <h3 style="margin-top: 0;">Detalles de la Cita:</h3>
            <ul>
                <li><strong>Cliente:</strong> {html_module.escape(str(user.first_name))} {html_module.escape(str(user.last_name))} ({html_module.escape(str(user.email))})</li>
                <li><strong>Servicio:</strong> {html_module.escape(str(service_name))}</li>
                <li><strong>Asesor:</strong> {html_module.escape(advisor_name)}</li>
                <li><strong>Fecha:</strong> {start_date}</li>
                <li><strong>Hora:</strong> {start_time}</li>
                <li><strong>Estado:</strong> Pendiente de confirmación</li>
                <li><strong>Referencia:</strong> {ref}</li>
                <li><strong>Pago:</strong> Completado</li>
            </ul>
        </div>
        
        <p>Esta cita está pendiente de confirmación por parte del asesor asignado.</p>
        
        <p style="text-align: center;">
            <a href="{html_module.escape(bu)}/admin/appointments" class="button">Ver Todas las Citas</a>
        </p>
    """
    return get_email_template_base(
        f"Nueva Cita Creada - {b['organization_name']}",
        content,
        year=datetime.now().year,
        organization_name=b['organization_name'],
        base_url=b['base_url'],
        contact_email=b['contact_email'],
        org_tagline=b['org_tagline'] or None,
    )


def get_welcome_email(user, *, organization_name=None, base_url=None, contact_email=None, org_tagline=None):
    """Template para email de bienvenida usando el nuevo template HTML"""
    try:
        from app import app, resolve_email_logo_absolute_url
        import os
        from flask import has_request_context, request
        
        oid = int(getattr(user, 'organization_id', None) or 1)
        b = _merge_branding(organization_name, base_url, contact_email, org_tagline)
        logo_url = resolve_email_logo_absolute_url(
            organization_id=oid, allow_fallback_to_platform_logo=True
        )
        if base_url is not None:
            base_url_resolved = str(base_url).rstrip('/')
        elif has_request_context() and request:
            base_url_resolved = request.url_root.rstrip('/')
        else:
            base_url_resolved = b['base_url']
        
        login_url = f"{base_url_resolved}/login"
        oname = b['organization_name']
        cmail = b['contact_email']
        
        # Renderizar el nuevo template HTML - usar app_context si no hay request context
        if has_request_context():
            html = render_template('emails/sistema/bienvenida.html',
                                  logo_url=logo_url,
                                  user_first_name=user.first_name,
                                  user_last_name=user.last_name,
                                  login_url=login_url,
                                  base_url=base_url_resolved,
                                  year=datetime.now().year,
                                  contact_email=cmail,
                                  organization_name=oname)
        else:
            # Si no hay request context, usar app_context
            with app.app_context():
                html = render_template('emails/sistema/bienvenida.html',
                                      logo_url=logo_url,
                                      user_first_name=user.first_name,
                                      user_last_name=user.last_name,
                                      login_url=login_url,
                                      base_url=base_url_resolved,
                                      year=datetime.now().year,
                                      contact_email=cmail,
                                      organization_name=oname)
        
        return html
    except Exception as e:
        # Fallback al template anterior si hay error
        import traceback
        traceback.print_exc()
        print(f"⚠️ Error al cargar template de bienvenida: {e}")
        fb = _merge_branding(organization_name, base_url, contact_email, org_tagline)
        bu, on = fb['base_url'], html_module.escape(fb['organization_name'])
        content = f"""
            <h2>¡Bienvenido!</h2>
            <p>Hola <strong>{html_module.escape(str(user.first_name))} {html_module.escape(str(user.last_name))}</strong>,</p>
            <p>Te damos la bienvenida a {on}.</p>
            
            <div class="info-box">
                <h3 style="margin-top: 0;">¿Qué puedes hacer ahora?</h3>
                <ul>
                    <li>Explorar nuestros eventos y cursos</li>
                    <li>Acceder a recursos exclusivos</li>
                    <li>Conectar con otros investigadores</li>
                    <li>Gestionar tu membresía</li>
                </ul>
            </div>
            
            <p>Estamos aquí para apoyarte.</p>
            <p style="text-align: center;">
                <a href="{html_module.escape(fb['base_url'])}/login" class="button">Ir a mi Dashboard</a>
            </p>
        """
        return get_email_template_base(
            f"Bienvenido a {fb['organization_name']}",
            content,
            year=datetime.now().year,
            organization_name=fb['organization_name'],
            base_url=fb['base_url'],
            contact_email=fb['contact_email'],
            org_tagline=fb['org_tagline'] or None,
        )


def get_password_reset_email(user, reset_token, reset_url, *, organization_name=None, base_url=None, contact_email=None, org_tagline=None):
    """Template para restablecimiento de contraseña"""
    b = _merge_branding(organization_name, base_url, contact_email, org_tagline)
    ru = html_module.escape(str(reset_url))
    content = f"""
        <h2>Restablecer Contraseña</h2>
        <p>Hola <strong>{html_module.escape(str(user.first_name))} {html_module.escape(str(user.last_name))}</strong>,</p>
        <p>Has solicitado restablecer tu contraseña. Haz clic en el botón siguiente para continuar:</p>
        
        <p style="text-align: center;">
            <a href="{ru}" class="button">Restablecer Contraseña</a>
        </p>
        
        <p>Si no solicitaste este cambio, puedes ignorar este correo. El enlace expirará en 1 hora.</p>
        
        <p><small>O copia y pega este enlace en tu navegador:</small><br>
        <small style="color: #666; word-break: break-all;">{ru}</small></p>
    """
    return get_email_template_base(
        f"Restablecer Contraseña - {b['organization_name']}",
        content,
        year=datetime.now().year,
        organization_name=b['organization_name'],
        base_url=b['base_url'],
        contact_email=b['contact_email'],
        org_tagline=b['org_tagline'] or None,
    )


def get_email_verification_email(user, verification_url, *, organization_name=None, base_url=None, contact_email=None, org_tagline=None):
    """Template para verificación de email usando el nuevo template HTML"""
    try:
        from app import app, resolve_email_logo_absolute_url
        import os
        from flask import has_request_context, request
        
        oid = int(getattr(user, 'organization_id', None) or 1)
        b = _merge_branding(organization_name, base_url, contact_email, org_tagline)
        logo_url = resolve_email_logo_absolute_url(
            organization_id=oid, allow_fallback_to_platform_logo=True
        )
        if base_url is not None:
            base_url_resolved = str(base_url).rstrip('/')
        elif has_request_context() and request:
            base_url_resolved = request.url_root.rstrip('/')
        else:
            base_url_resolved = b['base_url']
        oname = b['organization_name']
        cmail = b['contact_email']
        
        # Renderizar el template HTML
        if has_request_context():
            html = render_template('emails/sistema/verificacion_email.html',
                                  logo_url=logo_url,
                                  user_first_name=user.first_name,
                                  user_last_name=user.last_name,
                                  verification_url=verification_url,
                                  year=datetime.now().year,
                                  contact_email=cmail,
                                  organization_name=oname)
        else:
            with app.app_context():
                html = render_template('emails/sistema/verificacion_email.html',
                                      logo_url=logo_url,
                                      user_first_name=user.first_name,
                                      user_last_name=user.last_name,
                                      verification_url=verification_url,
                                      year=datetime.now().year,
                                      contact_email=cmail,
                                      organization_name=oname)
        
        return html
    except Exception as e:
        # Fallback al template anterior si hay error
        import traceback
        traceback.print_exc()
        fb = _merge_branding(organization_name, base_url, contact_email, org_tagline)
        vu = html_module.escape(str(verification_url))
        on = html_module.escape(fb['organization_name'])
        content = f"""
            <h2>Verifica tu Correo Electrónico</h2>
            <p>Hola <strong>{html_module.escape(str(user.first_name))} {html_module.escape(str(user.last_name))}</strong>,</p>
            <p>Gracias por registrarte en {on}. Para completar tu registro, verifica tu email haciendo clic en el siguiente enlace:</p>
            <p style="text-align: center;">
                <a href="{vu}" class="button">Verificar mi Email</a>
            </p>
            <p>Este enlace expirará en 24 horas.</p>
            <p><small>O copia y pega este enlace en tu navegador:</small><br>
            <small style="color: #666; word-break: break-all;">{vu}</small></p>
        """
        return get_email_template_base(
            f"Verifica tu Email - {fb['organization_name']}",
            content,
            year=datetime.now().year,
            organization_name=fb['organization_name'],
            base_url=fb['base_url'],
            contact_email=fb['contact_email'],
            org_tagline=fb['org_tagline'] or None,
        )


def get_office365_request_email(user_name, email, purpose, description, request_id, *, organization_name=None, base_url=None, contact_email=None, org_tagline=None):
    """Template por defecto para notificación de solicitud de correo Office 365.
    Variables: user_name, email, purpose, description, request_id.
    """
    b = _merge_branding(organization_name, base_url, contact_email, org_tagline)
    content = f"""
        <h2>Solicitud de correo electrónico Office 365</h2>
        <p><strong>Usuario solicitante:</strong> {html_module.escape(str(user_name))}</p>
        <p><strong>Email solicitado:</strong> {html_module.escape(str(email))}</p>
        <p><strong>Motivo:</strong> {html_module.escape(str(purpose))}</p>
        <p><strong>Descripción:</strong></p>
        <p>{html_module.escape(str(description)).replace(chr(10), '<br>')}</p>
        <p><em>ID solicitud: {html_module.escape(str(request_id))}. Revisar en panel de administración.</em></p>
    """
    return get_email_template_base(
        f"Nueva solicitud Office 365 – {b['organization_name']}",
        content,
        year=datetime.now().year,
        organization_name=b['organization_name'],
        base_url=b['base_url'],
        contact_email=b['contact_email'],
        org_tagline=b['org_tagline'] or None,
    )


def get_crm_activity_assigned_email(
    lead_name,
    activity_summary,
    activity_type,
    due_text,
    crm_url,
    *,
    organization_name=None,
    base_url=None,
    contact_email=None,
    org_tagline=None,
):
    """Fallback HTML para plantilla crm_activity_assigned (variables: lead_name, activity_summary, …)."""
    b = _merge_branding(organization_name, base_url, contact_email, org_tagline)
    ln = html_module.escape(str(lead_name or ''))
    su = html_module.escape(str(activity_summary or ''))
    tp = html_module.escape(str(activity_type or ''))
    dt = html_module.escape(str(due_text or ''))
    cu = html_module.escape(str(crm_url or ''))
    content = f"""
        <h2>Nueva actividad asignada</h2>
        <p><strong>Lead:</strong> {ln}</p>
        <p><strong>Actividad:</strong> {su}</p>
        <p><strong>Tipo:</strong> {tp}</p>
        <p><strong>Vence:</strong> {dt}</p>
        <p><a href="{cu}" class="button">Abrir CRM</a></p>
    """
    return get_email_template_base(
        f"[CRM] Nueva actividad asignada – {b['organization_name']}",
        content,
        year=datetime.now().year,
        organization_name=b['organization_name'],
        base_url=b['base_url'],
        contact_email=b['contact_email'],
        org_tagline=b['org_tagline'] or None,
    )


def get_crm_activity_reminder_email(
    lead_name,
    activity_summary,
    activity_type,
    due_text,
    alert_label,
    crm_url,
    *,
    organization_name=None,
    base_url=None,
    contact_email=None,
    org_tagline=None,
):
    """Fallback HTML para plantilla crm_activity_reminder (alertas vencidas / hoy / 24h)."""
    b = _merge_branding(organization_name, base_url, contact_email, org_tagline)
    ln = html_module.escape(str(lead_name or ''))
    su = html_module.escape(str(activity_summary or ''))
    tp = html_module.escape(str(activity_type or ''))
    dt = html_module.escape(str(due_text or ''))
    al = html_module.escape(str(alert_label or ''))
    cu = html_module.escape(str(crm_url or ''))
    content = f"""
        <h2>{al}</h2>
        <p><strong>Lead:</strong> {ln}</p>
        <p><strong>Actividad:</strong> {su}</p>
        <p><strong>Tipo:</strong> {tp}</p>
        <p><strong>Vencimiento:</strong> {dt}</p>
        <p><a href="{cu}" class="button">Abrir CRM</a></p>
    """
    return get_email_template_base(
        f"[CRM] {alert_label} – {b['organization_name']}",
        content,
        year=datetime.now().year,
        organization_name=b['organization_name'],
        base_url=b['base_url'],
        contact_email=b['contact_email'],
        org_tagline=b['org_tagline'] or None,
    )

