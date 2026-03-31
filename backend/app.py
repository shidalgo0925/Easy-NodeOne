#!/usr/bin/env python3
"""
Easy NodeOne - Backend Flask para gestión modular
"""

import sys
import re
import html as html_module
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, has_request_context, send_file, abort, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime, timedelta
import os
import secrets
from functools import wraps
from sqlalchemy import text as sql_text

# Sistema de licencias (módulo independiente)
try:
    sys.path.insert(0, '/home/relaticpanama2025/.shh/license-system')
    from license_validator import LicenseValidator
    LICENSE_VALIDATOR = LicenseValidator('nodeone')
except Exception as e:
    LICENSE_VALIDATOR = None
    print(f"⚠️ Error inicializando sistema de licencias: {e}")
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    stripe = None
    STRIPE_AVAILABLE = False
    print("⚠️ Stripe no está instalado. Funcionalidad de pagos no disponible.")

try:
    from flask_mail import Mail, Message
    FLASK_MAIL_AVAILABLE = True
except ImportError:
    Mail = None
    Message = None
    FLASK_MAIL_AVAILABLE = False
    print("⚠️ flask_mail no está instalado. Funcionalidad de email no disponible.")

try:
    from email_service import EmailService
    from email_templates import (
        get_membership_payment_confirmation_email,
        get_membership_expiring_email,
        get_membership_expired_email,
        get_membership_renewed_email,
        get_event_registration_email,
        get_event_cancellation_email,
        get_event_update_email,
        get_appointment_confirmation_email,
        get_appointment_reminder_email,
        get_appointment_created_email,
        get_appointment_new_advisor_email,
        get_appointment_new_admin_email,
        get_welcome_email,
        get_password_reset_email,
        get_email_verification_email,
        get_office365_request_email,
    )
    EMAIL_TEMPLATES_AVAILABLE = True
except ImportError as e:
    EMAIL_TEMPLATES_AVAILABLE = False
    EmailService = None
    print("⚠️ Email templates no disponibles. Usando templates básicos.")

# Importar procesadores de pago
try:
    from payment_processors import get_payment_processor, PAYMENT_METHODS
    PAYMENT_PROCESSORS_AVAILABLE = True
except ImportError:
    PAYMENT_PROCESSORS_AVAILABLE = False
    print("⚠️ Payment processors no disponibles.")
    PAYMENT_METHODS = {}

# OAuth (login social)
try:
    from authlib.integrations.flask_client import OAuth
    OAUTH_AVAILABLE = True
except ImportError:
    OAuth = None
    OAUTH_AVAILABLE = False
    print("⚠️ Authlib no instalado. Login social no disponible.")

# Configuración de la aplicación
app = Flask(__name__, template_folder='../templates', static_folder='../static')
# Detrás de Nginx/Cloudflare: confiar en X-Forwarded-Proto y X-Forwarded-For
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_for=1)
# Branding unificado (GLOBAL = misma marca en topbar; TENANT = nombre de org activa en sesión)
app.config['APP_BRAND_NAME'] = (os.environ.get('APP_BRAND_NAME') or 'Easy NodeOne').strip() or 'Easy NodeOne'
_brand_mode = (os.environ.get('BRAND_MODE') or 'GLOBAL').strip().upper()
app.config['BRAND_MODE'] = _brand_mode if _brand_mode in ('GLOBAL', 'TENANT') else 'GLOBAL'

# Ensure module alias 'app' points to this instance even when running as __main__
sys.modules.setdefault('app', sys.modules[__name__])
# SECRET_KEY estable: si cambia en cada arranque, la cookie de sesión deja de valer → login en cada clic.
basedir = os.path.abspath(os.path.dirname(__file__))
_instance_dir = os.path.join(os.path.dirname(basedir), 'instance')
os.makedirs(_instance_dir, exist_ok=True)


def _load_or_create_secret_key():
    sk = (os.environ.get('SECRET_KEY') or '').strip()
    if sk:
        return sk
    key_path = os.path.join(_instance_dir, '.flask_secret_key')
    if os.path.isfile(key_path):
        try:
            with open(key_path, 'r', encoding='utf-8') as f:
                s = f.read().strip()
                if s:
                    return s
        except OSError:
            pass
    k = secrets.token_hex(32)
    try:
        with open(key_path, 'w', encoding='utf-8') as f:
            f.write(k)
        try:
            os.chmod(key_path, 0o600)
        except OSError:
            pass
    except OSError:
        pass
    return k


app.config['SECRET_KEY'] = _load_or_create_secret_key()
db_path = os.path.join(_instance_dir, 'nodeone.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuración de Stripe
if stripe:
    stripe.api_key = os.getenv('STRIPE_SECRET_KEY', 'sk_test_your_stripe_secret_key_here')
    STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', 'pk_test_your_stripe_publishable_key_here')
else:
    STRIPE_PUBLISHABLE_KEY = None

# Configuración de Mail (valores por defecto, se pueden sobrescribir desde BD)
# Configurado para Microsoft Office 365 por defecto
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.office365.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', '587'))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@relaticpanama.org')

# Inicialización de extensiones
from nodeone.core.db import db
db.init_app(app)

from models import *  # noqa: F403 — ORM (compat from app import Model)


# Logger: excepciones a archivo (para ver 500 en producción)
import logging
_logpath = os.path.join(os.path.dirname(basedir), 'instance', 'app_errors.log')
os.makedirs(os.path.dirname(_logpath), exist_ok=True)
_file_handler = logging.FileHandler(_logpath, encoding='utf-8')
_file_handler.setLevel(logging.ERROR)
_file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
app.logger.addHandler(_file_handler)


login_manager = LoginManager()
login_manager.init_app(app)
mail = Mail(app) if Mail else None

# Aplicar configuración de email desde BD si existe (después de crear las tablas)
def apply_email_config_from_db():
    """Aplicar configuración de email desde la base de datos"""
    global mail, email_service
    try:
        # EmailConfig ya está definido arriba, no necesita import
        email_config = EmailConfig.get_active_config()
        if email_config:
            email_config.apply_to_app(app)
            # Reinicializar Mail con nueva configuración (solo si Mail está disponible)
            if Mail:
                mail = Mail()
                mail.init_app(app)
            else:
                mail = None
            if EMAIL_TEMPLATES_AVAILABLE:
                email_service = EmailService(mail)
            print("✅ Configuración de email cargada desde base de datos")
        else:
            # Si no hay configuración en BD, usar variables de entorno o valores por defecto
            print("⚠️ No hay configuración de email en BD, usando variables de entorno")
            # Asegurar que mail esté inicializado (solo si Mail está disponible)
            if not mail and Mail:
                mail = Mail(app)
                mail.init_app(app)
            if EMAIL_TEMPLATES_AVAILABLE and mail:
                if not email_service:
                    email_service = EmailService(mail)
    except Exception as e:
        print(f"⚠️ No se pudo cargar configuración de email desde BD: {e}")
        print("   Usando configuración por defecto o variables de entorno")
        import traceback
        traceback.print_exc()
        # Asegurar que mail esté inicializado incluso si falla (solo si Mail está disponible)
        if not mail and Mail:
            mail = Mail(app)
            mail.init_app(app)
        if EMAIL_TEMPLATES_AVAILABLE and mail:
            if not email_service:
                email_service = EmailService(mail)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor, inicia sesión para acceder a esta página.'

# OAuth (login social): Google, Facebook, LinkedIn
oauth = OAuth(app) if OAUTH_AVAILABLE else None
if oauth:
    base_url = os.getenv('BASE_URL', '').rstrip('/')  # ej: https://miembros.relatic.org
    app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID', '')
    app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET', '')
    app.config['FACEBOOK_CLIENT_ID'] = os.getenv('FACEBOOK_CLIENT_ID', '')
    app.config['FACEBOOK_CLIENT_SECRET'] = os.getenv('FACEBOOK_CLIENT_SECRET', '')
    app.config['LINKEDIN_CLIENT_ID'] = os.getenv('LINKEDIN_CLIENT_ID', '')
    app.config['LINKEDIN_CLIENT_SECRET'] = os.getenv('LINKEDIN_CLIENT_SECRET', '')
    oauth.register(
        name='google',
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )
    oauth.register(
        name='facebook',
        client_kwargs={'scope': 'email public_profile'},
        authorize_url='https://www.facebook.com/v18.0/dialog/oauth',
        authorize_params=None,
        access_token_url='https://graph.facebook.com/v18.0/oauth/access_token',
        access_token_params=None,
        userinfo_endpoint='https://graph.facebook.com/v18.0/me?fields=id,name,email,first_name,last_name',
        userinfo_compliance_fix=lambda client, data: {
            'sub': str(data.get('id', '')),
            'name': data.get('name', ''),
            'given_name': data.get('first_name', ''),
            'family_name': data.get('last_name', ''),
            'email': data.get('email', ''),
        },
    )
    oauth.register(
        name='linkedin',
        client_kwargs={'scope': 'openid profile email'},
        authorize_url='https://www.linkedin.com/oauth/v2/authorization',
        access_token_url='https://www.linkedin.com/oauth/v2/accessToken',
        userinfo_endpoint='https://api.linkedin.com/v2/userinfo',
    )

# Inicializar servicio de correo
if EMAIL_TEMPLATES_AVAILABLE:
    email_service = EmailService(mail)
else:
    email_service = None

# Aplicar configuración de email desde BD al iniciar (si las tablas ya existen)
# Usar before_request en lugar de before_first_request (deprecado en Flask 2.2+)
_email_config_initialized = False
_license_checked = False
_single_tenant_other_orgs_deactivated = False
_rehome_users_to_default_org_done = False

@app.before_request
def ensure_session_organization():
    """Sesión manda: asegurar organization_id tras login o sesión antigua."""
    global _single_tenant_other_orgs_deactivated, _rehome_users_to_default_org_done
    if not has_request_context():
        return
    from utils.organization import default_organization_id, single_tenant_default_only

    def _rollback():
        try:
            db.session.rollback()
        except Exception:
            pass

    # Migraciones opcionales: errores aquí no deben impedir fijar organization_id en sesión.
    if single_tenant_default_only() and os.environ.get('NODEONE_REHOME_USERS_TO_DEFAULT_ORG', '').strip().lower() in (
        '1', 'true', 'yes', 'on',
    ):
        try:
            if not _rehome_users_to_default_org_done:
                def_oid = default_organization_id()
                n = User.query.filter(User.organization_id != def_oid).update(
                    {User.organization_id: def_oid},
                    synchronize_session=False,
                )
                db.session.commit()
                _rehome_users_to_default_org_done = True
                app.logger.info(
                    'NODEONE_REHOME_USERS_TO_DEFAULT_ORG: %s usuarios → org %s',
                    n,
                    def_oid,
                )
        except Exception as e:
            _rollback()
            app.logger.warning('ensure_session_organization (rehome): %s', e)

    if single_tenant_default_only() and os.environ.get('NODEONE_DEACTIVATE_OTHER_ORGS', '').strip().lower() in (
        '1', 'true', 'yes', 'on',
    ):
        try:
            if not _single_tenant_other_orgs_deactivated:
                def_oid = default_organization_id()
                n = SaasOrganization.query.filter(SaasOrganization.id != def_oid).update(
                    {SaasOrganization.is_active: False},
                    synchronize_session=False,
                )
                db.session.commit()
                _single_tenant_other_orgs_deactivated = True
                app.logger.info(
                    'NODEONE_DEACTIVATE_OTHER_ORGS: inactivas %s filas (distintas de org %s)',
                    n,
                    def_oid,
                )
        except Exception as e:
            _rollback()
            app.logger.warning('ensure_session_organization (deactivate): %s', e)

    try:
        if single_tenant_default_only():
            ensure_canonical_saas_organization_usable()
    except Exception as e:
        _rollback()
        app.logger.warning('ensure_canonical_saas_organization_usable: %s', e)

    try:
        if getattr(current_user, 'is_authenticated', False):
            if single_tenant_default_only():
                if getattr(current_user, 'is_admin', False):
                    if session.get('organization_id') in (None, ''):
                        session['organization_id'] = default_organization_id()
                    else:
                        try:
                            sid = int(session['organization_id'])
                        except (TypeError, ValueError):
                            session['organization_id'] = default_organization_id()
                        else:
                            if sid < 1:
                                session['organization_id'] = default_organization_id()
                            else:
                                o = SaasOrganization.query.get(sid)
                                if o is None or not getattr(o, 'is_active', True):
                                    session['organization_id'] = default_organization_id()
                else:
                    session['organization_id'] = int(
                        getattr(current_user, 'organization_id', None) or default_organization_id()
                    )
            elif session.get('organization_id') in (None, ''):
                session['organization_id'] = _usable_session_organization_id_for_user(current_user)
            else:
                try:
                    sid = int(session['organization_id'])
                except (TypeError, ValueError):
                    session['organization_id'] = _usable_session_organization_id_for_user(current_user)
                else:
                    if sid < 1:
                        session['organization_id'] = (
                            default_organization_id()
                            if single_tenant_default_only()
                            else _usable_session_organization_id_for_user(current_user)
                        )
                    else:
                        o = SaasOrganization.query.get(sid)
                        if o is None or not getattr(o, 'is_active', True):
                            session['organization_id'] = _usable_session_organization_id_for_user(current_user)
    except Exception as e:
        _rollback()
        app.logger.warning('ensure_session_organization (session): %s', e)
        try:
            if getattr(current_user, 'is_authenticated', False):
                if single_tenant_default_only():
                    if getattr(current_user, 'is_admin', False):
                        if session.get('organization_id') in (None, ''):
                            session['organization_id'] = default_organization_id()
                    else:
                        session['organization_id'] = int(
                            getattr(current_user, 'organization_id', None) or default_organization_id()
                        )
                else:
                    session['organization_id'] = _usable_session_organization_id_for_user(current_user)
        except Exception:
            pass


