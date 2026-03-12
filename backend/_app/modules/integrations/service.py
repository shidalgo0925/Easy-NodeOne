# Lógica de integraciones (Office365 solicitudes usuario).
import re
import html as html_module

from app import (
    app,
    db,
    DiscountCode,
    User,
    Notification,
    EmailTemplate,
)
from . import repository

try:
    from email_templates import get_office365_request_email
except ImportError:
    get_office365_request_email = None

OFFICE365_PRO_OR_ABOVE = ('admin', 'pro', 'premium', 'deluxe', 'corporativo')


def user_has_pro_or_above(user):
    m = user.get_active_membership()
    if not m or not getattr(m, 'is_currently_active', lambda: False)():
        return False
    mt = (getattr(m, 'membership_type', '') or '').strip().lower()
    return mt in OFFICE365_PRO_OR_ABOVE


def get_page_data(user):
    membership = user.get_active_membership()
    is_pro_or_above = user_has_pro_or_above(user)
    # Política de uso de correo: si debe aceptar y datos para mostrar
    try:
        from _app.modules.policies import service as policies_svc
        policy_correo = policies_svc.get_policy_for_display(policies_svc.SLUG_POLITICA_CORREO, active_only=True)
        must_accept = policies_svc.user_must_accept_email_policy(user)
        checkbox_text = policies_svc.CHECKBOX_POLITICA_CORREO
    except Exception:
        policy_correo = None
        must_accept = False
        checkbox_text = ''
    return {
        'membership': membership,
        'is_pro_or_above': is_pro_or_above,
        'policy_correo': policy_correo,
        'must_accept_email_policy': must_accept,
        'checkbox_politica_correo': checkbox_text,
    }


def submit_request(user, data, request=None):
    """
    Valida, crea solicitud Office365, envía correos.
    Requiere aceptación de política de correo si aplica.
    Retorna (response_dict, None) o (None, (error_msg, status_code)).
    """
    email = (data.get('email') or '').strip()
    purpose = (data.get('purpose') or '').strip()
    description = (data.get('description') or '').strip()
    authorization_code = (data.get('authorization_code') or data.get('code') or '').strip()
    policy_accepted = data.get('policy_accepted') in (True, 'true', '1', 1)

    # Aceptación obligatoria de política de uso de correo
    try:
        from _app.modules.policies import service as policies_svc
        if policies_svc.user_must_accept_email_policy(user):
            if not policy_accepted:
                return None, ({'success': False, 'error': 'Debes aceptar la Política de Uso del Correo Institucional para continuar.', 'require_policy_acceptance': True}, 400)
            ok, err = policies_svc.record_email_policy_acceptance(user, request)
            if not ok:
                return None, ({'success': False, 'error': err or 'Error al registrar la aceptación.'}, 400)
    except Exception:
        pass

    if not email:
        return None, ({'success': False, 'error': 'El correo es obligatorio.'}, 400)
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        return None, ({'success': False, 'error': 'Formato de correo no válido.'}, 400)
    if not purpose:
        return None, ({'success': False, 'error': 'El propósito es obligatorio.'}, 400)
    if len(description) < 10:
        return None, ({'success': False, 'error': 'La descripción debe tener al menos 10 caracteres.'}, 400)

    discount_code_id = None
    if user_has_pro_or_above(user):
        pass
    else:
        if not authorization_code:
            return None, ({
                'success': False,
                'error': 'Necesitas una membresía Pro o superior, o un código de autorización válido para solicitar correo.',
                'code_required': True,
            }, 403)
        dc = DiscountCode.query.filter(DiscountCode.code == authorization_code.strip().upper()).first()
        if not dc:
            return None, ({'success': False, 'error': 'Código de autorización no encontrado o incorrecto.'}, 400)
        if not getattr(dc, 'valid_for_office365', False):
            return None, ({'success': False, 'error': 'Este código no es válido para solicitud de correo Office 365.'}, 400)
        ok, msg = dc.can_use(user.id)
        if not ok:
            status = 409 if ('límite de usos' in msg or 'máximo' in msg) else 400
            return None, ({'success': False, 'error': msg}, status)
        discount_code_id = dc.id

    purpose_max = purpose[:255]
    description_safe = description[:2000]
    user_name = f'{getattr(user, "first_name", "") or ""} {getattr(user, "last_name", "") or ""}'.strip() or user.email

    try:
        req = repository.create_office365_request(
            user.id, email, purpose_max, description_safe, discount_code_id
        )
    except Exception:
        db.session.rollback()
        app.logger.exception('Office365Request create failed')
        return None, ({'success': False, 'error': 'Error al registrar la solicitud.'}, 500)

    admin_emails = repository.get_admin_emails()
    recipients = list(admin_emails)
    if email not in recipients:
        recipients.append(email)

    sub = {
        'user_name': html_module.escape(user_name),
        'email': html_module.escape(email),
        'purpose': html_module.escape(purpose_max),
        'description': html_module.escape(description_safe).replace(chr(10), '<br>'),
        'request_id': req.id,
    }
    t = EmailTemplate.query.filter_by(template_key='office365_request').first()
    if t:
        subject = t.subject.replace('{user_name}', sub['user_name']).replace('{email}', sub['email']).replace('{purpose}', sub['purpose']).replace('{description}', sub['description']).replace('{request_id}', str(req.id))
        if t.is_custom and t.html_content:
            body_html = t.html_content
            for k, v in sub.items():
                body_html = body_html.replace('{' + k + '}', str(v))
        else:
            body_html = get_office365_request_email(user_name, email, purpose_max, description_safe, req.id) if get_office365_request_email else f'<p>Solicitud #{req.id}</p>'
    else:
        subject = f'Nueva solicitud Office 365 – {email}'
        body_html = get_office365_request_email(user_name, email, purpose_max, description_safe, req.id) if get_office365_request_email else f'<p>Solicitud #{req.id}</p>'

    try:
        from flask_mail import Mail, Message
        mail_obj = app.extensions.get('mail')
    except ImportError:
        mail_obj = None
        Message = None
    if admin_emails and mail_obj and Message:
        try:
            msg = Message(subject=subject, recipients=recipients, html=body_html)
            mail_obj.send(msg)
        except Exception as e:
            app.logger.exception('Office365 email send failed')
            err_msg = str(e)[:500]
            for admin in User.query.filter_by(is_admin=True).all():
                try:
                    n = Notification(
                        user_id=admin.id,
                        notification_type='email_error',
                        title='Error al enviar correo (solicitud Office 365)',
                        message=f'Solicitud #{req.id}. No se pudo enviar el correo a los admins. Error: {err_msg}',
                    )
                    db.session.add(n)
                except Exception:
                    pass
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
    elif not admin_emails:
        app.logger.error('Office365 request id=%s: no hay admins con email configurado', req.id)

    if request:
        app.logger.info('Office365 request id=%s user_id=%s email=%s ip=%s', req.id, user.id, email, getattr(request, 'remote_addr', ''))

    resp = {
        'success': True,
        'message': 'Solicitud enviada. Recibirás una respuesta en 2-3 días hábiles.',
        'request_id': req.id,
    }
    if not admin_emails:
        resp['warning'] = 'Solicitud registrada pero no hay destinatarios configurados; contacta al soporte.'
    return resp, None
