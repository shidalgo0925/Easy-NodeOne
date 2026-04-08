"""API admin: configuración SMTP, diagnóstico, prueba, plantillas y logo de correo."""

import os
from datetime import datetime, timedelta

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from functools import wraps

admin_email_bp = Blueprint('admin_email', __name__)

# Desde nodeone/modules/admin_email_api/ → raíz del repo /static/... (4 niveles: módulos → nodeone → backend → repo)
_EMAIL_LOGO_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'static', 'public', 'emails', 'logos')
)


def _admin_required_lazy(f):
    """Igual que app.admin_required; importa app en request (evita ciclo)."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        import app as M

        if bool(getattr(current_user, 'must_change_password', False)):
            flash('Debes cambiar tu contraseña antes de continuar.', 'warning')
            return redirect(url_for('auth.change_password'))
        if not current_user.is_admin and not M._user_has_any_admin_permission(current_user):
            flash('No tienes permisos para acceder a esta página.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)

    return decorated_function


@admin_email_bp.route('/api/admin/email/config', methods=['GET', 'POST', 'PUT'])
@_admin_required_lazy
def api_email_config():
    """API para obtener y actualizar configuración SMTP"""
    import app as M
    coid = M._catalog_org_for_admin_catalog_routes()
    if request.method == 'GET':
        config = M.EmailConfig.get_active_config(
            organization_id=coid, allow_fallback_to_default_org=False
        )
        if config:
            return jsonify({'success': True, 'config': config.to_dict()})
        else:
            return jsonify({'success': False, 'message': 'No hay configuración activa'})
    
    elif request.method in ['POST', 'PUT']:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No se recibieron datos. Revisa que el formulario envíe JSON.'}), 400
        server = (data.get('mail_server') or '').strip()
        if 'brevo' in server.lower() or 'resend' in server.lower():
            data['use_environment_variables'] = False
        # Desactivar configuraciones activas previas del mismo tenant
        M.EmailConfig.query.filter_by(organization_id=coid).update({'is_active': False})
        
        # Buscar si existe una configuración en este tenant (reutilizar primera fila si hay varias)
        config = M.EmailConfig.query.filter_by(organization_id=coid).order_by(M.EmailConfig.id).first()
        
        if not config:
            # Crear nueva configuración
            config = M.EmailConfig(
                organization_id=coid,
                mail_server=data.get('mail_server', 'smtp.gmail.com'),
                mail_port=int(data.get('mail_port', 587)),
                mail_use_tls=bool(data.get('mail_use_tls', True)),
                mail_use_ssl=bool(data.get('mail_use_ssl', False)),
                mail_username=data.get('mail_username', ''),
                mail_password=data.get('mail_password', ''),
                mail_default_sender=data.get('mail_default_sender', 'noreply@relaticpanama.org'),
                use_environment_variables=bool(data.get('use_environment_variables', True)),
                is_active=True
            )
            M.db.session.add(config)
        else:
            # Actualizar configuración existente
            config.mail_server = data.get('mail_server', config.mail_server)
            config.mail_port = int(data.get('mail_port', config.mail_port))
            config.mail_use_tls = bool(data.get('mail_use_tls', config.mail_use_tls))
            config.mail_use_ssl = bool(data.get('mail_use_ssl', config.mail_use_ssl))
            config.mail_username = data.get('mail_username', config.mail_username)
            if 'mail_password' in data and data['mail_password']:
                config.mail_password = data.get('mail_password')
            config.mail_default_sender = data.get('mail_default_sender', config.mail_default_sender)
            config.use_environment_variables = bool(data.get('use_environment_variables', config.use_environment_variables))
            config.is_active = True
            config.updated_at = datetime.utcnow()
        
        try:
            M.db.session.commit()
            
            # Aplicar nueva configuración
            config.apply_to_app(M.app)
            M.mail = M.Mail(M.app)
            if getattr(M, 'EmailService', None) and M.mail:
                M.email_service = M.EmailService(M.mail)
            
            return jsonify({
                'success': True,
                'message': 'Configuración de email actualizada exitosamente',
                'config': config.to_dict()
            })
        except Exception as e:
            M.db.session.rollback()
            M.app.logger.exception('Email config save failed')
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

@admin_email_bp.route('/api/admin/email/diagnostic', methods=['GET'])
@_admin_required_lazy
def api_email_diagnostic():
    """Estado actual de la configuración de email (sin exponer contraseñas) para diagnosticar por qué no llegan correos."""
    import app as M
    try:
        _coid = M._catalog_org_for_admin_catalog_routes()
        config = M.EmailConfig.get_active_config(
            organization_id=_coid, allow_fallback_to_default_org=False
        )
        if not config:
            return jsonify({
                'has_config': False,
                'message': 'No hay configuración de email activa. Guarda el formulario de esta página con servidor, usuario y contraseña.',
                'username_configured': False,
                'password_configured': False,
            })
        use_env = bool(config.use_environment_variables)
        if use_env:
            username_configured = bool(os.getenv('MAIL_USERNAME') or (config.mail_username or '').strip())
            password_configured = bool(os.getenv('MAIL_PASSWORD') or (config.mail_password or '').strip())
        else:
            username_configured = bool((config.mail_username or '').strip())
            password_configured = bool((config.mail_password or '').strip())
        issues = []
        if not config.mail_server:
            issues.append('Falta servidor SMTP')
        if not config.mail_port or config.mail_port <= 0:
            issues.append('Puerto no configurado')
        if not username_configured:
            issues.append('Usuario/email SMTP no configurado' + (' (ni en BD ni en variable MAIL_USERNAME)' if use_env else ''))
        if not password_configured:
            issues.append('Contraseña SMTP no configurada' + (' (ni en BD ni en variable MAIL_PASSWORD)' if use_env else ''))
        if not (config.mail_default_sender or '').strip() or '@' not in (config.mail_default_sender or ''):
            issues.append('Remitente por defecto inválido o vacío')
        message = 'Configuración OK; puedes enviar correo de prueba.' if not issues else '; '.join(issues)
        return jsonify({
            'has_config': True,
            'is_active': config.is_active,
            'use_environment_variables': use_env,
            'server': config.mail_server or '',
            'port': config.mail_port or 0,
            'sender': (config.mail_default_sender or '').strip(),
            'username_configured': username_configured,
            'password_configured': password_configured,
            'issues': issues,
            'message': message,
        })
    except Exception as e:
        M.app.logger.exception('Email diagnostic failed')
        return jsonify({'has_config': False, 'message': str(e), 'username_configured': False, 'password_configured': False}), 500

@admin_email_bp.route('/api/admin/email/test', methods=['POST'])
@_admin_required_lazy
def api_email_test():
    """API para probar la configuración de email enviando un correo de prueba"""
    import app as M
    try:
        data = request.get_json(silent=True) or {}
        test_email = (data.get('email') or (current_user.email if current_user.is_authenticated else '')).strip()
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    
    # Validar email de destino
    if not test_email or '@' not in test_email:
        return jsonify({
            'success': False,
            'error': 'Email de destino inválido'
        }), 400
    
    # Solo probar SMTP del tenant del catálogo (no el de Default en pantalla de otro tenant)
    _coid_test = M._catalog_org_for_admin_catalog_routes()
    email_config = M.EmailConfig.get_active_config(
        organization_id=_coid_test, allow_fallback_to_default_org=False
    )
    if not email_config:
        return jsonify({
            'success': False,
            'error': 'No hay configuración de email activa para esta organización. Configura SMTP en /admin/email.',
            'details': 'Si es un tenant nuevo, crea su propia configuración (no se usa la de Default en el panel).',
        }), 400
    
    # Validar campos requeridos
    validation_errors = []
    
    if not email_config.mail_server:
        validation_errors.append('Servidor SMTP no configurado')
    elif email_config.mail_server not in ['smtp.gmail.com', 'smtp.office365.com', 'smtp-mail.outlook.com']:
        # Permitir otros servidores pero advertir
        pass
    
    if not email_config.mail_port or email_config.mail_port <= 0:
        validation_errors.append('Puerto SMTP no configurado o inválido')
    
    if not email_config.mail_username:
        validation_errors.append('Usuario/Email SMTP no configurado')
    elif '@' not in email_config.mail_username:
        # Resend y otros usan usuario "resend" sin @
        if not email_config.mail_server or 'resend' not in email_config.mail_server.lower():
            validation_errors.append('Usuario SMTP no parece ser un email válido')
    
    if not email_config.mail_password:
        validation_errors.append('Contraseña SMTP no configurada')
    elif len(email_config.mail_password) < 8:
        # Resend usa API key larga (re_...); Gmail 16
        if not email_config.mail_server or 'resend' not in email_config.mail_server.lower():
            validation_errors.append('Contraseña SMTP muy corta (mínimo 8 caracteres)')
    
    if not email_config.mail_default_sender:
        validation_errors.append('Remitente por defecto no configurado')
    elif '@' not in email_config.mail_default_sender:
        validation_errors.append('Remitente por defecto no parece ser un email válido')
    
    # Verificar configuración específica según el servidor
    if email_config.mail_server == 'smtp.gmail.com':
        # Solo advertir si la contraseña es muy corta, pero no bloquear
        if len(email_config.mail_password) < 8:
            validation_errors.append('Contraseña SMTP muy corta (mínimo 8 caracteres)')
        elif len(email_config.mail_password) != 16:
            # Advertencia informativa pero no bloquea - permite intentar
            pass  # No agregar error, solo permitir intentar
        if not email_config.mail_use_tls:
            validation_errors.append('Gmail requiere TLS habilitado')
    
    if email_config.mail_server == 'smtp.office365.com':
        if not email_config.mail_use_tls:
            validation_errors.append('Office 365 requiere TLS habilitado')
        if email_config.mail_port not in [587, 25]:
            validation_errors.append('Office 365 requiere puerto 587 (recomendado) o 25')
    
    # Si hay errores de validación, retornarlos
    if validation_errors:
        return jsonify({
            'success': False,
            'error': 'Configuración de email incompleta o incorrecta',
            'details': validation_errors,
            'config_summary': {
                'server': email_config.mail_server or '(no configurado)',
                'port': email_config.mail_port or '(no configurado)',
                'username': email_config.mail_username or '(no configurado)',
                'tls': email_config.mail_use_tls,
                'sender': email_config.mail_default_sender or '(no configurado)',
                'has_password': bool(email_config.mail_password),
                'password_length': len(email_config.mail_password) if email_config.mail_password else 0
            }
        }), 400
    
    # Brevo: el remitente no debe ser el login SMTP
    if email_config.mail_server and 'brevo' in email_config.mail_server.lower():
        if (email_config.mail_default_sender or '').strip().lower() == (email_config.mail_username or '').strip().lower():
            return jsonify({
                'success': False,
                'error': 'Con Brevo, el "Remitente por defecto" debe ser un email verificado en tu cuenta Brevo, no el usuario SMTP.',
                'details': [
                    'En Brevo: Remitentes y dominios → crea/verifica un remitente (ej: noreply@tudominio.com).',
                    'Usa ese email en "Remitente por defecto" y el usuario SMTP solo para autenticación.'
                ]
            }), 400
        email_config.use_environment_variables = False
    # Resend: usar siempre config de la BD
    if email_config.mail_server and 'resend' in email_config.mail_server.lower():
        email_config.use_environment_variables = False
    
    oid_smtp = int(getattr(email_config, 'organization_id', None) or M.default_organization_id())
    M.app.logger.info(
        'Test email: server=%s port=%s ssl=%s tls=%s sender=%s to=%s org=%s',
        email_config.mail_server, email_config.mail_port, email_config.mail_use_ssl, email_config.mail_use_tls,
        email_config.mail_default_sender, test_email, oid_smtp,
    )
    M.app.config['MAIL_TIMEOUT'] = 25

    try:
        ok_smtp, _ = M.apply_transactional_smtp_for_organization(oid_smtp)
        if not ok_smtp or not M.mail:
            return jsonify({
                'success': False,
                'error': 'No se pudo aplicar SMTP transaccional para esta organización. Revisa EmailConfig activo.',
            }), 500
        from flask_mail import Message

        msg = Message(
            subject='[Prueba] Configuración de Email - RelaticPanama',
            recipients=[test_email],
            sender=email_config.mail_default_sender,
            html=f"""
            <h2>Correo de Prueba</h2>
            <p>Este es un correo de prueba para verificar que la configuración SMTP está funcionando correctamente.</p>
            <p>Si recibes este correo, significa que la configuración es correcta.</p>
            <p><strong>Remitente:</strong> {email_config.mail_default_sender}</p>
            <p><strong>Servidor:</strong> {email_config.mail_server}</p>
            <p><strong>Fecha:</strong> {datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')}</p>
            <p>Saludos,<br>Equipo RelaticPanama</p>
            """
        )
        M.mail.send(msg)
        M.app.logger.info('Test email sent OK to %s', test_email)
        
        message = f'Correo de prueba enviado exitosamente a {test_email}.'
        if email_config.mail_server and 'brevo' in email_config.mail_server.lower():
            message += ' Si no lo ves, revisa carpeta de spam y que el remitente esté verificado en Brevo.'
        if email_config.mail_server and 'resend' in email_config.mail_server.lower():
            message += ' Si no llega, revisa spam y que el dominio del remitente esté verificado en Resend.'
        return jsonify({
            'success': True,
            'message': message,
            'config_used': {
                'server': email_config.mail_server,
                'sender': email_config.mail_default_sender
            }
        })
    except Exception as e:
        error_msg = str(e)
        error_details = []
        M.app.logger.exception('Test email send failed: %s', error_msg)
        
        # Brevo: errores frecuentes
        if email_config.mail_server and 'brevo' in email_config.mail_server.lower():
            if '535' in error_msg or 'auth' in error_msg.lower() or 'credential' in error_msg.lower():
                error_details.append('Usa la clave SMTP de Brevo (no la API key). En Brevo: Configuración → SMTP y API → Clave SMTP.')
            if 'sender' in error_msg.lower() or 'invalid' in error_msg.lower() or '550' in error_msg:
                error_details.append('El remitente debe estar verificado en Brevo (Remitentes y dominios). No uses el usuario SMTP como remitente.')
            if '450' in error_msg or 'not yet activated' in error_msg.lower():
                error_details.append('Correos transaccionales pueden no estar activados. Contacta a Brevo o activa en tu cuenta.')
        if email_config.mail_server and 'resend' in email_config.mail_server.lower():
            if '535' in error_msg or 'auth' in error_msg.lower() or 'credential' in error_msg.lower():
                error_details.append('Resend: usa la API key como contraseña SMTP. Usuario debe ser "resend". Puerto 465 con SSL.')
            if 'timeout' in error_msg.lower() or 'timed out' in error_msg.lower() or 'connection' in error_msg.lower():
                error_details.append('Conexión lenta o bloqueada. Prueba con Puerto 587, TLS marcado y SSL desmarcado (Resend soporta ambos).')
            if 'sender' in error_msg.lower() or 'domain' in error_msg.lower() or 'verified' in error_msg.lower():
                error_details.append('El remitente (From) debe usar un dominio verificado en Resend (Dashboard → Domains).')
        
        # Analizar el error y dar recomendaciones específicas
        if 'application-specific password' in error_msg.lower() or '5.7.9' in error_msg or 'invalidsecondfactor' in error_msg.lower():
            error_details.append('⚠️ Gmail requiere una CONTRASEÑA DE APLICACIÓN (16 caracteres)')
            error_details.append('La contraseña normal de Gmail NO funciona para SMTP')
            error_details.append('')
            error_details.append('SOLUCIÓN: Generar contraseña de aplicación')
            error_details.append('')
            error_details.append('Pasos:')
            error_details.append('1. Ve a: https://myaccount.google.com/apppasswords')
            error_details.append('2. Inicia sesión con relaticpanama2025@gmail.com')
            error_details.append('3. Si no tienes 2FA, actívalo primero (requerido)')
            error_details.append('4. Selecciona:')
            error_details.append('   - App: "Correo"')
            error_details.append('   - Device: "Otro (nombre personalizado)"')
            error_details.append('   - Escribe: "RelaticPanama"')
            error_details.append('5. Haz clic en "Generar"')
            error_details.append('6. Copia la contraseña de 16 caracteres (sin espacios)')
            error_details.append('7. Actualiza la contraseña en /admin/email')
            error_details.append('')
            error_details.append('O visita: https://support.google.com/mail/?p=InvalidSecondFactor')
        elif 'smtp_auth_disabled' in error_msg.lower() or '5.7.139' in error_msg or 'smtpclientauthentication is disabled' in error_msg.lower():
            error_details.append('⚠️ SMTP AUTH está DESHABILITADO en tu tenant de Office 365')
            error_details.append('')
            error_details.append('SOLUCIÓN: Habilitar SMTP AUTH en Microsoft 365 Admin Center')
            error_details.append('')
            error_details.append('Pasos:')
            error_details.append('1. Ve a https://admin.microsoft.com')
            error_details.append('2. Configuración → Correo → Autenticación')
            error_details.append('3. Busca "Autenticación SMTP básica"')
            error_details.append('4. Habilita SMTP AUTH para el usuario info@relaticpanama.org')
            error_details.append('')
            error_details.append('O visita: https://aka.ms/smtp_auth_disabled')
            error_details.append('')
            error_details.append('Nota: Si no tienes permisos de administrador, contacta al administrador de Microsoft 365')
        elif '535' in error_msg or 'badcredentials' in error_msg.lower() or ('authentication' in error_msg.lower() and 'credentials' in error_msg.lower()):
            error_details.append('❌ Error de autenticación: Usuario o contraseña incorrectos')
            if email_config.mail_server == 'smtp.gmail.com':
                error_details.append('')
                error_details.append('Para Gmail, verifica:')
                error_details.append('1. El usuario es correcto: ' + (email_config.mail_username or 'no configurado'))
                error_details.append('2. La contraseña es una contraseña de aplicación de 16 caracteres (sin espacios)')
                error_details.append('3. La contraseña de aplicación no fue revocada')
                error_details.append('')
                error_details.append('Si la contraseña tiene espacios, quítalos')
                error_details.append('Ejemplo: "abcd efgh ijkl mnop" → "abcdefghijklmnop"')
                error_details.append('')
                error_details.append('Para generar una nueva contraseña de aplicación:')
                error_details.append('https://myaccount.google.com/apppasswords')
        elif '535' in error_msg or 'authentication' in error_msg.lower():
            error_details.append('Error de autenticación: Usuario o contraseña incorrectos')
            if email_config.mail_server == 'smtp.gmail.com':
                error_details.append('Para Gmail, asegúrate de usar una contraseña de aplicación (16 caracteres)')
                error_details.append('Genera una en: https://myaccount.google.com/apppasswords')
            elif email_config.mail_server == 'smtp.office365.com':
                error_details.append('Para Office 365, verifica que la contraseña sea correcta')
                error_details.append('Si tienes MFA activado, puede que necesites una contraseña de aplicación')
        elif 'connection' in error_msg.lower() or 'timeout' in error_msg.lower():
            error_details.append('Error de conexión: No se pudo conectar al servidor SMTP')
            error_details.append(f'Verifica que el puerto {email_config.mail_port} esté abierto')
        elif 'tls' in error_msg.lower() or 'ssl' in error_msg.lower():
            error_details.append('Error de seguridad: Problema con TLS/SSL')
            error_details.append('Verifica que TLS esté habilitado para este servidor')
        elif '550' in error_msg or 'sending limit' in error_msg.lower() or 'daily' in error_msg.lower():
            error_details.append('Límite diario de envío alcanzado (Gmail/Google).')
            error_details.append('Espera a que se reinicie el límite o usa otro servidor SMTP.')
        
        # Notificación in-app para que el admin vea el error
        try:
            n = M.Notification(
                user_id=current_user.id,
                notification_type='email_error',
                title='Error al enviar correo de prueba',
                message=error_msg[:400] + ('…' if len(error_msg) > 400 else ''),
            )
            M.db.session.add(n)
            M.db.session.commit()
        except Exception:
            M.db.session.rollback()
        
        # Mensaje específico para SMTP AUTH deshabilitado
        if 'smtp_auth_disabled' in error_msg.lower() or '5.7.139' in error_msg:
            error_details.insert(0, '⚠️ SMTP AUTH está deshabilitado en tu tenant de Office 365')
            error_details.append('Solución: Habilitar SMTP AUTH en el centro de administración de Microsoft 365')
            error_details.append('Pasos:')
            error_details.append('1. Ve a https://admin.microsoft.com')
            error_details.append('2. Configuración → Correo → Autenticación')
            error_details.append('3. Habilita "Autenticación SMTP básica" para el usuario info@relaticpanama.org')
            error_details.append('O visita: https://aka.ms/smtp_auth_disabled')
        
        return jsonify({
            'success': False,
            'error': f'Error al enviar correo de prueba: {error_msg}',
            'details': error_details if error_details else ['Revisa la configuración SMTP en /admin/email']
        }), 500
    finally:
        M.apply_email_config_from_db()

@admin_email_bp.route('/api/admin/email/test-welcome', methods=['POST'])
@_admin_required_lazy
def api_email_test_welcome():
    """API para probar el template de bienvenida"""
    import app as M
    data = request.get_json()
    test_email = data.get('email', current_user.email)
    
    try:
        # Crear usuario de prueba
        class MockUser:
            def __init__(self, email, organization_id=1):
                self.id = 1
                self.organization_id = int(organization_id)
                self.first_name = "Juan"
                self.last_name = "Pérez"
                self.email = email
        
        user = MockUser(test_email, M._catalog_org_for_admin_catalog_routes())
        html_content, subj_mail = M.render_welcome_email_for_org(
            user, user.organization_id, strict_tenant_logo=False
        )
        oid = int(user.organization_id)
        try:
            ok_smtp, _ = M.apply_transactional_smtp_for_organization(oid)
            if not ok_smtp or not M.email_service:
                return jsonify({
                    'success': False,
                    'error': 'SMTP transaccional no disponible para esta organización.',
                }), 500
            M.email_service.send_email(
                subject=f'[Prueba] {subj_mail}',
                recipients=[test_email],
                html_content=html_content,
                email_type='welcome_test',
                recipient_name='Juan Pérez',
            )
            return jsonify({
                'success': True,
                'message': f'Email de bienvenida de prueba enviado exitosamente a {test_email}',
            })
        finally:
            M.apply_email_config_from_db()
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error al enviar email de prueba: {str(e)}'
        }), 500

@admin_email_bp.route('/api/admin/email/preview/<template_key>', methods=['GET'])
@_admin_required_lazy
def api_email_preview_template(template_key):
    """API para previsualizar cualquier template de email sin enviarlo"""
    import app as M
    try:
        preview_org = M._catalog_org_for_admin_catalog_routes()
        # Crear datos de prueba según el tipo de template
        class MockUser:
            def __init__(self, organization_id=1):
                self.id = 1
                self.organization_id = int(organization_id)
                self.first_name = "Juan"
                self.last_name = "Pérez"
                self.email = "juan.perez@example.com"
        
        class MockPayment:
            def __init__(self):
                self.membership_type = "pro"
                self.amount = 6000  # centavos (como Payment.amount en BD)
                self.created_at = datetime.utcnow()
        
        class MockSubscription:
            def __init__(self):
                self.membership_type = "pro"
                self.start_date = datetime.utcnow()
                self.end_date = datetime.utcnow() + timedelta(days=365)
        
        class MockEvent:
            def __init__(self):
                self.title = "Congreso de Investigación Cualitativa 2025"
                self.start_date = datetime.utcnow() + timedelta(days=30)
                self.end_date = datetime.utcnow() + timedelta(days=31)
                self.start_time = "09:00"
                self.id = 1
                self.currency = "USD"
                self.slug = "congreso-investigacion-2025"
        
        class MockRegistration:
            def __init__(self):
                self.registration_status = "confirmed"
                self.final_price = 50.00
        
        class MockAppointment:
            def __init__(self, org_id=1):
                class _MockAT:
                    name = 'Asesoría en Revisión de Artículos'
                    organization_id = int(org_id)

                    def public_service_label(self):
                        return self.name

                self.id = 999001
                self.organization_id = int(org_id)
                self.appointment_type_id = 1
                self.reference = 'DEMO-REF'
                self.appointment_type = _MockAT()
                self.start_datetime = datetime.utcnow() + timedelta(days=7)
                self.duration_minutes = 60
                self.is_virtual = True
                self.meeting_url = "https://meet.google.com/abc-defg-hij"
                self.notes = "Preparar preguntas sobre metodología"
        
        class MockAdvisor:
            def __init__(self):
                self.first_name = "María"
                self.last_name = "González"
                self.specializations = "Investigación cualitativa, revisión de artículos"
        
        user = MockUser(preview_org)
        preview_logo_url = M.resolve_email_logo_absolute_url(
            organization_id=preview_org, allow_fallback_to_platform_logo=False
        )
        
        # Generar HTML según el template_key
        if template_key == 'welcome':
            html_content, _pw = M.render_welcome_email_for_org(user, preview_org, strict_tenant_logo=True)
        elif template_key == 'membership_payment':
            payment = MockPayment()
            subscription = MockSubscription()
            html_content, _preview_subj = M.render_membership_payment_email_for_org(
                user, payment, subscription, preview_org, strict_tenant_logo=True
            )
        elif template_key == 'membership_expiring':
            subscription = MockSubscription()
            html_content, _pw = M.render_membership_expiring_email_for_org(
                user, subscription, 7, preview_org, strict_tenant_logo=True
            )
        elif template_key == 'membership_expired':
            subscription = MockSubscription()
            html_content, _pw = M.render_membership_expired_email_for_org(
                user, subscription, preview_org, strict_tenant_logo=True
            )
        elif template_key == 'membership_renewed':
            subscription = MockSubscription()
            html_content, _pw = M.render_membership_renewed_email_for_org(
                user, subscription, preview_org, strict_tenant_logo=True
            )
        elif template_key == 'event_registration':
            event = MockEvent()
            registration = MockRegistration()
            try:
                # Intentar usar el template HTML nuevo primero
                from flask import render_template
                
                base_url = request.url_root.rstrip('/') if request else 'https://miembros.relatic.org'
                logo_url = preview_logo_url
                
                html_content = render_template('emails/eventos/registro_evento.html',
                                              logo_url=logo_url,
                                              user_first_name=user.first_name,
                                              user_last_name=user.last_name,
                                              event_title=event.title,
                                              event_category="Congreso",
                                              event_start_date=event.start_date.strftime('%d de %B de %Y'),
                                              event_end_date=event.end_date.strftime('%d de %B de %Y'),
                                              event_format="Virtual",
                                              event_location=None,
                                              event_price=registration.final_price,
                                              event_currency=event.currency,
                                              event_description="Congreso internacional de investigación cualitativa",
                                              event_registration_url=None,
                                              event_detail_url=f"{base_url}/events/{event.slug}",
                                              event_has_certificate=True,
                                              discount_applied=False,
                                              base_url=base_url,
                                              year=datetime.now().year,
                                              contact_email='administracion@relaticpanama.org')
            except Exception as e:
                # Fallback al template antiguo si el nuevo falla
                html_content = M.get_event_registration_email(
                    event, user, registration, **M._email_branding_from_organization_id(preview_org)
                )
        elif template_key == 'event_cancellation':
            event = MockEvent()
            html_content, _pw = M.render_event_cancellation_email_for_org(
                event, user, preview_org, strict_tenant_logo=True
            )
        elif template_key == 'event_update':
            event = MockEvent()
            html_content, _pw = M.render_event_update_email_for_org(
                event, user, ["Fecha actualizada", "Nueva ubicación"], preview_org, strict_tenant_logo=True
            )
        elif template_key == 'appointment_confirmation':
            appointment = MockAppointment(preview_org)
            advisor = MockAdvisor()
            try:
                # Usar el template HTML nuevo
                from flask import render_template
                
                base_url = request.url_root.rstrip('/') if request else 'https://miembros.relatic.org'
                logo_url = preview_logo_url
                
                html_content = render_template('emails/eventos/confirmacion_cita.html',
                                              logo_url=logo_url,
                                              user_first_name=user.first_name,
                                              user_last_name=user.last_name,
                                              appointment_type=appointment.appointment_type.name,
                                              appointment_date=appointment.start_datetime.strftime('%d de %B de %Y'),
                                              appointment_time=appointment.start_datetime.strftime('%H:%M'),
                                              appointment_duration=appointment.duration_minutes,
                                              appointment_format='Virtual' if appointment.is_virtual else 'Presencial',
                                              advisor_name=f"{advisor.first_name} {advisor.last_name}",
                                              advisor_specialization=advisor.specializations,
                                              meeting_url=appointment.meeting_url,
                                              appointment_notes=appointment.notes,
                                              appointments_url=f"{base_url}/appointments",
                                              base_url=base_url,
                                              year=datetime.now().year,
                                              contact_email='administracion@relaticpanama.org')
            except Exception as e:
                # Fallback al template antiguo si el nuevo falla
                html_content = M.get_appointment_confirmation_email(
                    appointment, user, advisor, **M._email_branding_from_organization_id(preview_org)
                )
        elif template_key == 'appointment_reminder':
            appointment = MockAppointment(preview_org)
            advisor = MockAdvisor()
            try:
                # Usar el template HTML nuevo
                from flask import render_template
                
                base_url = request.url_root.rstrip('/') if request else 'https://miembros.relatic.org'
                logo_url = preview_logo_url
                
                html_content = render_template('emails/eventos/recordatorio_cita.html',
                                              logo_url=logo_url,
                                              user_first_name=user.first_name,
                                              user_last_name=user.last_name,
                                              appointment_type=appointment.appointment_type.name,
                                              appointment_date=appointment.start_datetime.strftime('%d de %B de %Y'),
                                              appointment_time=appointment.start_datetime.strftime('%H:%M'),
                                              appointment_duration=appointment.duration_minutes,
                                              appointment_format='Virtual' if appointment.is_virtual else 'Presencial',
                                              advisor_name=f"{advisor.first_name} {advisor.last_name}",
                                              advisor_specialization=advisor.specializations,
                                              meeting_url=appointment.meeting_url,
                                              appointment_notes=appointment.notes,
                                              hours_until=24,
                                              appointments_url=f"{base_url}/appointments",
                                              base_url=base_url,
                                              year=datetime.now().year,
                                              contact_email='administracion@relaticpanama.org')
            except Exception as e:
                # Fallback al template antiguo si el nuevo falla
                html_content = M.get_appointment_reminder_email(
                    appointment, user, advisor, 24, **M._email_branding_from_organization_id(preview_org)
                )
        elif template_key == 'appointment_cancellation':
            appointment = MockAppointment(preview_org)
            advisor = MockAdvisor()
            _ab = M._email_branding_from_organization_id(preview_org)
            html_content, _subj = M.render_appointment_communication_email(
                'appointment_cancellation',
                appointment,
                user,
                {'cancellation_reason': 'Ejemplo de motivo de cancelación', 'cancelled_by': 'member', 'advisor': advisor},
                lambda: M.get_appointment_cancellation_email(
                    appointment,
                    user,
                    cancellation_reason='Ejemplo de motivo de cancelación',
                    cancelled_by='member',
                    **_ab,
                ),
                f'Cancelación de cita - {_ab["organization_name"]}',
                strict_tenant_logo=True,
            )
        elif template_key == 'password_reset':
            reset_token = "abc123xyz"
            reset_url = f"{request.url_root.rstrip('/')}/reset-password?token={reset_token}"
            html_content, _pw = M.render_password_reset_email_for_org(
                user, reset_token, reset_url, preview_org, strict_tenant_logo=True
            )
        elif template_key == 'office365_request':
            html_content, _pw = M.render_office365_request_email_for_org(
                user_name=f"{user.first_name} {user.last_name}",
                email=user.email,
                purpose="Trabajo profesional / comunicación institucional",
                description="Solicito correo corporativo para uso en proyectos y contacto con miembros.",
                request_id=999,
                organization_id=preview_org,
                strict_tenant_logo=True,
            )
        elif template_key == 'crm_activity_assigned':
            from email_templates import _default_base_url, get_crm_activity_assigned_email
            from nodeone.services.crm_email import (
                build_crm_activity_assigned_email,
                crm_email_context_assigned_plain_esc,
            )

            crm_url = f"{_default_base_url().rstrip('/')}/admin/crm"
            lead_name_demo = 'Oportunidad Demo'
            summary_demo = 'Llamada de seguimiento'
            due_demo = '2026-01-15 10:00 UTC'
            _br = M._email_branding_from_organization_id(preview_org)
            plain, esc = crm_email_context_assigned_plain_esc(
                lead_name=lead_name_demo,
                activity_summary=summary_demo,
                activity_type='call',
                due_text=due_demo,
                crm_url=crm_url,
                assignee_name=f"{user.first_name} {user.last_name}",
            )
            default_html = get_crm_activity_assigned_email(
                lead_name_demo,
                summary_demo,
                'call',
                due_demo,
                crm_url,
                **_br,
            )
            html_content, _, _ = build_crm_activity_assigned_email(
                int(preview_org),
                plain,
                esc,
                default_subject=f"[CRM] Nueva actividad asignada: {summary_demo}",
                default_html=default_html,
                default_text=(
                    f"Nueva actividad asignada | Lead: {lead_name_demo} | Actividad: {summary_demo} | Vence: {due_demo}"
                ),
            )
        elif template_key == 'crm_activity_reminder':
            from email_templates import _default_base_url, get_crm_activity_reminder_email
            from nodeone.services.crm_email import (
                build_crm_activity_reminder_email,
                crm_email_context_reminder_plain_esc,
            )

            crm_url = f"{_default_base_url().rstrip('/')}/admin/crm"
            lead_name_demo = 'Oportunidad Demo'
            summary_demo = 'Revisión de propuesta'
            due_demo = '2026-01-15 18:00 UTC'
            alert_label = 'Actividad vence hoy'
            alert_kind = 'due_today'
            _br = M._email_branding_from_organization_id(preview_org)
            plain, esc = crm_email_context_reminder_plain_esc(
                lead_name=lead_name_demo,
                activity_summary=summary_demo,
                activity_type='task',
                due_text=due_demo,
                alert_label=alert_label,
                alert_kind=alert_kind,
                crm_url=crm_url,
                assignee_name=f"{user.first_name} {user.last_name}",
            )
            default_html = get_crm_activity_reminder_email(
                lead_name_demo,
                summary_demo,
                'task',
                due_demo,
                alert_label,
                crm_url,
                **_br,
            )
            html_content, _, _ = build_crm_activity_reminder_email(
                int(preview_org),
                plain,
                esc,
                default_subject=f"[CRM] {alert_label}: {summary_demo}",
                default_html=default_html,
                default_text=f"{alert_label} | Lead: {lead_name_demo} | Actividad: {summary_demo} | Vence: {due_demo}",
            )
        else:
            return jsonify({
                'success': False,
                'error': f'Template "{template_key}" no encontrado'
            }), 404
        
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error al generar preview: {str(e)}'
        }), 500

# Mantener ruta antigua para compatibilidad
@admin_email_bp.route('/api/admin/email/preview-welcome', methods=['GET'])
@_admin_required_lazy
def api_email_preview_welcome():
    """API para previsualizar el template de bienvenida sin enviarlo (compatibilidad)"""
    import app as M
    return api_email_preview_template('welcome')

@admin_email_bp.route('/api/admin/email/upload-logo', methods=['POST'])
@_admin_required_lazy
def api_upload_logo():
    """API para subir el logo para emails (por tenant si catálogo multi-org está activo)."""
    import app as M
    try:
        from werkzeug.utils import secure_filename
        
        if 'logo_file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No se proporcionó archivo'
            }), 400
        
        file = request.files['logo_file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No se seleccionó ningún archivo'
            }), 400
        
        if not M.allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Formato de archivo no permitido. Use PNG, JPG o SVG'
            }), 400
        
        # Verificar tamaño (máximo 500KB)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 500 * 1024:  # 500KB
            return jsonify({
                'success': False,
                'error': 'El archivo es demasiado grande. Máximo 500KB'
            }), 400
        
        # Crear directorio si no existe
        logo_dir = _EMAIL_LOGO_DIR
        os.makedirs(logo_dir, exist_ok=True)
        coid = M._catalog_org_for_admin_catalog_routes()
        # Siempre por tenant: no pisar logo-relatic / plataforma
        base_fn = f'logo-email-org{int(coid)}'
        
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if ext == 'svg':
            logo_path = os.path.join(logo_dir, f'{base_fn}.svg')
            file.save(logo_path)
            logo_url = url_for('static', filename=f'public/emails/logos/{base_fn}.svg')
            rel_stored = f'public/emails/logos/{base_fn}.svg'
        else:
            logo_path = os.path.join(logo_dir, f'{base_fn}.png')
            file.save(logo_path)
            logo_url = url_for('static', filename=f'public/emails/logos/{base_fn}.png')
            rel_stored = f'public/emails/logos/{base_fn}.png'

        try:
            s = M.OrganizationSettings.query.filter_by(organization_id=int(coid)).first()
            if s is None:
                s = M.OrganizationSettings(organization_id=int(coid))
                M.db.session.add(s)
            s.logo_url = rel_stored
            M.db.session.commit()
        except Exception as e:
            M.db.session.rollback()
            print(f"⚠️ Logo guardado en disco pero no organization_settings.logo_url: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Logo subido para esta organización (correos HTML).',
            'logo_url': logo_url,
            'organization_id': int(coid),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error al subir logo: {str(e)}'
        }), 500

@admin_email_bp.route('/api/admin/email/delete-logo', methods=['POST'])
@_admin_required_lazy
def api_delete_logo():
    """API para eliminar el logo de correo del tenant actual (o global si monotenant)."""
    import app as M
    try:
        logo_dir = _EMAIL_LOGO_DIR
        coid = M._catalog_org_for_admin_catalog_routes()
        deleted = False
        for ext in ('png', 'svg'):
            p = os.path.join(logo_dir, f'logo-email-org{int(coid)}.{ext}')
            if os.path.exists(p):
                os.remove(p)
                deleted = True
        try:
            s = M.OrganizationSettings.query.filter_by(organization_id=int(coid)).first()
            if s is not None:
                s.logo_url = ''
                M.db.session.commit()
        except Exception as e:
            M.db.session.rollback()
            print(f"⚠️ delete-logo: no se pudo limpiar organization_settings.logo_url: {e}")
        
        if deleted:
            return jsonify({
                'success': True,
                'message': 'Logo eliminado exitosamente'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No se encontró logo para eliminar'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error al eliminar logo: {str(e)}'
        }), 500

@admin_email_bp.route('/api/admin/email/logo-status', methods=['GET'])
@_admin_required_lazy
def api_logo_status():
    """API para verificar si existe el logo de correo del tenant del catálogo admin (sin mezclar Default)."""
    import app as M
    try:
        coid = M._catalog_org_for_admin_catalog_routes()
        logo_url = M.resolve_email_logo_absolute_url(
            organization_id=coid, allow_fallback_to_platform_logo=False
        )
        logo_exists = bool(logo_url)
        return jsonify({
            'success': True,
            'logo_exists': logo_exists,
            'logo_url': logo_url,
            'organization_id': int(coid),
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error al verificar logo: {str(e)}'
        }), 500

@admin_email_bp.route('/api/admin/email/templates')
@_admin_required_lazy
def api_email_templates():
    """API para obtener todos los templates de correo"""
    import app as M
    coid_tpl = M._catalog_org_for_admin_catalog_routes()
    if coid_tpl is None:
        return jsonify({'success': True, 'templates': []})
    templates = M.EmailTemplate.query.filter_by(organization_id=int(coid_tpl)).order_by(
        M.EmailTemplate.category, M.EmailTemplate.name
    ).all()
    return jsonify({
        'success': True,
        'templates': [t.to_dict() for t in templates]
    })


@admin_email_bp.route('/api/admin/email/templates/clone-from-default', methods=['POST'])
@_admin_required_lazy
def api_email_templates_clone_from_default():
    """
    Copia plantillas de correo desde la org base (id=1) u otra origen al tenant del contexto admin actual.
    Sin overwrite: solo crea las que falten. Con overwrite: actualiza las existentes con el HTML/asunto del origen.
    """
    _raw_coid = M._catalog_org_for_admin_catalog_routes()
    if _raw_coid is None:
        return jsonify({'success': False, 'error': 'Sin organización activa en sesión'}), 400
    coid = int(_raw_coid)
    data = request.get_json(silent=True) or {}
    overwrite = bool(data.get('overwrite'))
    source = int(data.get('source_organization_id', 1) or 1)
    if not M._admin_can_view_all_organizations():
        source = 1
    if source < 1 or M.SaasOrganization.query.get(source) is None:
        return jsonify({'success': False, 'error': 'Organización origen no válida'}), 400
    if coid == source:
        return jsonify({'success': False, 'error': 'Origen y destino no pueden ser la misma organización'}), 400
    if M.SaasOrganization.query.get(coid) is None:
        return jsonify({'success': False, 'error': 'Organización destino no válida'}), 400
    if not M._admin_can_view_all_organizations():
        cur = M.get_current_organization_id()
        if cur is None or int(cur) != coid:
            abort(403)
    try:
        created, updated, skipped = M.clone_email_templates_from_org(source, coid, overwrite=overwrite)
        return jsonify({
            'success': True,
            'message': 'Plantillas clonadas',
            'created': created,
            'updated': updated,
            'skipped': skipped,
            'organization_id': coid,
            'source_organization_id': source,
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        M.db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_email_bp.route('/api/admin/email/templates/<int:template_id>', methods=['GET', 'PUT'])
@_admin_required_lazy
def api_email_template(template_id):
    """API para obtener y actualizar un template de correo"""
    import app as M
    coid_tpl = M._catalog_org_for_admin_catalog_routes()
    template = M.EmailTemplate.query.get_or_404(template_id)
    if int(template.organization_id or 1) != int(coid_tpl):
        abort(404)
    
    if request.method == 'GET':
        return jsonify({'success': True, 'template': template.to_dict()})
    
    elif request.method == 'PUT':
        data = request.get_json()
        
        template.subject = data.get('subject', template.subject)
        template.html_content = data.get('html_content', template.html_content)
        template.text_content = data.get('text_content', template.text_content)
        template.is_custom = bool(data.get('is_custom', template.is_custom))
        template.updated_at = datetime.utcnow()
        
        try:
            M.db.session.commit()
            return jsonify({
                'success': True,
                'message': f'Template "{template.name}" actualizado exitosamente',
                'template': template.to_dict()
            })
        except Exception as e:
            M.db.session.rollback()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

@admin_email_bp.route('/api/admin/email/templates/<int:template_id>/reset', methods=['POST'])
@_admin_required_lazy
def api_email_template_reset(template_id):
    """API para resetear un template a su versión por defecto"""
    import app as M
    coid_tpl = M._catalog_org_for_admin_catalog_routes()
    template = M.EmailTemplate.query.get_or_404(template_id)
    if int(template.organization_id or 1) != int(coid_tpl):
        abort(404)
    
    # Cargar template por defecto desde email_templates.py
    try:
        if M.EMAIL_TEMPLATES_AVAILABLE:
            # Importar función de template
            template_func_map = {
                'welcome': M.get_welcome_email,
                'membership_payment': M.get_membership_payment_confirmation_email,
                'membership_expiring': M.get_membership_expiring_email,
                'membership_expired': M.get_membership_expired_email,
                'membership_renewed': M.get_membership_renewed_email,
                'event_registration': M.get_event_registration_email,
                'event_cancellation': M.get_event_cancellation_email,
                'event_update': M.get_event_update_email,
                'appointment_confirmation': M.get_appointment_confirmation_email,
                'appointment_reminder': M.get_appointment_reminder_email,
                'appointment_cancellation': M.get_appointment_cancellation_email,
                'office365_request': M.get_office365_request_email,
                'crm_activity_assigned': M.get_crm_activity_assigned_email,
                'crm_activity_reminder': M.get_crm_activity_reminder_email,
            }
            
            if template.template_key in template_func_map:
                # Nota: Esto requiere pasar objetos mock, por ahora solo marcamos como no custom
                template.is_custom = False
                template.updated_at = datetime.utcnow()
                M.db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': f'Template "{template.name}" reseteado a versión por defecto'
                })
        
        return jsonify({
            'success': False,
            'error': 'No se pudo resetear el template'
        }), 400
    except Exception as e:
        M.db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