@app.before_request
def initialize_email_config():
    """Aplicar configuración de email al iniciar la aplicación (solo una vez)"""
    global _email_config_initialized
    if not _email_config_initialized:
        try:
            ensure_organization_settings()
            apply_email_config_from_db()
            ensure_office365_discount_code_id()
            ensure_discount_code_valid_for_office365()
            _email_config_initialized = True
        except Exception as e:
            print(f"⚠️ No se pudo inicializar configuración de email: {e}")
            import traceback
            traceback.print_exc()


@app.before_request
def check_license():
    """Verificar licencia de la aplicación"""
    global _license_checked
    
    # Solo verificar una vez al inicio
    if _license_checked:
        return
    
    _license_checked = True
    
    # Validar licencia usando el módulo independiente
    if LICENSE_VALIDATOR:
        LICENSE_VALIDATOR.check_and_log()
        
        # Modo permisivo: permite funcionar pero muestra advertencia
        # Para modo restrictivo, descomenta las siguientes líneas:
        # if not LICENSE_VALIDATOR.is_valid():
        #     if request.path.startswith('/api/'):
        #         return jsonify({'error': 'Servicio no disponible'}), 503
        #     return render_template('error.html', message='Servicio no disponible'), 503

# Agregar filtro personalizado para JSON en templates
import json
@app.template_filter('from_json')
def from_json_filter(value):
    """Filtro para parsear JSON en templates"""
    if not value:
        return {}
    try:
        return json.loads(value)
    except:
        return {}

# Helper function para obtener el logo del sistema
def get_system_logo():
    """
    Obtener URL del logo del sistema
    Busca primero en static/public/emails/logos/, luego en static/images/
    
    Returns:
        URL relativa del logo (para usar con url_for o directamente)
    """
    import os
    
    # Buscar en la nueva ubicación (prioridad)
    logo_dir_public = os.path.join(os.path.dirname(__file__), '..', 'static', 'public', 'emails', 'logos')
    logo_path_png = os.path.join(logo_dir_public, 'logo-relatic.png')
    logo_path_svg = os.path.join(logo_dir_public, 'logo-relatic.svg')
    
    if os.path.exists(logo_path_png):
        return 'public/emails/logos/logo-relatic.png'
    elif os.path.exists(logo_path_svg):
        return 'public/emails/logos/logo-relatic.svg'
    
    # Fallback a ubicación antigua
    logo_dir_old = os.path.join(os.path.dirname(__file__), '..', 'static', 'images')
    logo_path_old = os.path.join(logo_dir_old, 'logo-relatic.svg')
    
    if os.path.exists(logo_path_old):
        return 'images/logo-relatic.svg'
    
    # Si no existe ninguno, retornar la ruta por defecto
    return 'images/logo-relatic.svg'

def get_logo_cache_key():
    """Mtime del logo para cache-busting: al subir uno nuevo, la URL cambia."""
    logo_dir_public = os.path.join(os.path.dirname(__file__), '..', 'static', 'public', 'emails', 'logos')
    logo_dir_old = os.path.join(os.path.dirname(__file__), '..', 'static', 'images')
    for path in (
        os.path.join(logo_dir_public, 'logo-relatic.png'),
        os.path.join(logo_dir_public, 'logo-relatic.svg'),
        os.path.join(logo_dir_old, 'logo-relatic.png'),
        os.path.join(logo_dir_old, 'logo-relatic.svg'),
    ):
        if os.path.exists(path):
            try:
                return int(os.path.getmtime(path))
            except Exception:
                pass
    return 0

# Context processor para hacer get_system_logo disponible en todos los templates
@app.context_processor
def inject_logo():
    """Inyectar función para obtener logo en todos los templates y clave de caché."""
    return dict(
        get_system_logo=get_system_logo,
        get_logo_cache_key=get_logo_cache_key,
        get_nav_logo=get_nav_logo,
        get_nav_logo_cache_key=get_nav_logo_cache_key,
        get_nav_brand_name=get_nav_brand_name,
        get_platform_logo=get_platform_logo,
        datetime=datetime,
        ORG_HOME=ORG_HOME,
        ORG_NONE=ORG_NONE,
        scoped_query=scoped_query,
        single_tenant_default_only=single_tenant_default_only,
    )

# Context processor: design tokens de identidad por cliente (organization_settings)
@app.context_processor
def inject_theme():
    """Inyectar colores y URLs de identidad para :root CSS y logo/favicon."""
    try:
        s = OrganizationSettings.get_settings_for_session()
        return {
            'theme_primary': s.primary_color or '#2563EB',
            'theme_primary_dark': s.primary_color_dark or '#1E3A8A',
            'theme_accent': s.accent_color or '#06B6D4',
            'theme_logo_url': s.logo_url or '',   # vacío = usar get_system_logo()
            'theme_favicon_url': s.favicon_url or '',
        }
    except Exception:
        return {
            'theme_primary': '#2563EB',
            'theme_primary_dark': '#1E3A8A',
            'theme_accent': '#06B6D4',
            'theme_logo_url': '',
            'theme_favicon_url': '',
        }

# Context processor: planes de membresía configurables (para dropdowns y listas)
@app.context_processor
def inject_membership_plans():
    try:
        return {'membership_plans': MembershipPlan.get_active_ordered()}
    except Exception:
        return {'membership_plans': []}


# Context processor: apariencia del usuario (tema y tamaño de fuente) para aplicar en <html>
@app.context_processor
def inject_user_appearance():
    out = {'user_theme': 'light', 'user_font_size': 'medium'}
    if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
        try:
            row = UserSettings.query.filter_by(user_id=current_user.id).first()
            if row and row.preferences:
                prefs = json.loads(row.preferences)
                if prefs.get('theme') in ('light', 'dark', 'auto'):
                    out['user_theme'] = prefs['theme']
                if prefs.get('font_size') in ('small', 'medium', 'large'):
                    out['user_font_size'] = prefs['font_size']
        except Exception:
            pass
    return out

# Context processor para admin - pasar datos comunes a todas las páginas admin
@app.context_processor
def inject_admin_data():
    """Inyectar datos comunes para páginas admin"""
    admin_data = {}
    
    # Solo calcular si el usuario es admin y está autenticado
    if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated and hasattr(current_user, 'is_admin') and current_user.is_admin:
        try:
            # Contar pagos pendientes de revisión OCR
            pending_payments_count = Payment.query.filter(
                Payment.ocr_status.in_(['pending', 'needs_review']),
                Payment.status == 'pending'
            ).count()
            admin_data['pending_payments_count'] = pending_payments_count
        except:
            admin_data['pending_payments_count'] = 0
    else:
        admin_data['pending_payments_count'] = 0
    
    return admin_data

# Helper function para URLs de imágenes públicas
def get_public_image_url(filename, absolute=True):
    """
    Obtener URL de imagen pública desde static/public/
    
    Args:
        filename: Ruta relativa desde static/public/ 
                 (ej: 'emails/logos/logo-relatic.png')
        absolute: Si True, retorna URL absoluta (necesario para emails)
                 Si False, retorna URL relativa (para páginas web)
    
    Returns:
        URL completa de la imagen
        
    Ejemplo:
        # Para emails (URL absoluta)
        logo_url = get_public_image_url('emails/logos/logo-relatic.png', absolute=True)
        # → https://miembros.relatic.org/static/public/emails/logos/logo-relatic.png
        
        # Para páginas web (URL relativa)
        logo_url = get_public_image_url('emails/logos/logo-relatic.png', absolute=False)
        # → /static/public/emails/logos/logo-relatic.png
    """
    from flask import url_for, request
    
    # Generar URL relativa usando url_for
    relative_url = url_for('static', filename=f'public/{filename}')
    
    if absolute:
        # Para emails necesitamos URL absoluta
        # Intentar obtener base URL del request, si no está disponible usar variable de entorno
        if request and hasattr(request, 'url_root'):
            base_url = request.url_root.rstrip('/')
        else:
            # Fallback: usar variable de entorno o valor por defecto
            base_url = os.getenv('BASE_URL', 'https://miembros.relatic.org')
        return f"{base_url}{relative_url}"
    
    return relative_url

# Funciones de utilidad para validación de email
def validate_email_format(email):
    """
    Validación estricta de formato de email
    Retorna (is_valid, error_message)
    """
    if not email or not isinstance(email, str):
        return False, "El email es obligatorio"
    
    email = email.strip().lower()
    
    # Validación básica de longitud
    if len(email) > 120:
        return False, "El email es demasiado largo (máximo 120 caracteres)"
    
    if len(email) < 5:
        return False, "El email es demasiado corto"
    
    # Regex estricto para validar formato de email
    email_regex = r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$'
    
    if not re.match(email_regex, email):
        return False, "El formato del email no es válido"
    
    # Validar estructura del dominio
    parts = email.split('@')
    if len(parts) != 2:
        return False, "El email debe tener un formato válido (usuario@dominio.com)"
    
    domain = parts[1]
    domain_parts = domain.split('.')
    
    if len(domain_parts) < 2:
        return False, "El dominio del email debe tener al menos una extensión (ej: .com, .org)"
    
    # La extensión debe tener al menos 2 caracteres y ser solo letras
    extension = domain_parts[-1]
    if len(extension) < 2 or not extension.isalpha():
        return False, "La extensión del dominio no es válida"
    
    # Dominios temporales bloqueados (lista básica)
    blocked_domains = [
        'tempmail.com', 'mailinator.com', 'guerrillamail.com', 
        '10minutemail.com', 'throwaway.email', 'temp-mail.org',
        'maildrop.cc', 'getnada.com', 'mohmal.com'
    ]
    
    if domain.lower() in blocked_domains:
        return False, "No se permiten direcciones de correo temporal"
    
    return True, None

# Decorador para requerir permisos de administrador
def admin_required(f):
    """Decorador para requerir permisos de administrador (compatibilidad: is_admin o RBAC)."""
    from functools import wraps
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if bool(getattr(current_user, 'must_change_password', False)):
            flash('Debes cambiar tu contraseña antes de continuar.', 'warning')
            return redirect(url_for('auth.change_password'))
        if not current_user.is_admin and not _user_has_any_admin_permission(current_user):
            flash('No tienes permisos para acceder a esta página.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def platform_admin_required(f):
    """Solo User.is_admin (administrador de plataforma), no RBAC tenant."""
    from functools import wraps

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if bool(getattr(current_user, 'must_change_password', False)):
            flash('Debes cambiar tu contraseña antes de continuar.', 'warning')
            return redirect(url_for('auth.change_password'))
        if not getattr(current_user, 'is_admin', False):
            flash('Solo administradores de plataforma pueden acceder aquí.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)

    return decorated_function


def _user_has_any_admin_permission(user):
    """True si el usuario tiene al menos un rol RBAC con algún permiso (para admin_required)."""
    r = db.session.execute(
        db.text('SELECT 1 FROM user_role ur JOIN role_permission rp ON rp.role_id = ur.role_id WHERE ur.user_id = :uid LIMIT 1'),
        {'uid': user.id}
    ).fetchone()
    return r is not None


def require_permission(perm_code):
    """
    Decorador: exige que el usuario tenga el permiso (RBAC).
    Regla clave: backend valida por permiso, nunca por rol.
    """
    from functools import wraps
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if bool(getattr(current_user, 'must_change_password', False)):
                flash('Debes cambiar tu contraseña antes de continuar.', 'warning')
                return redirect(url_for('auth.change_password'))
            if not current_user.has_permission(perm_code):
                if request.is_json or request.accept_mimetypes.best == 'application/json':
                    return jsonify({'error': 'Forbidden', 'message': 'No tienes permiso para esta acción.'}), 403
                flash('No tienes permiso para esta acción.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# Lista de países válidos
VALID_COUNTRIES = [
    'Argentina', 'Bolivia', 'Brasil', 'Chile', 'Colombia', 'Costa Rica',
    'Cuba', 'Ecuador', 'El Salvador', 'España', 'Guatemala', 'Honduras',
    'México', 'Nicaragua', 'Panamá', 'Paraguay', 'Perú', 'República Dominicana',
    'Uruguay', 'Venezuela', 'Estados Unidos', 'Canadá', 'Otro'
]

def validate_country(country):
    """
    Validar que el país sea válido
    Retorna (is_valid, error_message)
    """
    if not country or not isinstance(country, str):
        return False, "El país es obligatorio"
    
    country = country.strip()
    
    if country not in VALID_COUNTRIES:
        return False, f"El país '{country}' no es válido. Seleccione un país de la lista."
    
    return True, None

def validate_cedula_or_passport(cedula_or_passport, country=None):
    """
    Validar formato de cédula o pasaporte según el país
    Retorna (is_valid, error_message)
    """
    if not cedula_or_passport or not isinstance(cedula_or_passport, str):
        return False, "La cédula o pasaporte es obligatorio"
    
    cedula_or_passport = cedula_or_passport.strip()
    
    # Validación básica de longitud
    if len(cedula_or_passport) < 4:
        return False, "La cédula o pasaporte es demasiado corta (mínimo 4 caracteres)"
    
    if len(cedula_or_passport) > 20:
        return False, "La cédula o pasaporte es demasiado larga (máximo 20 caracteres)"
    
    # Validación específica por país
    if country:
        country = country.strip()
        
        # Panamá: formato 8-123-456 o 12345678 (8 dígitos)
        if country == 'Panamá':
            # Remover guiones y espacios
            cleaned = re.sub(r'[-\s]', '', cedula_or_passport)
            if not cleaned.isdigit():
                return False, "La cédula panameña debe contener solo números"
            if len(cleaned) != 8:
                return False, "La cédula panameña debe tener 8 dígitos (formato: 8-123-456 o 12345678)"
        
        # Colombia: formato 1234567890 (10 dígitos)
        elif country == 'Colombia':
            cleaned = re.sub(r'[-\s.]', '', cedula_or_passport)
            if not cleaned.isdigit():
                return False, "La cédula colombiana debe contener solo números"
            if len(cleaned) < 7 or len(cleaned) > 10:
                return False, "La cédula colombiana debe tener entre 7 y 10 dígitos"
        
        # Argentina: formato 12345678 (8 dígitos) o 12.345.678
        elif country == 'Argentina':
            cleaned = re.sub(r'[-\s.]', '', cedula_or_passport)
            if not cleaned.isdigit():
                return False, "El DNI argentino debe contener solo números"
            if len(cleaned) < 7 or len(cleaned) > 8:
                return False, "El DNI argentino debe tener 7 u 8 dígitos"
        
        # México: formato CURP o RFC (alfanumérico)
        elif country == 'México':
            if not re.match(r'^[A-Z0-9]{10,18}$', cedula_or_passport.upper()):
                return False, "El formato de identificación mexicana no es válido (CURP o RFC)"
        
        # Pasaportes internacionales: formato alfanumérico
        # Permitir formato estándar de pasaporte (letras y números)
        if 'pasaporte' in cedula_or_passport.lower() or len(cedula_or_passport) > 10:
            if not re.match(r'^[A-Z0-9]{6,20}$', cedula_or_passport.upper()):
                return False, "El formato del pasaporte no es válido (debe ser alfanumérico, 6-20 caracteres)"
    
    # Validación general: debe ser alfanumérico (letras y números)
    if not re.match(r'^[A-Z0-9\-\s\.]{4,20}$', cedula_or_passport.upper()):
        return False, "El formato de cédula o pasaporte no es válido (debe ser alfanumérico)"
    
    return True, None

def generate_verification_token():
    """Generar token único para verificación de email"""
    return secrets.token_urlsafe(32)


def _enable_multi_tenant_catalog():
    v = os.environ.get('ENABLE_MULTI_TENANT_CATALOG', '1').strip().lower()
    return v in ('1', 'true', 'yes')


from utils.organization import (  # noqa: E402 — tras modelos SaaS
    ORG_HOME,
    ORG_NONE,
    default_organization_id,
    get_current_organization_id,
    get_user_home_organization_id,
    scoped_query,
    single_tenant_default_only,
    user_has_access_to_organization,
)


def ensure_canonical_saas_organization_usable():
    """
    Nombre visible de la org por defecto (id default): Easy Demo (sustituye nombres legados).
    Single-tenant: la fila saas_organization con id=default debe existir y estar activa.
    Nota: PK en SQLite es 1, 2, … — no existe organización id 0.
    """
    oid = default_organization_id()
    _legacy_default_org_names = (
        'organización principal',
        'default',
        'organización por defecto',
        'relatic',
        '',
    )
    org = SaasOrganization.query.get(oid)
    if org is not None and (org.name or '').strip().lower() in _legacy_default_org_names:
        org.name = 'Easy Demo'
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

    if not single_tenant_default_only():
        return

    org = SaasOrganization.query.get(oid)
    if org is None:
        db.session.add(SaasOrganization(id=oid, name='Easy Demo', is_active=True))
        try:
            db.session.commit()
            app.logger.warning('Creada saas_organization id=%s (faltaba; single-tenant)', oid)
        except Exception:
            db.session.rollback()
            app.logger.exception('No se pudo crear saas_organization id=%s', oid)
        return
    was_inactive = not bool(getattr(org, 'is_active', True))
    if was_inactive:
        org.is_active = True
        try:
            db.session.commit()
            app.logger.warning('Reactivada saas_organization id=%s (single-tenant)', oid)
        except Exception:
            db.session.rollback()
            app.logger.exception('No se pudo reactivar saas_organization id=%s', oid)


def _usable_session_organization_id_for_user(user):
    """Org de sesión: la del usuario si está activa; si no, primera org activa; si no, default."""
    oid = int(getattr(user, 'organization_id', None) or default_organization_id())
    org = SaasOrganization.query.get(oid)
    if org is not None and getattr(org, 'is_active', True):
        return oid
    first = SaasOrganization.query.filter_by(is_active=True).order_by(SaasOrganization.id.asc()).first()
    if first is not None:
        return int(first.id)
    return default_organization_id()


def _infra_org_id_for_runtime():
    return get_current_organization_id()


def _org_id_for_module_visibility():
    """
    Solo para flags de módulo en plantillas y guards públicos (¿módulo encendido?).
    No usar para queries de datos: ahí va get_current_organization_id() (anónimo = None).
    """
    try:
        oid = get_current_organization_id()
    except RuntimeError:
        oid = None
    if oid is not None:
        return oid
    return default_organization_id()


def has_saas_module_enabled(organization_id, module_code):
    if not module_code:
        return True
    if not _enable_multi_tenant_catalog():
        return True
    if organization_id is None:
        return False
    try:
        oid = int(organization_id)
    except (TypeError, ValueError):
        return False
    mod = SaasModule.query.filter_by(code=module_code).first()
    if mod is None:
        return True
    link = SaasOrgModule.query.filter_by(organization_id=oid, module_id=mod.id).first()
    if link is not None:
        return bool(link.enabled)
    return bool(mod.is_core)


def apply_session_organization_after_login(user, req):
    """Tras login: session['organization_id'] = org del usuario; selector opcional si hay acceso."""
    if single_tenant_default_only():
        ensure_canonical_saas_organization_usable()
        if getattr(user, 'is_admin', False):
            raw = (req.form.get('organization_id') or req.form.get('saas_organization_id') or '').strip()
            if raw:
                try:
                    cand = int(raw)
                except (TypeError, ValueError):
                    return False, 'Organización no válida.'
                org = SaasOrganization.query.get(cand)
                if org is None or not getattr(org, 'is_active', True):
                    return False, 'Organización no disponible.'
                if not user_has_access_to_organization(user, cand):
                    return False, 'No tienes acceso a esa organización.'
                session['organization_id'] = cand
                return True, None
            session['organization_id'] = default_organization_id()
            return True, None
        session['organization_id'] = int(getattr(user, 'organization_id', None) or default_organization_id())
        return True, None
    base = _usable_session_organization_id_for_user(user)
    session['organization_id'] = base
    raw = (req.form.get('organization_id') or req.form.get('saas_organization_id') or '').strip()
    if not raw:
        return True, None
    try:
        cand = int(raw)
    except (TypeError, ValueError):
        return False, 'Organización no válida.'
    org = SaasOrganization.query.get(cand)
    if org is None or not getattr(org, 'is_active', True):
        return False, 'Organización no disponible.'
    if not user_has_access_to_organization(user, cand):
        return False, 'No tienes acceso a esa organización.'
    session['organization_id'] = cand
    return True, None


def _admin_can_view_all_organizations():
    return bool(getattr(current_user, 'is_authenticated', False) and getattr(current_user, 'is_admin', False))


def _platform_admin_data_scope_organization_id():
    if not has_request_context():
        return None
    v = session.get('platform_admin_scope_org_id')
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _catalog_org_for_member_and_theme():
    return get_current_organization_id()


def _catalog_org_for_admin_catalog_routes():
    return get_current_organization_id()


def admin_data_scope_organization_id():
    """Listados admin: is_admin → sesión (selector); resto en single-tenant → user.organization_id."""
    if has_request_context() and getattr(current_user, 'is_authenticated', False):
        if single_tenant_default_only() and not getattr(current_user, 'is_admin', False):
            return int(getattr(current_user, 'organization_id', None) or default_organization_id())
    oid = get_current_organization_id()
    if oid is not None:
        return int(oid)
    return int(default_organization_id())


def tenant_data_organization_id():
    """
    Datos de negocio por empresa (beneficios, planes en vista miembro).
    - is_admin: sesión (selector).
    - resto: user.organization_id (evita mezclar con org canónica de sesión en single-tenant).
    """
    if not has_request_context():
        return int(default_organization_id())
    if not getattr(current_user, 'is_authenticated', False):
        return int(default_organization_id())
    if getattr(current_user, 'is_admin', False):
        oid = get_current_organization_id()
        return int(oid) if oid is not None else int(default_organization_id())
    return int(getattr(current_user, 'organization_id', None) or default_organization_id())


def _platform_nav_logo_relpath():
    """
    Logo de barra/favicon fijo de producto (Easy NodeOne).
    El upload de branding en /admin escribe logo-relatic.* en public/emails/logos y copia a
    images/logo-relatic.* — puede pisar el icono global. Este nombre no lo toca el upload.
    """
    static_dir = os.path.join(os.path.dirname(__file__), '..', 'static')
    p = os.path.join(static_dir, 'images', 'logo-easy-nodeone.svg')
    if os.path.exists(p):
        return 'images/logo-easy-nodeone.svg'
    p2 = os.path.join(static_dir, 'images', 'logo-relatic.svg')
    if os.path.exists(p2):
        return 'images/logo-relatic.svg'
    return 'images/logo-relatic.svg'


def _nav_theme_logo_relpath():
    """Ruta bajo static/ del logo configurado en organization_settings de la org activa (sesión)."""
    try:
        s = OrganizationSettings.get_settings_for_session()
        u = (s.logo_url or '').strip()
        if u:
            return u.lstrip('/')
    except Exception:
        pass
    return None


def get_nav_logo():
    # Branding por organización (sesión): si hay logo en organization_settings de esa org, usarlo.
    rel = _nav_theme_logo_relpath()
    if rel:
        return rel
    # Single-tenant: logo de plataforma fijo si no hay branding por tenant (evita pisar icono global).
    if single_tenant_default_only() and os.environ.get('NODEONE_NAV_USE_PLATFORM_LOGO', '1').strip().lower() not in (
        '0', 'false', 'no', 'off',
    ):
        return _platform_nav_logo_relpath()
    return get_system_logo()


def get_nav_logo_cache_key():
    rel = _nav_theme_logo_relpath()
    if rel:
        p = os.path.join(os.path.dirname(__file__), '..', 'static', rel)
        if os.path.exists(p):
            try:
                oid = 0
                try:
                    if has_request_context() and getattr(current_user, 'is_authenticated', False):
                        gco = get_current_organization_id()
                        oid = int(gco) if gco is not None else 0
                except Exception:
                    pass
                return int(os.path.getmtime(p)) + oid * 1_000_000_000
            except OSError:
                pass
        return 0
    if single_tenant_default_only() and os.environ.get('NODEONE_NAV_USE_PLATFORM_LOGO', '1').strip().lower() not in (
        '0', 'false', 'no', 'off',
    ):
        rel = _platform_nav_logo_relpath()
        p = os.path.join(os.path.dirname(__file__), '..', 'static', rel)
        if os.path.exists(p):
            try:
                return int(os.path.getmtime(p))
            except OSError:
                pass
        return 0
    return get_logo_cache_key()


def get_nav_brand_name():
    """Una sola regla: BRAND_MODE GLOBAL vs TENANT (sesión)."""
    try:
        mode = (app.config.get('BRAND_MODE') or 'GLOBAL').strip().upper()
        if mode == 'GLOBAL':
            return (app.config.get('APP_BRAND_NAME') or 'Easy NodeOne').strip() or 'Easy NodeOne'
        # Single-tenant: miembros → org canónica; admin plataforma → org activa en sesión.
        if single_tenant_default_only() and not (
            getattr(current_user, 'is_authenticated', False) and getattr(current_user, 'is_admin', False)
        ):
            oid = default_organization_id()
        else:
            oid = get_current_organization_id()
        if oid is None:
            return (app.config.get('APP_BRAND_NAME') or 'Easy NodeOne').strip() or 'Easy NodeOne'
        org = SaasOrganization.query.get(oid)
        if org and (org.name or '').strip():
            return (org.name or '').strip()
    except Exception:
        pass
    return (app.config.get('APP_BRAND_NAME') or 'Easy NodeOne').strip() or 'Easy NodeOne'


def get_platform_logo():
    return get_nav_logo()


def saas_module_enabled(module_code):
    """Para plantillas: {% if saas_module_enabled('appointments') %}. Incluye anónimos (org por defecto solo para el flag)."""
    return has_saas_module_enabled(_org_id_for_module_visibility(), module_code)


@app.context_processor
def inject_saas_module_template_helper():
    return dict(saas_module_enabled=saas_module_enabled)


@app.context_processor
def inject_admin_nav_context():
    """
    Flags y listas para base.html / admin (sidebar y dropdown).
    Sin esto, {% if show_tenant_admin_menu %} etc. quedan indefinidos → siempre ocultos.
    """
    out = {
        'show_tenant_admin_menu': False,
        'show_platform_admin_nav': False,
        'saas_organizations_nav': [],
        'multi_tenant_catalog_enabled': _enable_multi_tenant_catalog(),
        'catalog_admin_context_org_name': None,
        'effective_org_nav': None,
    }
    if not has_request_context():
        return out
    try:
        if not getattr(current_user, 'is_authenticated', False):
            return out
        is_flag_admin = bool(getattr(current_user, 'is_admin', False))
        rbac_admin = False
        if not is_flag_admin:
            try:
                rbac_admin = _user_has_any_admin_permission(current_user)
            except Exception:
                rbac_admin = False
        can_admin_ui = is_flag_admin or rbac_admin
        out['show_tenant_admin_menu'] = can_admin_ui
        # Selector de empresa: con catálogo multi-tenant (RBAC o admin) o siempre si is_admin.
        # Si ENABLE_MULTI_TENANT_CATALOG=0, antes no se mostraba ninguna org extra aunque existieran en BD.
        show_org_switcher = (can_admin_ui and _enable_multi_tenant_catalog()) or is_flag_admin
        if show_org_switcher:
            out['show_platform_admin_nav'] = True
            try:
                q = SaasOrganization.query.filter_by(is_active=True).order_by(
                    SaasOrganization.name.asc(), SaasOrganization.id.asc()
                )
                if single_tenant_default_only() and not is_flag_admin:
                    def_oid = default_organization_id()
                    out['saas_organizations_nav'] = [o for o in q.all() if int(o.id) == int(def_oid)]
                else:
                    out['saas_organizations_nav'] = q.all()
            except Exception:
                out['saas_organizations_nav'] = []
        if single_tenant_default_only() and not is_flag_admin:
            oid = default_organization_id()
        else:
            oid = get_current_organization_id()
        if oid is not None:
            try:
                out['effective_org_nav'] = int(oid)
            except Exception:
                out['effective_org_nav'] = None
            try:
                org = SaasOrganization.query.get(int(oid))
                if org and (getattr(org, 'name', None) or '').strip():
                    out['catalog_admin_context_org_name'] = org.name.strip()
            except Exception:
                pass
    except Exception:
        pass
    return out




# Función helper para validar archivos
def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Carpeta para guardar comprobantes de pago
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'static', 'uploads', 'receipts')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configuración del login manager
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Decoradores
def email_verified_required(f):
    """Decorador para requerir email verificado"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.email_verified:
            # Si la request es JSON/AJAX, devolver JSON en lugar de redirigir
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({
                    'success': False,
                    'error': 'Debes verificar tu email para acceder a esta función. Revisa tu bandeja de entrada o solicita un nuevo enlace de verificación.',
                    'requires_verification': True
                }), 403
            flash('Debes verificar tu email para acceder a esta función. Revisa tu bandeja de entrada o solicita un nuevo enlace de verificación.', 'warning')
            return redirect(url_for('resend_verification'))
        return f(*args, **kwargs)
    return decorated_function

def send_verification_email(user):
    """Enviar email de verificación al usuario. Retorna (éxito: bool, detalle_error: str|None)."""
    try:
        if not EMAIL_TEMPLATES_AVAILABLE or not email_service:
            print(f"⚠️ Email service no disponible. No se enviará email de verificación a {user.email}")
            return False, "Servicio de email no configurado. El administrador debe configurar SMTP en Configuración → Email."
        
        # Refrescar usuario desde BD para asegurar que tenemos la versión más reciente
        db.session.refresh(user)
        
        # Generar token de verificación (solo si no existe o expiró)
        if not user.email_verification_token or (user.email_verification_token_expires and user.email_verification_token_expires < datetime.utcnow()):
            token = generate_verification_token()
            user.email_verification_token = token
            user.email_verification_token_expires = datetime.utcnow() + timedelta(hours=24)
            user.email_verification_sent_at = datetime.utcnow()
            
            # Guardar token en BD ANTES de enviar email
            db.session.commit()
            print(f"✅ Token de verificación generado y guardado para {user.email}")
        else:
            # Usar token existente si aún es válido
            token = user.email_verification_token
            print(f"✅ Reutilizando token existente para {user.email}")
        
        # Obtener base_url
        if has_request_context() and request:
            base_url = request.url_root.rstrip('/')
        else:
            base_url = os.getenv('BASE_URL', 'https://miembros.relatic.org')
        
        verification_url = f"{base_url}/verify-email/{token}"
        
        # Generar HTML del email
        html_content = get_email_verification_email(user, verification_url)
        
        # Enviar email
        success = email_service.send_email(
            subject='Verifica tu Email - RelaticPanama',
            recipients=[user.email],
            html_content=html_content,
            email_type='email_verification',
            related_entity_type='user',
            related_entity_id=user.id,
            recipient_id=user.id,
            recipient_name=f"{user.first_name} {user.last_name}"
        )
        
        if success:
            print(f"✅ Email de verificación enviado exitosamente a {user.email}")
            return True, None
        else:
            print(f"❌ Error al enviar email de verificación a {user.email}")
            return False, "El servidor de correo rechazó el envío. Revisa la configuración SMTP en Configuración → Email (usuario y contraseña)."
            
    except Exception as e:
        err = str(e).strip()[:300]
        print(f"❌ Error enviando email de verificación: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return False, err if err else "Error desconocido al enviar el correo."


def _organization_id_for_public_registration():
    """organization_id para /register y OAuth nuevo usuario: form/query, subdominio en saas_organization, o default."""
    raw = (
        (request.form.get('saas_organization_id') or request.form.get('organization_id') or '')
        or (request.args.get('saas_organization_id') or request.args.get('organization_id') or '')
    ).strip()
    if raw:
        try:
            oid = int(raw)
        except (TypeError, ValueError):
            oid = None
        if oid and oid >= 1:
            org = SaasOrganization.query.get(oid)
            if org is not None and getattr(org, 'is_active', True):
                return oid
    host = (request.host or '').split(':')[0].lower()
    parts = host.split('.')
    if len(parts) >= 3:
        sub = parts[0]
        if sub and sub not in ('www', 'app', 'mail', 'web', 'cdn'):
            org = (
                SaasOrganization.query.filter_by(is_active=True)
                .filter(SaasOrganization.subdomain.isnot(None))
                .filter(SaasOrganization.subdomain != '')
                .filter(db.func.lower(SaasOrganization.subdomain) == sub.lower())
                .first()
            )
            if org is not None:
                return int(org.id)
    return default_organization_id()


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
    import json
    subscriptions_created = []
    events_registered = []
    
    # Obtener desglose de descuentos antes de procesar
    discount_breakdown = cart.get_discount_breakdown()
    original_amount = discount_breakdown['subtotal']
    final_amount = discount_breakdown['final_total']
    total_discount = discount_breakdown['total_discount']
    
    # Registrar uso del código de descuento si existe
    if cart.discount_code_id:
        discount_code = DiscountCode.query.get(cart.discount_code_id)
        if discount_code:
            # Incrementar contador de usos
            discount_code.current_uses = (discount_code.current_uses or 0) + 1
            
            # Crear registro de aplicación
            code_discount_amount = discount_breakdown['code_discount']['amount'] if discount_breakdown['code_discount'] else 0
            discount_application = DiscountApplication(
                discount_code_id=discount_code.id,
                user_id=payment.user_id,
                payment_id=payment.id,
                cart_id=cart.id,
                original_amount=original_amount,
                discount_amount=code_discount_amount,
                final_amount=final_amount
            )
            db.session.add(discount_application)
    
    # Procesar items del carrito
    for item in cart.items:
        if item.product_type == 'membership':
            metadata = json.loads(item.item_metadata) if item.item_metadata else {}
            membership_type = metadata.get('membership_type', 'basic')
            
            # Crear suscripción
            end_date = datetime.utcnow() + timedelta(days=365)
            subscription = Subscription(
                user_id=payment.user_id,
                payment_id=payment.id,
                membership_type=membership_type,
                status='active',
                end_date=end_date
            )
            db.session.add(subscription)
            subscriptions_created.append(subscription)
        
        elif item.product_type == 'event':
            # Registrar al evento
            metadata = json.loads(item.item_metadata) if item.item_metadata else {}
            event_id = metadata.get('event_id')
            if event_id:
                # Verificar si el evento existe
                event = Event.query.get(event_id)
                if event:
                    # Verificar si ya está registrado
                    existing_registration = EventRegistration.query.filter_by(
                        event_id=event_id,
                        user_id=payment.user_id
                    ).first()
                    
                    if not existing_registration:
                        # Calcular precio con descuentos
                        base_price = item.unit_price
                        discount_amount = 0
                        
                        # Aplicar descuento del código si aplica a eventos
                        if cart.discount_code_id:
                            discount_code = DiscountCode.query.get(cart.discount_code_id)
                            if discount_code and discount_code.applies_to in ['all', 'events']:
                                discount_amount = discount_code.apply_discount(base_price)
                        
                        final_price = base_price - discount_amount
                        
                        # Crear registro de evento
                        event_registration = EventRegistration(
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
                        db.session.add(event_registration)
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
                service = Service.query.get(service_id)
                
                # Verificar si es un servicio con cita agendada (tiene slot_id en metadata)
                slot_id = metadata.get('slot_id')
                if slot_id and metadata.get('requires_appointment'):
                    # Crear appointment con el slot seleccionado
                    try:
                        slot = AppointmentSlot.query.get(slot_id)
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
                        user = User.query.get(payment.user_id)
                        membership = user.get_active_membership() if user else None
                        membership_type = membership.membership_type if membership else 'basic'
                        
                        # Calcular precios
                        pricing = service.pricing_for_membership(membership_type)
                        final_price = pricing['final_price']
                        
                        # Determinar estado de pago
                        deposit_amount = metadata.get('deposit_amount', final_price)
                        if deposit_amount >= final_price:
                            payment_status = 'paid'
                        else:
                            payment_status = 'partial'
                        
                        # Crear Appointment (flujo agendable: slot + pago → confirmación directa)
                        appointment = Appointment(
                            appointment_type_id=appointment_type_id,
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
                            base_price=pricing['base_price'],
                            final_price=final_price,
                            discount_applied=pricing['base_price'] - pricing['final_price'],
                            payment_status=payment_status,
                            payment_method=payment.payment_method,
                            user_notes=case_description
                        )
                        
                        # Reservar slot
                        slot.reserved_seats = (slot.reserved_seats or 0) + 1
                        if slot.remaining_seats() == 0:
                            slot.is_available = False
                        
                        db.session.add(appointment)
                        db.session.flush()  # Para obtener el ID de la cita
                        print(f"✅ Cita creada: {appointment.reference} para servicio {service.name} en slot {slot_id}")
                        
                        # Enviar notificaciones
                        try:
                            from app import NotificationEngine
                            # Obtener el usuario del asesor
                            advisor_user = None
                            if advisor_id:
                                advisor_obj = Advisor.query.get(advisor_id)
                                if advisor_obj and advisor_obj.user:
                                    advisor_user = advisor_obj.user
                            
                            # Notificar al cliente (usuario que compró)
                            NotificationEngine.notify_appointment_created(appointment, user, advisor_user, service)
                            
                            # Notificar al asesor
                            if advisor_user:
                                NotificationEngine.notify_appointment_new_to_advisor(appointment, user, advisor_user, service)
                            
                            # Notificar a administradores
                            NotificationEngine.notify_appointment_new_to_admins(appointment, user, advisor_user, service)
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
                        user = User.query.get(payment.user_id)
                        if user:
                            appointment = create_diagnostic_appointment_from_payment(service, user, payment)
                            print(f"✅ Cita de diagnóstico creada en cola: {appointment.reference} para servicio {service.name}")
                            
                            # TODO: Enviar email al usuario informando que está en cola
                            # TODO: Enviar notificación al asesor sobre nueva cita en cola
                    except Exception as e:
                        print(f"⚠️ Error creando cita de diagnóstico para servicio {service_id}: {e}")
                        import traceback
                        traceback.print_exc()
                        # No fallar el pago si falla la creación de la cita
                        # Se puede crear manualmente después
        
        elif item.product_type == 'proposal':
            # Fase 8: Pago de propuesta aceptada (flujo consultivo)
            metadata = json.loads(item.item_metadata) if item.item_metadata else {}
            proposal_id = metadata.get('proposal_id') or item.product_id
            if proposal_id:
                prop = Proposal.query.get(proposal_id)
                if prop and prop.client_id == payment.user_id and prop.status == 'ENVIADA':
                    prop.status = 'ACEPTADA'
                    db.session.add(prop)
    
    db.session.commit()

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

        # Automatización marketing
        try:
            from _app.modules.marketing.service import trigger_automation
            base_url = None
            try:
                from flask import request as req
                base_url = req.host_url.rstrip('/') if req else None
            except Exception:
                pass
            if subscriptions_created:
                trigger_automation('membership_renewed', payment.user_id, base_url=base_url)
            for event_reg in events_registered:
                trigger_automation('event_registered', event_reg.user_id, base_url=base_url, event_id=event_reg.event_id)
        except Exception as e:
            print(f"Marketing automation error: {e}")

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


# Funciones helper para el carrito
def generate_discount_code(prefix="DSC", length=8, custom_part=None):
    """
    Genera un código de descuento único automáticamente
    
    Args:
        prefix: Prefijo del código (ej: "DSC", "EVT", "PROMO")
        length: Longitud de la parte aleatoria
        custom_part: Parte personalizada opcional (se inserta entre prefijo y aleatorio)
    
    Returns:
        str: Código único generado
    """
    import random
    import string
    
    max_attempts = 100
    attempt = 0
    
    while attempt < max_attempts:
        # Generar parte aleatoria
        random_part = ''.join(random.choices(
            string.ascii_uppercase + string.digits, 
            k=length
        ))
        
        # Construir código
        if custom_part:
            code = f"{prefix}-{custom_part}-{random_part}"
        else:
            code = f"{prefix}-{random_part}"
        
        # Verificar que no exista
        if not DiscountCode.query.filter_by(code=code).first():
            return code
        
        attempt += 1
    
    # Si no se pudo generar en 100 intentos, usar timestamp
    import time
    timestamp = str(int(time.time()))[-6:]
    code = f"{prefix}-{timestamp}"
    
    # Verificar unicidad final
    if DiscountCode.query.filter_by(code=code).first():
        code = f"{prefix}-{timestamp}-{random.randint(1000, 9999)}"
    
    return code


def get_or_create_cart(user_id):
    """Wrapper: delegar al módulo payments (compatibilidad para event_routes, appointment_routes, services, etc.)."""
    from _app.modules.payments.service import get_or_create_cart as _get
    return _get(user_id)


def add_to_cart(user_id, product_type, product_id, product_name, unit_price, quantity=1, product_description=None, metadata=None):
    """Wrapper: delegar al módulo payments (compatibilidad para event_routes, appointment_routes, services, etc.)."""
    from _app.modules.payments.service import add_to_cart as _add
    return _add(user_id, product_type, product_id, product_name, unit_price, quantity, product_description, metadata)


class NotificationEngine:
    """Motor de notificaciones para eventos y movimientos del sistema"""
    
    @staticmethod
    def _is_notification_enabled(notification_type):
        """Verificar si una notificación está habilitada en la configuración"""
        return NotificationSettings.is_enabled(notification_type)
    
    @staticmethod
    def notify_event_registration(event, user, registration):
        """Notificar a moderador, administrador y expositor del evento sobre un nuevo registro"""
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
            
            # Crear notificaciones y enviar emails a todos los responsables
            for recipient in recipients:
                # Crear notificación en la base de datos
                notification = Notification(
                    user_id=recipient.id,
                    event_id=event.id,
                    notification_type='event_registration',
                    title=f'Nuevo registro al evento: {event.title}',
                    message=f'El usuario {user.first_name} {user.last_name} ({user.email}) se ha registrado al evento "{event.title}". Estado: {registration.registration_status}.'
                )
                db.session.add(notification)
                # Hacer commit de la notificación primero
                db.session.flush()  # Para obtener el ID de la notificación
                
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
                        <p>Saludos,<br>Equipo RelaticPanama</p>
                        """
                    # Verificar que mail esté configurado
                    if not mail:
                        raise Exception("Flask-Mail no está inicializado")
                    
                    msg = Message(
                        subject=f'[RelaticPanama] Nuevo registro: {event.title}',
                        recipients=[recipient.email],
                        html=html_content
                    )
                    mail.send(msg)
                    notification.email_sent = True
                    notification.email_sent_at = datetime.utcnow()
                    # Registrar en EmailLog ANTES del commit
                    log_email_sent(
                        recipient_email=recipient.email,
                        subject=f'[RelaticPanama] Nuevo registro: {event.title}',
                        html_content=html_content,
                        email_type='event_registration_notification',
                        related_entity_type='event',
                        related_entity_id=event.id,
                        recipient_id=recipient.id,
                        recipient_name=f"{recipient.first_name} {recipient.last_name}",
                        status='sent'
                    )
                    print(f"✅ Email de notificación enviado a {recipient.email} para evento {event.id}")
                except Exception as e:
                    print(f"❌ Error enviando email de notificación a {recipient.email}: {e}")
                    import traceback
                    traceback.print_exc()
                    notification.email_sent = False
                    # Registrar fallo en EmailLog ANTES del commit
                    log_email_sent(
                        recipient_email=recipient.email,
                        subject=f'[RelaticPanama] Nuevo registro: {event.title}',
                        html_content='',
                        email_type='event_registration_notification',
                        related_entity_type='event',
                        related_entity_id=event.id,
                        recipient_id=recipient.id,
                        recipient_name=f"{recipient.first_name} {recipient.last_name}",
                        status='failed',
                        error_message=str(e)[:1000]  # Limitar tamaño del error
                    )
            
            db.session.commit()
            
        except Exception as e:
            print(f"Error en notify_event_registration: {e}")
            db.session.rollback()
    
    @staticmethod
    def notify_event_cancellation(event, user, registration):
        """Notificar a moderador, administrador y expositor sobre una cancelación"""
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('event_cancellation'):
            print(f"⚠️ Notificación 'event_cancellation' está deshabilitada. No se enviará correo.")
            return
        
        try:
            recipients = event.get_notification_recipients()
            
            if not recipients:
                return
            
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
                
                notification = Notification(
                    user_id=recipient.id,
                    event_id=event.id,
                    notification_type='event_cancellation',
                    title=f'Cancelación de registro: {event.title}',
                    message=f'El usuario {user.first_name} {user.last_name} ({user.email}) ha cancelado su registro al evento "{event.title}".'
                )
                db.session.add(notification)
                
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
                        <p>Saludos,<br>Equipo RelaticPanama</p>
                        """
                    msg = Message(
                        subject=f'[RelaticPanama] Cancelación de registro: {event.title}',
                        recipients=[recipient.email],
                        html=html_content
                    )
                    mail.send(msg)
                    notification.email_sent = True
                    notification.email_sent_at = datetime.utcnow()
                    # Registrar en EmailLog
                    log_email_sent(
                        recipient_email=recipient.email,
                        subject=f'[RelaticPanama] Cancelación de registro: {event.title}',
                        html_content=html_content,
                        email_type='event_cancellation_notification',
                        related_entity_type='event',
                        related_entity_id=event.id,
                        recipient_id=recipient.id,
                        recipient_name=f"{recipient.first_name} {recipient.last_name}",
                        status='sent'
                    )
                except Exception as e:
                    print(f"Error enviando email de cancelación a {recipient.email}: {e}")
                    log_email_sent(
                        recipient_email=recipient.email,
                        subject=f'[RelaticPanama] Cancelación de registro: {event.title}',
                        html_content='',
                        email_type='event_cancellation_notification',
                        related_entity_type='event',
                        related_entity_id=event.id,
                        recipient_id=recipient.id,
                        recipient_name=f"{recipient.first_name} {recipient.last_name}",
                        status='failed',
                        error_message=str(e)
                    )
            
            db.session.commit()
            
        except Exception as e:
            print(f"Error en notify_event_cancellation: {e}")
            db.session.rollback()
    
    @staticmethod
    def notify_event_confirmation(event, user, registration):
        """Notificar a moderador, administrador y expositor cuando se confirma un registro"""
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('event_confirmation'):
            print(f"⚠️ Notificación 'event_confirmation' está deshabilitada. No se enviará correo.")
            return
        
        try:
            recipients = event.get_notification_recipients()
            
            if not recipients:
                return
            
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
                
                notification = Notification(
                    user_id=recipient.id,
                    event_id=event.id,
                    notification_type='event_confirmation',
                    title=f'Registro confirmado: {event.title}',
                    message=f'El registro de {user.first_name} {user.last_name} al evento "{event.title}" ha sido confirmado.'
                )
                db.session.add(notification)
                
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
                        <p>Saludos,<br>Equipo RelaticPanama</p>
                        """
                    msg = Message(
                        subject=f'[RelaticPanama] Registro confirmado: {event.title}',
                        recipients=[recipient.email],
                        html=html_content
                    )
                    mail.send(msg)
                    notification.email_sent = True
                    notification.email_sent_at = datetime.utcnow()
                    # Registrar en EmailLog
                    log_email_sent(
                        recipient_email=recipient.email,
                        subject=f'[RelaticPanama] Registro confirmado: {event.title}',
                        html_content=html_content,
                        email_type='event_confirmation_notification',
                        related_entity_type='event',
                        related_entity_id=event.id,
                        recipient_id=recipient.id,
                        recipient_name=f"{recipient.first_name} {recipient.last_name}",
                        status='sent'
                    )
                    print(f"✅ Email de confirmación enviado a {recipient.email} para evento {event.id}")
                except Exception as e:
                    print(f"❌ Error enviando email de confirmación a {recipient.email}: {e}")
                    import traceback
                    traceback.print_exc()
                    notification.email_sent = False
                    # Registrar fallo en EmailLog
                    log_email_sent(
                        recipient_email=recipient.email,
                        subject=f'[RelaticPanama] Registro confirmado: {event.title}',
                        html_content='',
                        email_type='event_confirmation_notification',
                        related_entity_type='event',
                        related_entity_id=event.id,
                        recipient_id=recipient.id,
                        recipient_name=f"{recipient.first_name} {recipient.last_name}",
                        status='failed',
                        error_message=str(e)
                    )
            
            db.session.commit()
            
        except Exception as e:
            print(f"Error en notify_event_confirmation: {e}")
            db.session.rollback()
    
    @staticmethod
    def notify_event_update(event, changes=None):
        """Notificar cambios en un evento a todos los registrados"""
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('event_update'):
            print(f"⚠️ Notificación 'event_update' está deshabilitada. No se enviará correo.")
            return
        
        try:
            event_creator = User.query.get(event.created_by) if event.created_by else None
            
            if not event_creator:
                return
            
            # Notificar al creador
            notification = Notification(
                user_id=event_creator.id,
                event_id=event.id,
                notification_type='event_update',
                title=f'Evento actualizado: {event.title}',
                message=f'Se han realizado cambios en el evento "{event.title}".'
            )
            db.session.add(notification)
            
            # Notificar a todos los registrados
            registrations = EventRegistration.query.filter_by(
                event_id=event.id,
                registration_status='confirmed'
            ).all()
            
            for reg in registrations:
                user = User.query.get(reg.user_id)
                if user:
                    user_notification = Notification(
                        user_id=user.id,
                        event_id=event.id,
                        notification_type='event_update',
                        title=f'Actualización del evento: {event.title}',
                        message=f'El evento "{event.title}" al que estás registrado ha sido actualizado. Revisa los detalles en la plataforma.'
                    )
                    db.session.add(user_notification)
                    
                    try:
                        html_content = f"""
                            <h2>Evento Actualizado</h2>
                            <p>Hola {user.first_name},</p>
                            <p>El evento "{event.title}" al que estás registrado ha sido actualizado.</p>
                            <p>Te recomendamos revisar los detalles del evento en la plataforma.</p>
                            <p>Saludos,<br>Equipo RelaticPanama</p>
                            """
                        msg = Message(
                            subject=f'[RelaticPanama] Actualización: {event.title}',
                            recipients=[user.email],
                            html=html_content
                        )
                        mail.send(msg)
                        user_notification.email_sent = True
                        user_notification.email_sent_at = datetime.utcnow()
                        # Registrar en EmailLog
                        log_email_sent(
                            recipient_email=user.email,
                            subject=f'[RelaticPanama] Actualización: {event.title}',
                            html_content=html_content,
                            email_type='event_update',
                            related_entity_type='event',
                            related_entity_id=event.id,
                            recipient_id=user.id,
                            recipient_name=f"{user.first_name} {user.last_name}",
                            status='sent'
                        )
                    except Exception as e:
                        print(f"Error enviando email de actualización a {user.email}: {e}")
                        log_email_sent(
                            recipient_email=user.email,
                            subject=f'[RelaticPanama] Actualización: {event.title}',
                            html_content='',
                            email_type='event_update',
                            related_entity_type='event',
                            related_entity_id=event.id,
                            recipient_id=user.id,
                            recipient_name=f"{user.first_name} {user.last_name}",
                            status='failed',
                            error_message=str(e)
                        )
            
            db.session.commit()
            
        except Exception as e:
            print(f"Error en notify_event_update: {e}")
            db.session.rollback()
    
    @staticmethod
    def notify_membership_payment(user, payment, subscription):
        """Notificar confirmación de pago de membresía"""
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('membership_payment'):
            print(f"⚠️ Notificación 'membership_payment' está deshabilitada. No se enviará correo a {user.email}")
            return
        
        try:
            # Crear notificación
            notification = Notification(
                user_id=user.id,
                notification_type='membership_payment',
                title='Pago de Membresía Confirmado',
                message=f'Tu pago por la membresía {payment.membership_type.title()} ha sido procesado exitosamente. Válida hasta {subscription.end_date.strftime("%d/%m/%Y")}.'
            )
            db.session.add(notification)
            
            # Enviar email
            if EMAIL_TEMPLATES_AVAILABLE and email_service:
                html_content = get_membership_payment_confirmation_email(user, payment, subscription)
                email_service.send_email(
                    subject='Confirmación de Pago - RelaticPanama',
                    recipients=[user.email],
                    html_content=html_content,
                    email_type='membership_payment',
                    related_entity_type='payment',
                    related_entity_id=payment.id,
                    recipient_id=user.id,
                    recipient_name=f"{user.first_name} {user.last_name}"
                )
                notification.email_sent = True
                notification.email_sent_at = datetime.utcnow()
            else:
                # Fallback al método anterior
                send_payment_confirmation_email(user, payment, subscription)
                notification.email_sent = True
                notification.email_sent_at = datetime.utcnow()
            
            db.session.commit()
        except Exception as e:
            print(f"Error en notify_membership_payment: {e}")
            db.session.rollback()
    
    @staticmethod
    def notify_membership_expiring(user, subscription, days_left):
        """Notificar que la membresía está por expirar"""
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('membership_expiring'):
            print(f"⚠️ Notificación 'membership_expiring' está deshabilitada. No se enviará correo a {user.email}")
            return
        
        try:
            notification = Notification(
                user_id=user.id,
                notification_type='membership_expiring',
                title=f'Membresía Expirará en {days_left} Días',
                message=f'Tu membresía {subscription.membership_type.title()} expirará el {subscription.end_date.strftime("%d/%m/%Y")}. Renueva ahora para continuar disfrutando de todos los beneficios.'
            )
            db.session.add(notification)
            
            if EMAIL_TEMPLATES_AVAILABLE and email_service:
                html_content = get_membership_expiring_email(user, subscription, days_left)
                email_service.send_email(
                    subject=f'Tu Membresía Expirará en {days_left} Días - RelaticPanama',
                    recipients=[user.email],
                    html_content=html_content,
                    email_type='membership_expiring',
                    related_entity_type='subscription',
                    related_entity_id=subscription.id,
                    recipient_id=user.id,
                    recipient_name=f"{user.first_name} {user.last_name}"
                )
                notification.email_sent = True
                notification.email_sent_at = datetime.utcnow()
            
            db.session.commit()
        except Exception as e:
            print(f"Error en notify_membership_expiring: {e}")
            db.session.rollback()
    
    @staticmethod
    def notify_membership_expired(user, subscription):
        """Notificar que la membresía ha expirado"""
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('membership_expired'):
            print(f"⚠️ Notificación 'membership_expired' está deshabilitada. No se enviará correo a {user.email}")
            return
        
        try:
            notification = Notification(
                user_id=user.id,
                notification_type='membership_expired',
                title='Membresía Expirada',
                message=f'Tu membresía {subscription.membership_type.title()} ha expirado. Renueva ahora para reactivar tus beneficios.'
            )
            db.session.add(notification)
            
            if EMAIL_TEMPLATES_AVAILABLE and email_service:
                html_content = get_membership_expired_email(user, subscription)
                email_service.send_email(
                    subject='Tu Membresía Ha Expirado - RelaticPanama',
                    recipients=[user.email],
                    html_content=html_content,
                    email_type='membership_expired',
                    related_entity_type='subscription',
                    related_entity_id=subscription.id,
                    recipient_id=user.id,
                    recipient_name=f"{user.first_name} {user.last_name}"
                )
                notification.email_sent = True
                notification.email_sent_at = datetime.utcnow()
            
            db.session.commit()
        except Exception as e:
            print(f"Error en notify_membership_expired: {e}")
            db.session.rollback()
    
    @staticmethod
    def notify_membership_renewed(user, subscription):
        """Notificar renovación de membresía"""
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('membership_renewed'):
            print(f"⚠️ Notificación 'membership_renewed' está deshabilitada. No se enviará correo a {user.email}")
            return
        
        try:
            notification = Notification(
                user_id=user.id,
                notification_type='membership_renewed',
                title='Membresía Renovada',
                message=f'Tu membresía {subscription.membership_type.title()} ha sido renovada exitosamente. Válida hasta {subscription.end_date.strftime("%d/%m/%Y")}.'
            )
            db.session.add(notification)
            
            if EMAIL_TEMPLATES_AVAILABLE and email_service:
                html_content = get_membership_renewed_email(user, subscription)
                email_service.send_email(
                    subject='Membresía Renovada - RelaticPanama',
                    recipients=[user.email],
                    html_content=html_content,
                    email_type='membership_renewed',
                    related_entity_type='subscription',
                    related_entity_id=subscription.id,
                    recipient_id=user.id,
                    recipient_name=f"{user.first_name} {user.last_name}"
                )
                notification.email_sent = True
                notification.email_sent_at = datetime.utcnow()
            
            db.session.commit()
        except Exception as e:
            print(f"Error en notify_membership_renewed: {e}")
            db.session.rollback()
    
    @staticmethod
    def notify_appointment_confirmation(appointment, user, advisor):
        """Notificar confirmación de cita"""
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('appointment_confirmation'):
            print(f"⚠️ Notificación 'appointment_confirmation' está deshabilitada. No se enviará correo a {user.email}")
            return
        
        try:
            notification = Notification(
                user_id=user.id,
                notification_type='appointment_confirmation',
                title='Cita Confirmada',
                message=f'Tu cita con {advisor.first_name} {advisor.last_name} ha sido confirmada para el {(appointment.start_datetime.strftime("%d/%m/%Y %H:%M") if getattr(appointment, "start_datetime", None) else "próximo")}.'
            )
            db.session.add(notification)
            
            if EMAIL_TEMPLATES_AVAILABLE and email_service:
                html_content = get_appointment_confirmation_email(appointment, user, advisor)
                email_service.send_email(
                    subject='Cita Confirmada - RelaticPanama',
                    recipients=[user.email],
                    html_content=html_content,
                    email_type='appointment_confirmation',
                    related_entity_type='appointment',
                    related_entity_id=appointment.id,
                    recipient_id=user.id,
                    recipient_name=f"{user.first_name} {user.last_name}"
                )
                notification.email_sent = True
                notification.email_sent_at = datetime.utcnow()
            
            db.session.commit()
        except Exception as e:
            print(f"Error en notify_appointment_confirmation: {e}")
            db.session.rollback()
    
    @staticmethod
    def notify_appointment_reminder(appointment, user, advisor, hours_before=24):
        """Notificar recordatorio de cita"""
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('appointment_reminder'):
            print(f"⚠️ Notificación 'appointment_reminder' está deshabilitada. No se enviará correo a {user.email}")
            return
        
        try:
            notification = Notification(
                user_id=user.id,
                notification_type='appointment_reminder',
                title=f'Recordatorio: Cita en {hours_before} horas',
                message=f'Recuerda que tienes una cita con {advisor.first_name} {advisor.last_name} el {appointment.appointment_date.strftime("%d/%m/%Y")} a las {appointment.appointment_time}.'
            )
            db.session.add(notification)
            
            if EMAIL_TEMPLATES_AVAILABLE and email_service:
                html_content = get_appointment_reminder_email(appointment, user, advisor, hours_before)
                email_service.send_email(
                    subject=f'Recordatorio: Cita en {hours_before} horas - RelaticPanama',
                    recipients=[user.email],
                    html_content=html_content,
                    email_type='appointment_reminder',
                    related_entity_type='appointment',
                    related_entity_id=appointment.id,
                    recipient_id=user.id,
                    recipient_name=f"{user.first_name} {user.last_name}"
                )
                notification.email_sent = True
                notification.email_sent_at = datetime.utcnow()
            
            db.session.commit()
        except Exception as e:
            print(f"Error en notify_appointment_reminder: {e}")
            db.session.rollback()
    
    @staticmethod
    def notify_appointment_created(appointment, user, advisor, service):
        """Notificar al cliente que su cita fue creada después del pago"""
        try:
            # Crear notificación para el cliente
            notification = Notification(
                user_id=user.id,
                notification_type='appointment_created',
                title='Cita Agendada - Pendiente de Confirmación',
                message=f'Tu cita para "{service.name if service else appointment.appointment_type.name}" ha sido agendada para el {appointment.start_datetime.strftime("%d/%m/%Y")} a las {appointment.start_datetime.strftime("%H:%M")}. Está pendiente de confirmación por el asesor.'
            )
            db.session.add(notification)
            db.session.flush()
            
            # Enviar email al cliente
            if EMAIL_TEMPLATES_AVAILABLE and email_service:
                try:
                    from email_templates import get_appointment_created_email
                    html_content = get_appointment_created_email(appointment, user, advisor, service)
                    email_service.send_email(
                        subject='Cita Agendada - RelaticPanama',
                        recipients=[user.email],
                        html_content=html_content,
                        email_type='appointment_created',
                        related_entity_type='appointment',
                        related_entity_id=appointment.id,
                        recipient_id=user.id,
                        recipient_name=f"{user.first_name} {user.last_name}"
                    )
                    notification.email_sent = True
                    notification.email_sent_at = datetime.utcnow()
                    print(f"✅ Email de cita creada enviado a cliente {user.email}")
                except Exception as e:
                    print(f"⚠️ Error enviando email de cita creada a cliente: {e}")
            
            db.session.commit()
        except Exception as e:
            print(f"Error en notify_appointment_created: {e}")
            db.session.rollback()
    
    @staticmethod
    def notify_appointment_new_to_advisor(appointment, user, advisor, service):
        """Notificar al asesor sobre nueva cita que requiere confirmación"""
        if not advisor:
            return
        
        try:
            # Crear notificación para el asesor
            notification = Notification(
                user_id=advisor.id,
                notification_type='appointment_new',
                title='Nueva Cita Pendiente de Confirmación',
                message=f'Nueva cita solicitada por {user.first_name} {user.last_name} para "{service.name if service else appointment.appointment_type.name}" el {appointment.start_datetime.strftime("%d/%m/%Y")} a las {appointment.start_datetime.strftime("%H:%M")}. Requiere tu confirmación.'
            )
            db.session.add(notification)
            db.session.flush()
            
            # Enviar email al asesor
            if EMAIL_TEMPLATES_AVAILABLE and email_service:
                try:
                    from email_templates import get_appointment_new_advisor_email
                    html_content = get_appointment_new_advisor_email(appointment, user, advisor, service)
                    email_service.send_email(
                        subject='Nueva Cita Pendiente de Confirmación - RelaticPanama',
                        recipients=[advisor.email],
                        html_content=html_content,
                        email_type='appointment_new_advisor',
                        related_entity_type='appointment',
                        related_entity_id=appointment.id,
                        recipient_id=advisor.id,
                        recipient_name=f"{advisor.first_name} {advisor.last_name}"
                    )
                    notification.email_sent = True
                    notification.email_sent_at = datetime.utcnow()
                    print(f"✅ Email de nueva cita enviado a asesor {advisor.email}")
                except Exception as e:
                    print(f"⚠️ Error enviando email de nueva cita a asesor: {e}")
            
            db.session.commit()
        except Exception as e:
            print(f"Error en notify_appointment_new_to_advisor: {e}")
            db.session.rollback()
    
    @staticmethod
    def notify_appointment_new_to_admins(appointment, user, advisor, service):
        """Notificar a administradores sobre nueva cita creada"""
        try:
            # Obtener todos los administradores activos
            admins = User.query.filter_by(is_admin=True, is_active=True).all()
            
            if not admins:
                print("⚠️ No se encontraron administradores para notificar")
                return
            
            advisor_name = f"{advisor.first_name} {advisor.last_name}" if advisor else "No asignado"
            
            for admin in admins:
                # Crear notificación para cada administrador
                notification = Notification(
                    user_id=admin.id,
                    notification_type='appointment_new_admin',
                    title='Nueva Cita Creada',
                    message=f'Nueva cita creada: {user.first_name} {user.last_name} ({user.email}) solicitó "{service.name if service else appointment.appointment_type.name}" con {advisor_name} para el {appointment.start_datetime.strftime("%d/%m/%Y")} a las {appointment.start_datetime.strftime("%H:%M")}.'
                )
                db.session.add(notification)
                db.session.flush()
                
                # Enviar email a cada administrador
                if EMAIL_TEMPLATES_AVAILABLE and email_service:
                    try:
                        from email_templates import get_appointment_new_admin_email
                        html_content = get_appointment_new_admin_email(appointment, user, advisor, service, admin)
                        email_service.send_email(
                            subject='Nueva Cita Creada - RelaticPanama',
                            recipients=[admin.email],
                            html_content=html_content,
                            email_type='appointment_new_admin',
                            related_entity_type='appointment',
                            related_entity_id=appointment.id,
                            recipient_id=admin.id,
                            recipient_name=f"{admin.first_name} {admin.last_name}"
                        )
                        notification.email_sent = True
                        notification.email_sent_at = datetime.utcnow()
                        print(f"✅ Email de nueva cita enviado a administrador {admin.email}")
                    except Exception as e:
                        print(f"⚠️ Error enviando email de nueva cita a administrador {admin.email}: {e}")
            
            db.session.commit()
        except Exception as e:
            print(f"Error en notify_appointment_new_to_admins: {e}")
            db.session.rollback()
    
    @staticmethod
    def notify_welcome(user):
        """Notificar bienvenida a nuevo usuario"""
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('welcome'):
            print(f"⚠️ Notificación 'welcome' está deshabilitada. No se enviará correo a {user.email}")
            return
        
        try:
            notification = Notification(
                user_id=user.id,
                notification_type='welcome',
                title='¡Bienvenido a RelaticPanama!',
                message='Te damos la bienvenida a RelaticPanama. Explora nuestros eventos, recursos y servicios disponibles.'
            )
            db.session.add(notification)
            
            # Verificar si email_service está disponible
            if not EMAIL_TEMPLATES_AVAILABLE:
                print(f"⚠️ EMAIL_TEMPLATES_AVAILABLE es False. No se enviará correo a {user.email}")
                db.session.commit()
                return
            
            if not email_service:
                print(f"⚠️ email_service es None. No se enviará correo a {user.email}")
                db.session.commit()
                return
            
            # Generar HTML del email
            try:
                html_content = get_welcome_email(user)
            except Exception as e:
                print(f"❌ Error al generar template de bienvenida: {e}")
                import traceback
                traceback.print_exc()
                db.session.commit()  # Guardar notificación aunque falle el email
                return
            
            # Enviar email
            try:
                success = email_service.send_email(
                    subject='Bienvenido a RelaticPanama',
                    recipients=[user.email],
                    html_content=html_content,
                    email_type='welcome',
                    related_entity_type='user',
                    related_entity_id=user.id,
                    recipient_id=user.id,
                    recipient_name=f"{user.first_name} {user.last_name}"
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
            
            db.session.commit()
        except Exception as e:
            print(f"❌ Error en notify_welcome: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
    
    @staticmethod
    def notify_event_registration_to_user(event, user, registration):
        """Notificar al usuario sobre su registro a evento"""
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('event_registration_user'):
            print(f"⚠️ Notificación 'event_registration_user' está deshabilitada. No se enviará correo a {user.email}")
            return
        
        try:
            notification = Notification(
                user_id=user.id,
                event_id=event.id,
                notification_type='event_registration_user',
                title=f'Registro Confirmado: {event.title}',
                message=f'Tu registro al evento "{event.title}" ha sido confirmado. Estado: {registration.registration_status}.'
            )
            db.session.add(notification)
            
            if EMAIL_TEMPLATES_AVAILABLE and email_service:
                html_content = get_event_registration_email(event, user, registration)
                email_service.send_email(
                    subject=f'Registro Confirmado: {event.title}',
                    recipients=[user.email],
                    html_content=html_content,
                    email_type='event_registration',
                    related_entity_type='event',
                    related_entity_id=event.id,
                    recipient_id=user.id,
                    recipient_name=f"{user.first_name} {user.last_name}"
                )
                notification.email_sent = True
                notification.email_sent_at = datetime.utcnow()
            
            db.session.commit()
        except Exception as e:
            print(f"Error en notify_event_registration_to_user: {e}")
            db.session.rollback()
    
    @staticmethod
    def notify_event_cancellation_to_user(event, user):
        """Notificar al usuario sobre cancelación de registro"""
        # Verificar si la notificación está habilitada
        if not NotificationEngine._is_notification_enabled('event_cancellation_user'):
            print(f"⚠️ Notificación 'event_cancellation_user' está deshabilitada. No se enviará correo a {user.email}")
            return
        
        try:
            notification = Notification(
                user_id=user.id,
                event_id=event.id,
                notification_type='event_cancellation_user',
                title=f'Registro Cancelado: {event.title}',
                message=f'Tu registro al evento "{event.title}" ha sido cancelado.'
            )
            db.session.add(notification)
            
            if EMAIL_TEMPLATES_AVAILABLE and email_service:
                html_content = get_event_cancellation_email(event, user)
                email_service.send_email(
                    subject=f'Cancelación de Registro: {event.title}',
                    recipients=[user.email],
                    html_content=html_content,
                    email_type='event_cancellation',
                    related_entity_type='event',
                    related_entity_id=event.id,
                    recipient_id=user.id,
                    recipient_name=f"{user.first_name} {user.last_name}"
                )
                notification.email_sent = True
                notification.email_sent_at = datetime.utcnow()
            
            db.session.commit()
        except Exception as e:
            print(f"Error en notify_event_cancellation_to_user: {e}")
            db.session.rollback()


def log_email_sent(recipient_email, subject, html_content=None, text_content=None, 
                   email_type=None, related_entity_type=None, related_entity_id=None,
                   recipient_id=None, recipient_name=None, status='sent', error_message=None):
    """Registrar un email enviado en EmailLog"""
    try:
        email_log = EmailLog(
            recipient_id=recipient_id,
            recipient_email=recipient_email,
            recipient_name=recipient_name or recipient_email,
            subject=subject,
            html_content=html_content[:5000] if html_content else None,
            text_content=text_content[:5000] if text_content else None,
            email_type=email_type or 'general',
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            status=status,
            error_message=error_message[:1000] if error_message else None,
            sent_at=datetime.utcnow() if status == 'sent' else None
        )
        db.session.add(email_log)
        db.session.commit()
        print(f"📧 Email registrado en log: {email_type or 'general'} → {recipient_email} ({status})")
    except Exception as e:
        print(f"❌ Error registrando email en log: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()

def send_ocr_review_notifications(payment, user, ocr_extracted_data):
    """Enviar notificaciones cuando OCR necesita revisión manual"""
    try:
        # Obtener administradores
        admins = User.query.filter_by(is_admin=True, is_active=True).all()
        
        if not admins:
            print("⚠️ No hay administradores para notificar")
            return
        
        # Preparar datos para el email
        expected_amount = payment.amount / 100.0
        extracted_amount = ocr_extracted_data.get('amount') if ocr_extracted_data else None
        
        # Email al usuario
        if EMAIL_TEMPLATES_AVAILABLE and email_service:
            user_html = f"""
            <h2>Revisión de Pago Requerida</h2>
            <p>Hola {user.first_name},</p>
            <p>Hemos recibido tu comprobante de pago, pero necesitamos verificar algunos datos:</p>
            <ul>
                <li><strong>Monto esperado:</strong> ${expected_amount:.2f}</li>
                <li><strong>Monto en comprobante:</strong> ${extracted_amount:.2f} {'(detectado)' if extracted_amount else '(no detectado)'}</li>
                <li><strong>Método de pago:</strong> {payment.payment_method.title()}</li>
            </ul>
            <p>Nuestro equipo revisará tu comprobante y te notificará cuando se apruebe tu membresía.</p>
            <p>Saludos,<br>Equipo RelaticPanama</p>
            """
            
            email_service.send_email(
                subject='Revisión de Pago - RelaticPanama',
                recipients=[user.email],
                html_content=user_html,
                email_type='payment_review',
                related_entity_type='payment',
                related_entity_id=payment.id,
                recipient_id=user.id,
                recipient_name=f"{user.first_name} {user.last_name}"
            )
        
        # Email a administradores
        admin_html = f"""
        <h2>Revisión de Pago Requerida</h2>
        <p>Se requiere revisión manual de un pago:</p>
        <ul>
            <li><strong>Usuario:</strong> {user.first_name} {user.last_name} ({user.email})</li>
            <li><strong>ID de Pago:</strong> {payment.id}</li>
            <li><strong>Monto esperado:</strong> ${expected_amount:.2f}</li>
            <li><strong>Monto detectado:</strong> ${extracted_amount:.2f} {'(detectado)' if extracted_amount else '(no detectado)'}</li>
            <li><strong>Método:</strong> {payment.payment_method.title()}</li>
            <li><strong>Referencia:</strong> {ocr_extracted_data.get('reference', 'N/A') if ocr_extracted_data else 'N/A'}</li>
            <li><strong>Fecha detectada:</strong> {ocr_extracted_data.get('date', 'N/A') if ocr_extracted_data else 'N/A'}</li>
            <li><strong>Banco detectado:</strong> {ocr_extracted_data.get('bank', 'N/A') if ocr_extracted_data else 'N/A'}</li>
        </ul>
        <p><a href="/admin/payments/review/{payment.id}">Revisar Pago</a></p>
        """
        
        for admin in admins:
            if EMAIL_TEMPLATES_AVAILABLE and email_service:
                email_service.send_email(
                    subject=f'Revisión de Pago Requerida - Pago #{payment.id}',
                    recipients=[admin.email],
                    html_content=admin_html,
                    email_type='payment_review_admin',
                    related_entity_type='payment',
                    related_entity_id=payment.id,
                    recipient_id=admin.id,
                    recipient_name=f"{admin.first_name} {admin.last_name}"
                )
        
        print(f"✅ Notificaciones OCR enviadas para Payment ID: {payment.id}")
    except Exception as e:
        print(f"⚠️ Error enviando notificaciones OCR: {e}")
        import traceback
        traceback.print_exc()

def send_payment_confirmation_email(user, payment, subscription):
    """Enviar email de confirmación de pago"""
    try:
        html_content = f"""
            <h2>¡Pago Confirmado!</h2>
            <p>Hola {user.first_name},</p>
            <p>Tu pago por la membresía {payment.membership_type.title()} ha sido procesado exitosamente.</p>
            <p><strong>Detalles del pago:</strong></p>
            <ul>
                <li>Membresía: {payment.membership_type.title()}</li>
                <li>Monto: ${payment.amount / 100:.2f}</li>
                <li>Fecha: {payment.created_at.strftime('%d/%m/%Y')}</li>
                <li>Válida hasta: {subscription.end_date.strftime('%d/%m/%Y')}</li>
            </ul>
            <p>Ya puedes acceder a todos los beneficios de tu membresía.</p>
            <p>¡Gracias por ser parte de RelaticPanama!</p>
            """
        msg = Message(
            subject='Confirmación de Pago - RelaticPanama',
            recipients=[user.email],
            html=html_content
        )
        mail.send(msg)
        # Registrar en EmailLog
        log_email_sent(
            recipient_email=user.email,
            subject='Confirmación de Pago - RelaticPanama',
            html_content=html_content,
            email_type='membership_payment',
            related_entity_type='payment',
            related_entity_id=payment.id,
            recipient_id=user.id,
            recipient_name=f"{user.first_name} {user.last_name}",
            status='sent'
        )
    except Exception as e:
        print(f"Error sending email: {e}")
        # Registrar fallo en EmailLog
        log_email_sent(
            recipient_email=user.email,
            subject='Confirmación de Pago - RelaticPanama',
            html_content='',
            email_type='membership_payment',
            related_entity_type='payment',
            related_entity_id=payment.id,
            recipient_id=user.id,
            recipient_name=f"{user.first_name} {user.last_name}",
            status='failed',
            error_message=str(e)
        )



def _default_user_preferences():
    """Valores por defecto para configuración de usuario."""
    return {
        'notif_email': True,
        'notif_events': True,
        'notif_publications': False,
        'notif_newsletter': True,
        'privacy_profile': False,
        'privacy_email': False,
        'privacy_activity': True,
        'language': 'es',
        'timezone': 'America/Panama',
        'theme': 'light',
        'font_size': 'medium',
    }




# Blueprints modulares: una sola vía (guards SaaS antes de register; idempotente).
# El bloque legacy que registraba auth/members/… aquí sin guards hacía que register_modules
# saltara el registro y dejaba payments/policies/services sin guard SaaS.
try:
    from nodeone.core.features import register_modules

    register_modules(app)
except Exception as e:
    print(f"Warning: register_modules: {e}")

# Funciones de utilidad
def create_sample_data():
    """Crear datos de ejemplo"""
    # Crear beneficios de ejemplo
    benefits = [
        Benefit(name='Acceso a Revistas', description='Acceso completo a la biblioteca de revistas especializadas', membership_type='basic', organization_id=1),
        Benefit(name='Base de Datos', description='Acceso a bases de datos de investigación', membership_type='basic', organization_id=1),
        Benefit(name='Asesoría de Publicación', description='Sesiones de asesoría para publicaciones académicas', membership_type='premium', organization_id=1),
        Benefit(name='Soporte Prioritario', description='Soporte técnico prioritario', membership_type='premium', organization_id=1),
    ]
    
    for benefit in benefits:
        if not Benefit.query.filter_by(name=benefit.name, organization_id=1).first():
            db.session.add(benefit)
    
    db.session.commit()

def ensure_must_change_password_column():
    """Añadir columna must_change_password a user si no existe (compatibilidad con DB existente)."""
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        if 'user' not in inspector.get_table_names():
            return
        columns = [col['name'] for col in inspector.get_columns('user')]
        if 'must_change_password' in columns:
            return
        db.session.execute(text('ALTER TABLE user ADD COLUMN must_change_password BOOLEAN DEFAULT 0'))
        db.session.commit()
        print('✅ Columna user.must_change_password añadida.')
    except Exception as e:
        db.session.rollback()
        print(f'⚠️ ensure_must_change_password_column: {e}')


def ensure_benefit_icon_color_columns():
    """Añadir columnas icon y color a benefit si no existen."""
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        if 'benefit' not in inspector.get_table_names():
            return
        columns = [col['name'] for col in inspector.get_columns('benefit')]
        if 'icon' not in columns:
            db.session.execute(text('ALTER TABLE benefit ADD COLUMN icon VARCHAR(80)'))
            db.session.commit()
            print('✅ Columna benefit.icon añadida.')
        if 'color' not in columns:
            db.session.execute(text('ALTER TABLE benefit ADD COLUMN color VARCHAR(20)'))
            db.session.commit()
            print('✅ Columna benefit.color añadida.')
    except Exception as e:
        db.session.rollback()
        print(f'⚠️ ensure_benefit_icon_color_columns: {e}')


def ensure_membership_plan_table():
    """Crear tabla membership_plan si no existe y sembrar planes por defecto."""
    try:
        MembershipPlan.__table__.create(db.engine, checkfirst=True)
        if MembershipPlan.query.count() == 0:
            defaults = [
                {'slug': 'basic', 'name': 'Básico', 'price_yearly': 0, 'price_monthly': 0, 'display_order': 0, 'level': 0, 'badge': 'Incluido con la membresía gratuita', 'color': 'bg-success', 'organization_id': 1},
                {'slug': 'pro', 'name': 'Pro', 'price_yearly': 60, 'price_monthly': 5, 'display_order': 1, 'level': 1, 'badge': 'Plan recomendado', 'color': 'bg-info', 'organization_id': 1},
                {'slug': 'premium', 'name': 'Premium', 'price_yearly': 120, 'price_monthly': 10, 'display_order': 2, 'level': 2, 'badge': 'Más beneficios', 'color': 'bg-primary', 'organization_id': 1},
                {'slug': 'deluxe', 'name': 'De Luxe', 'price_yearly': 200, 'price_monthly': 17, 'display_order': 3, 'level': 3, 'badge': 'Experiencia completa', 'color': 'bg-warning text-dark', 'organization_id': 1},
                {'slug': 'corporativo', 'name': 'Corporativo', 'price_yearly': 300, 'price_monthly': 25, 'display_order': 4, 'level': 4, 'badge': 'Para empresas', 'color': 'bg-dark text-white', 'organization_id': 1},
                {'slug': 'admin', 'name': 'Admin', 'price_yearly': 0, 'price_monthly': 0, 'display_order': 99, 'level': 99, 'badge': 'Acceso administrador', 'color': 'bg-secondary', 'organization_id': 1},
            ]
            for d in defaults:
                db.session.add(MembershipPlan(**d))
            db.session.commit()
            print('✅ Tabla membership_plan creada y planes por defecto insertados.')
    except Exception as e:
        db.session.rollback()
        print(f'⚠️ ensure_membership_plan_table: {e}')


def _politica_correo_institucional_html():
    """Contenido HTML de la Política de Uso de Correo Institucional (versión 1.0)."""
    return """
<p><strong>Relatic Panamá</strong><br>Versión 1.0</p>

<h2>1. Naturaleza del Servicio</h2>
<p>El correo institucional @relaticpanama.org es un beneficio otorgado por Relatic Panamá a sus miembros activos como parte de su ecosistema digital institucional.</p>
<p>La asignación de la cuenta está sujeta a las condiciones establecidas en la presente política y podrá estar subsidiada total o parcialmente según campañas vigentes.</p>

<h2>2. Vigencia</h2>
<p>La cuenta de correo institucional permanecerá activa únicamente mientras el miembro mantenga su condición de miembro activo.</p>
<p>En caso de pérdida de membresía por:</p>
<ul>
<li>No renovación</li>
<li>Suspensión</li>
<li>Retiro voluntario</li>
<li>Incumplimiento de normas institucionales</li>
</ul>
<p>La cuenta podrá ser suspendida o eliminada conforme a los plazos establecidos.</p>

<h2>3. Suspensión y Eliminación</h2>
<p>En caso de pérdida de estatus activo:</p>
<ul>
<li>Se otorgará un período de gracia de hasta <strong>15 días calendario</strong>.</li>
<li>Posteriormente, la cuenta será suspendida.</li>
<li>Transcurridos hasta <strong>60 días adicionales</strong>, la cuenta podrá ser eliminada definitivamente.</li>
</ul>
<p>Relatic Panamá no garantiza la recuperación de información una vez eliminada la cuenta.</p>

<h2>4. Uso Adecuado</h2>
<p>El correo institucional debe utilizarse exclusivamente para fines académicos, institucionales o profesionales relacionados con la organización.</p>
<p>Queda prohibido:</p>
<ul>
<li>Envío de spam.</li>
<li>Actividades ilícitas.</li>
<li>Uso para fraudes o suplantación de identidad.</li>
<li>Compartir credenciales con terceros.</li>
<li>Uso que afecte la reputación institucional.</li>
</ul>
<p>Relatic Panamá se reserva el derecho de suspender cuentas que incumplan estas disposiciones.</p>

<h2>5. Seguridad</h2>
<p>El usuario es responsable de:</p>
<ul>
<li>Mantener confidencial su contraseña.</li>
<li>Activar y mantener el doble factor de autenticación.</li>
<li>Notificar cualquier acceso sospechoso.</li>
</ul>
<p>Relatic Panamá no se hace responsable por negligencia en la protección de credenciales.</p>

<h2>6. Costos y Renovación</h2>
<p>El otorgamiento inicial del correo puede estar subsidiado como parte de campañas institucionales.</p>
<p>Relatic Panamá podrá establecer en el futuro un cargo por gestión administrativa o mantenimiento del servicio, el cual será comunicado previamente.</p>

<h2>7. Modificaciones</h2>
<p>Relatic Panamá podrá actualizar esta política cuando lo considere necesario. Las modificaciones serán publicadas en el portal institucional.</p>
<p>El uso continuo del correo implica aceptación de las condiciones vigentes.</p>
"""


def ensure_policies_table():
    """Crear tablas policy y policy_acceptance si no existen y sembrar política de correo."""
    try:
        Policy.__table__.create(db.engine, checkfirst=True)
        PolicyAcceptance.__table__.create(db.engine, checkfirst=True)
        if Policy.query.filter_by(slug='politica-uso-correo-institucional').first() is None:
            p = Policy(
                title='Política de Uso de Correo Institucional',
                slug='politica-uso-correo-institucional',
                content=_politica_correo_institucional_html(),
                version='1.0',
                is_active=True,
            )
            db.session.add(p)
            db.session.commit()
            print('✅ Política de Uso de Correo Institucional insertada (v1.0).')
    except Exception as e:
        db.session.rollback()
        print(f'⚠️ ensure_policies_table: {e}')


def ensure_email_log_columns():
    """Asegurar que todas las columnas necesarias existan en la tabla email_log"""
    try:
        from sqlalchemy import inspect, text
        
        # Verificar si la tabla existe
        inspector = inspect(db.engine)
        if 'email_log' not in inspector.get_table_names():
            print("🔧 Tabla email_log no existe. Creándola...")
            # Crear la tabla usando el modelo
            EmailLog.__table__.create(db.engine, checkfirst=True)
            print("✅ Tabla email_log creada exitosamente con todas las columnas")
            return
        
        columns = [col['name'] for col in inspector.get_columns('email_log')]
        print(f"📋 Columnas actuales en email_log: {', '.join(columns)}")
        
        # Definir todas las columnas que debería tener según el modelo EmailLog
        required_columns = {
            'from_email': 'VARCHAR(200)',
            'recipient_id': 'INTEGER',
            'recipient_email': 'VARCHAR(120)',
            'recipient_name': 'VARCHAR(200)',
            'subject': 'VARCHAR(500)',
            'html_content': 'TEXT',
            'text_content': 'TEXT',
            'email_type': 'VARCHAR(50)',
            'related_entity_type': 'VARCHAR(50)',
            'related_entity_id': 'INTEGER',
            'status': 'VARCHAR(20)',
            'error_message': 'TEXT',
            'retry_count': 'INTEGER',
            'sent_at': 'DATETIME',
            'created_at': 'DATETIME'
        }
        
        # Agregar columnas faltantes
        added_columns = []
        for col_name, col_type in required_columns.items():
            if col_name not in columns:
                print(f"🔧 Agregando columna '{col_name}' ({col_type}) a la tabla email_log...")
                try:
                    with db.engine.connect() as conn:
                        conn.execute(text(f"ALTER TABLE email_log ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                    print(f"✅ Columna '{col_name}' agregada correctamente")
                    added_columns.append(col_name)
                except Exception as col_error:
                    print(f"⚠️ Error agregando columna '{col_name}': {col_error}")
        
        if added_columns:
            print(f"✅ Migración completada: {len(added_columns)} columnas agregadas: {', '.join(added_columns)}")
        else:
            print("✅ Todas las columnas necesarias ya existen en email_log")
        
    except Exception as e:
        print(f"⚠️ Error verificando columnas de email_log: {e}")
        import traceback
        traceback.print_exc()
        # No lanzar excepción para no bloquear el inicio de la app


def ensure_office365_discount_code_id():
    """Añadir columna discount_code_id a office365_request si no existe."""
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        if 'office365_request' not in inspector.get_table_names():
            return
        columns = [col['name'] for col in inspector.get_columns('office365_request')]
        if 'discount_code_id' in columns:
            return
        db.session.execute(text('ALTER TABLE office365_request ADD COLUMN discount_code_id INTEGER'))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        pass


def ensure_discount_code_valid_for_office365():
    """Añadir columna valid_for_office365 a discount_code si no existe."""
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        if 'discount_code' not in inspector.get_table_names():
            return
        columns = [col['name'] for col in inspector.get_columns('discount_code')]
        if 'valid_for_office365' in columns:
            return
        db.session.execute(text('ALTER TABLE discount_code ADD COLUMN valid_for_office365 BOOLEAN DEFAULT 0'))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        pass


def ensure_organization_settings():
    """Asegurar que exista la tabla organization_settings y al menos una fila con valores por defecto."""
    try:
        OrganizationSettings.__table__.create(db.engine, checkfirst=True)
        OrganizationSettings.get_settings()
    except Exception as e:
        print(f'⚠️ ensure_organization_settings: {e}')
        db.session.rollback()


def ensure_organization_settings_org_id_column():
    """Añadir organization_settings.organization_id (branding por empresa) y asociar fila legada a org 1."""
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        if 'organization_settings' not in inspector.get_table_names():
            return
        cols = [c['name'] for c in inspector.get_columns('organization_settings')]
        if 'organization_id' not in cols:
            db.session.execute(text(
                'ALTER TABLE organization_settings ADD COLUMN organization_id INTEGER REFERENCES saas_organization(id)'
            ))
            db.session.commit()
            print('✅ Columna organization_settings.organization_id añadida.')
        rows = OrganizationSettings.query.filter(OrganizationSettings.organization_id.is_(None)).order_by(
            OrganizationSettings.id.asc()
        ).all()
        if len(rows) == 1:
            rows[0].organization_id = 1
            db.session.commit()
        elif len(rows) > 1:
            keep = rows[0]
            keep.organization_id = 1
            for extra in rows[1:]:
                db.session.delete(extra)
            db.session.commit()
            print('✅ organization_settings: filas sin org consolidadas (se conservó la primera).')
    except Exception as e:
        db.session.rollback()
        print(f'⚠️ ensure_organization_settings_org_id_column: {e}')


def ensure_service_organization_id_column():
    """Añadir service.organization_id para filtrar catálogo por empresa (sesión)."""
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        if 'service' not in inspector.get_table_names():
            return
        cols = [c['name'] for c in inspector.get_columns('service')]
        if 'organization_id' not in cols:
            db.session.execute(text(
                'ALTER TABLE service ADD COLUMN organization_id INTEGER DEFAULT 1 REFERENCES saas_organization(id)'
            ))
            db.session.commit()
            db.session.execute(text('UPDATE service SET organization_id = 1 WHERE organization_id IS NULL'))
            db.session.commit()
            print('✅ Columna service.organization_id añadida.')
    except Exception as e:
        db.session.rollback()
        print(f'⚠️ ensure_service_organization_id_column: {e}')


def ensure_benefit_organization_id_column():
    """Añadir benefit.organization_id para no mezclar beneficios entre empresas."""
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        if 'benefit' not in inspector.get_table_names():
            return
        cols = [c['name'] for c in inspector.get_columns('benefit')]
        if 'organization_id' not in cols:
            db.session.execute(text(
                'ALTER TABLE benefit ADD COLUMN organization_id INTEGER DEFAULT 1 REFERENCES saas_organization(id)'
            ))
            db.session.commit()
            db.session.execute(text('UPDATE benefit SET organization_id = 1 WHERE organization_id IS NULL'))
            db.session.commit()
            print('✅ Columna benefit.organization_id añadida.')
    except Exception as e:
        db.session.rollback()
        print(f'⚠️ ensure_benefit_organization_id_column: {e}')


def ensure_membership_plan_organization_id_column():
    """Añadir membership_plan.organization_id (planes por empresa)."""
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        if 'membership_plan' not in inspector.get_table_names():
            return
        cols = [c['name'] for c in inspector.get_columns('membership_plan')]
        if 'organization_id' not in cols:
            db.session.execute(text(
                'ALTER TABLE membership_plan ADD COLUMN organization_id INTEGER DEFAULT 1 REFERENCES saas_organization(id)'
            ))
            db.session.commit()
            db.session.execute(text('UPDATE membership_plan SET organization_id = 1 WHERE organization_id IS NULL'))
            db.session.commit()
            print('✅ Columna membership_plan.organization_id añadida.')
    except Exception as e:
        db.session.rollback()
        print(f'⚠️ ensure_membership_plan_organization_id_column: {e}')


def ensure_certificate_event_organization_id_column():
    """certificate_events.organization_id (certificados por empresa)."""
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        if 'certificate_events' not in inspector.get_table_names():
            return
        cols = [c['name'] for c in inspector.get_columns('certificate_events')]
        if 'organization_id' not in cols:
            db.session.execute(text(
                'ALTER TABLE certificate_events ADD COLUMN organization_id INTEGER DEFAULT 1 REFERENCES saas_organization(id)'
            ))
            db.session.commit()
            db.session.execute(text('UPDATE certificate_events SET organization_id = 1 WHERE organization_id IS NULL'))
            db.session.commit()
            print('✅ Columna certificate_events.organization_id añadida.')
    except Exception as e:
        db.session.rollback()
        print(f'⚠️ ensure_certificate_event_organization_id_column: {e}')


def ensure_certificate_template_organization_id_column():
    """certificate_templates.organization_id."""
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        if 'certificate_templates' not in inspector.get_table_names():
            return
        cols = [c['name'] for c in inspector.get_columns('certificate_templates')]
        if 'organization_id' not in cols:
            db.session.execute(text(
                'ALTER TABLE certificate_templates ADD COLUMN organization_id INTEGER DEFAULT 1 REFERENCES saas_organization(id)'
            ))
            db.session.commit()
            db.session.execute(text('UPDATE certificate_templates SET organization_id = 1 WHERE organization_id IS NULL'))
            db.session.commit()
            print('✅ Columna certificate_templates.organization_id añadida.')
    except Exception as e:
        db.session.rollback()
        print(f'⚠️ ensure_certificate_template_organization_id_column: {e}')


def create_app():
    """
    Factory para WSGI (Gunicorn) y `nodeone.core.factory`.

    La instancia global `app` ya está construida al terminar de importar este módulo
    (rutas, blueprints, modelos). Aquí solo se aplican capas nodeone idempotentes.
    """
    from nodeone.core.config import load_config
    from nodeone.core.features import init_extensions

    load_config(app)
    init_extensions(app)
    return app


def bootstrap_nodeone_schema():
    """
    DDL / parches idempotentes antes de Gunicorn (bootstrap_nodeone.py, systemd ExecStartPre).
    Misma secuencia que el arranque de desarrollo sin levantar el servidor HTTP.
    """
    with app.app_context():
        db.create_all()
        ensure_must_change_password_column()
        ensure_email_log_columns()  # Asegurar columnas antes de crear datos de muestra
        ensure_benefit_icon_color_columns()
        ensure_canonical_saas_organization_usable()
        ensure_benefit_organization_id_column()
        ensure_membership_plan_organization_id_column()
        ensure_membership_plan_table()
        ensure_policies_table()
        ensure_organization_settings()
        ensure_organization_settings_org_id_column()
        ensure_service_organization_id_column()
        ensure_certificate_event_organization_id_column()
        ensure_certificate_template_organization_id_column()
        try:
            CertificateEvent.__table__.create(db.engine, checkfirst=True)
            Certificate.__table__.create(db.engine, checkfirst=True)
            CertificateTemplate.__table__.create(db.engine, checkfirst=True)
            try:
                db.session.execute(sql_text('ALTER TABLE certificate_events ADD COLUMN background_url VARCHAR(500)'))
                db.session.commit()
            except Exception:
                db.session.rollback()
            import certificate_routes as _cert_routes_mod

            for org in SaasOrganization.query.filter_by(is_active=True).all():
                _cert_routes_mod._seed_org_certificate_events(int(org.id))
        except Exception as e:
            print(f'⚠️ ensure_certificate_events: {e}')
        ensure_office365_discount_code_id()
        ensure_discount_code_valid_for_office365()
        create_sample_data()
        apply_email_config_from_db()


if __name__ == '__main__':
    bootstrap_nodeone_schema()
    port = int(os.environ.get('PORT', 9001))
    app.run(host='0.0.0.0', port=port, debug=True)
