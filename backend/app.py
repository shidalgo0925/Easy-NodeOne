#!/usr/bin/env python3
"""
Sistema de Membresía RelaticPanama
Backend Flask para gestión de usuarios y membresías
"""

import sys
import re
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, has_request_context, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import secrets
from functools import wraps

# Sistema de licencias (módulo independiente)
try:
    sys.path.insert(0, '/home/relaticpanama2025/.shh/license-system')
    from license_validator import LicenseValidator
    LICENSE_VALIDATOR = LicenseValidator('membresia-relatic')
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
        get_email_verification_email
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

# Ensure module alias 'app' points to this instance even when running as __main__
sys.modules.setdefault('app', sys.modules[__name__])
app.config['SECRET_KEY'] = secrets.token_hex(16)
# Usar ruta absoluta para la base de datos para evitar confusiones
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(os.path.dirname(basedir), 'instance', 'relaticpanama.db')
os.makedirs(os.path.dirname(db_path), exist_ok=True)  # Crear directorio instance/ si no existe
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
db = SQLAlchemy(app)
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
            # Reinicializar Mail con nueva configuración
            mail = Mail() if Mail else None
            mail.init_app(app)  # Inicializar correctamente Flask-Mail
            if EMAIL_TEMPLATES_AVAILABLE:
                email_service = EmailService(mail)
            print("✅ Configuración de email cargada desde base de datos")
        else:
            # Si no hay configuración en BD, usar variables de entorno o valores por defecto
            print("⚠️ No hay configuración de email en BD, usando variables de entorno")
            # Asegurar que mail esté inicializado
            if not mail:
                mail = Mail(app)
                mail.init_app(app)
            if EMAIL_TEMPLATES_AVAILABLE:
                if not email_service:
                    email_service = EmailService(mail)
    except Exception as e:
        print(f"⚠️ No se pudo cargar configuración de email desde BD: {e}")
        print("   Usando configuración por defecto o variables de entorno")
        import traceback
        traceback.print_exc()
        # Asegurar que mail esté inicializado incluso si falla
        if not mail:
            mail = Mail(app)
            mail.init_app(app)
        if EMAIL_TEMPLATES_AVAILABLE:
            if not email_service:
                email_service = EmailService(mail)
login_manager.login_view = 'login'
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

@app.before_request
def initialize_email_config():
    """Aplicar configuración de email al iniciar la aplicación (solo una vez)"""
    global _email_config_initialized
    if not _email_config_initialized:
        try:
            apply_email_config_from_db()
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

# Context processor para hacer get_system_logo disponible en todos los templates
@app.context_processor
def inject_logo():
    """Inyectar función para obtener logo en todos los templates"""
    return dict(get_system_logo=get_system_logo, datetime=datetime)

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
    """Decorador para requerir permisos de administrador"""
    from functools import wraps
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('No tienes permisos para acceder a esta página.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

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

# Modelos de la base de datos
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))
    country = db.Column(db.String(100))  # País del usuario
    cedula_or_passport = db.Column(db.String(20))  # Cédula o pasaporte
    tags = db.Column(db.String(500))  # Etiquetas separadas por comas
    user_group = db.Column(db.String(100))  # Grupo del usuario
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)  # Campo para administradores
    is_advisor = db.Column(db.Boolean, default=False)  # Campo para asesores que atienden citas
    
    # Verificación de email
    email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(100), unique=True, nullable=True)
    email_verification_token_expires = db.Column(db.DateTime, nullable=True)
    email_verification_sent_at = db.Column(db.DateTime, nullable=True)
    
    # Recuperación de contraseña
    password_reset_token = db.Column(db.String(100), unique=True, nullable=True)
    password_reset_token_expires = db.Column(db.DateTime, nullable=True)
    password_reset_sent_at = db.Column(db.DateTime, nullable=True)
    
    # Foto de perfil
    profile_picture = db.Column(db.String(500), nullable=True)  # Ruta a la imagen de perfil
    
    # Relación con membresías
    memberships = db.relationship('Membership', backref='user', lazy=True)
    
    def get_profile_picture_url(self):
        """Retorna la URL de la foto de perfil o una por defecto"""
        # Usar has_request_context para evitar errores fuera de contexto de Flask
        if has_request_context():
            if self.profile_picture:
                return url_for('static', filename=f'uploads/profiles/{self.profile_picture}', _external=False)
            return url_for('static', filename='images/default-avatar.png', _external=False)
        else:
            # Fuera del contexto de Flask, retornar ruta relativa
            if self.profile_picture:
                return f'/static/uploads/profiles/{self.profile_picture}'
            return '/static/images/default-avatar.png'
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_active_membership(self):
        """
        Obtener membresía activa del usuario.
        Los administradores siempre tienen acceso completo sin restricciones de planes.
        """
        # Los administradores tienen acceso completo, no necesitan membresía
        if hasattr(self, 'is_admin') and self.is_admin:
            # Retornar un objeto virtual que simula una membresía premium ilimitada
            # Esto permite que el código existente funcione sin cambios
            class AdminMembership:
                """Membresía virtual para administradores con acceso completo"""
                def __init__(self):
                    from datetime import timedelta
                    self.membership_type = 'admin'
                    self.status = 'active'
                    self.start_date = datetime.utcnow()
                    # Fecha muy lejana (100 años) para evitar problemas en templates
                    # pero técnicamente "ilimitada" para administradores
                    self.end_date = datetime.utcnow() + timedelta(days=36500)  # ~100 años
                    self.is_active = True
                    self.payment_status = 'paid'
                    self.amount = 0.0
                
                def is_currently_active(self):
                    return True
                
                def __bool__(self):
                    return True
                
                def __repr__(self):
                    return '<AdminMembership: Full Access>'
            
            return AdminMembership()
        
        # Para usuarios normales, buscar suscripción activa primero
        active_subscription = Subscription.query.filter_by(
            user_id=self.id, 
            status='active'
        ).filter(Subscription.end_date > datetime.utcnow()).first()
        
        if active_subscription:
            return active_subscription
        
        # Fallback al sistema anterior si existe
        return Membership.query.filter_by(user_id=self.id, is_active=True).first()


class SocialAuth(db.Model):
    """Vinculación de usuario con proveedor OAuth (Google, Facebook, LinkedIn)."""
    __tablename__ = 'social_auth'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    provider = db.Column(db.String(50), nullable=False)  # google, facebook, linkedin
    provider_user_id = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('provider', 'provider_user_id', name='uq_social_provider_user'),)


class Membership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    membership_type = db.Column(db.String(50), nullable=False)  # 'basic', 'pro', 'premium', 'deluxe', 'corporativo'
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    payment_status = db.Column(db.String(20), default='pending')  # 'pending', 'paid', 'failed'
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def is_currently_active(self):
        """Verificar si la membresía está actualmente activa"""
        return self.is_active and datetime.utcnow() <= self.end_date

class Benefit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    membership_type = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Método de pago y referencia
    payment_method = db.Column(db.String(50), nullable=False)  # stripe, paypal, banco_general, yappy
    payment_reference = db.Column(db.String(200))  # ID de transacción del proveedor (stripe_payment_intent_id, paypal_order_id, etc.)
    
    # Información del pago
    amount = db.Column(db.Integer, nullable=False)  # Amount in cents
    currency = db.Column(db.String(3), default='usd')
    status = db.Column(db.String(20), default='pending')  # pending, awaiting_confirmation, succeeded, failed, cancelled
    
    # Información adicional
    membership_type = db.Column(db.String(50), nullable=False)  # 'cart' para pagos del carrito, o tipo específico
    payment_url = db.Column(db.String(500))  # URL para pagos externos (PayPal, Banco General, etc.)
    receipt_url = db.Column(db.String(500))  # URL del comprobante subido por el usuario
    receipt_filename = db.Column(db.String(255))  # Nombre del archivo del comprobante
    
    # OCR y verificación
    ocr_data = db.Column(db.Text)  # JSON con datos extraídos por OCR
    ocr_status = db.Column(db.String(20), default='pending')  # pending, verified, rejected, needs_review
    ocr_verified_at = db.Column(db.DateTime)  # Fecha de verificación OCR
    admin_notes = db.Column(db.Text)  # Notas del administrador
    
    # Metadata adicional (JSON) - usando payment_metadata porque metadata es reservado en SQLAlchemy
    payment_metadata = db.Column(db.Text)  # JSON con información adicional del pago
    
    # Fechas
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    paid_at = db.Column(db.DateTime)  # Fecha cuando se confirmó el pago
    
    user = db.relationship('User', backref=db.backref('payments', lazy=True))
    
    def to_dict(self):
        """Convertir a diccionario para JSON"""
        import json
        return {
            'id': self.id,
            'user_id': self.user_id,
            'payment_method': self.payment_method,
            'payment_reference': self.payment_reference,
            'amount': self.amount,
            'currency': self.currency,
            'status': self.status,
            'membership_type': self.membership_type,
            'payment_url': self.payment_url,
            'receipt_url': self.receipt_url,
            'receipt_filename': self.receipt_filename,
            'ocr_data': json.loads(self.ocr_data) if self.ocr_data else None,
            'ocr_status': self.ocr_status,
            'ocr_verified_at': self.ocr_verified_at.isoformat() if self.ocr_verified_at else None,
            'admin_notes': self.admin_notes,
            'metadata': json.loads(self.payment_metadata) if self.payment_metadata else {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None
        }

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'), nullable=False)
    membership_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='active')  # active, expired, cancelled
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    auto_renew = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('subscriptions', lazy=True))
    payment = db.relationship('Payment', backref=db.backref('subscription', uselist=False))
    
    def is_currently_active(self):
        """Verificar si la suscripción está actualmente activa"""
        return self.status == 'active' and datetime.utcnow() <= self.end_date
    
    @property
    def is_active(self):
        """Propiedad para compatibilidad con Membership"""
        return self.is_currently_active()

# Modelos de Eventos
class Event(db.Model):
    """Modelo para eventos según el diagrama de flujo - 5 pasos: Evento, Descripción, Publicidad, Certificado, Kahoot"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    summary = db.Column(db.Text)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), default='general')
    format = db.Column(db.String(50), default='virtual')  # virtual, presencial, híbrido
    tags = db.Column(db.String(500))
    base_price = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='USD')
    registration_url = db.Column(db.String(500))
    contact_email = db.Column(db.String(120))
    contact_phone = db.Column(db.String(20))
    location = db.Column(db.String(200))
    country = db.Column(db.String(100))
    # Campos adicionales según diagrama
    venue = db.Column(db.String(200))  # Sede o Universidad
    university = db.Column(db.String(200))  # Universidad organizadora
    is_virtual = db.Column(db.Boolean, default=False)
    has_certificate = db.Column(db.Boolean, default=False)
    certificate_instructions = db.Column(db.Text)
    certificate_template = db.Column(db.String(500))  # Template del certificado
    # Integración Kahoot
    kahoot_enabled = db.Column(db.Boolean, default=False)
    kahoot_link = db.Column(db.String(500))
    kahoot_required = db.Column(db.Boolean, default=False)  # Si es obligatorio participar
    # Flujo de 5 pasos
    step_1_event_completed = db.Column(db.Boolean, default=False)  # 1. Evento
    step_2_description_completed = db.Column(db.Boolean, default=False)  # 2. Descripción
    step_3_publicity_completed = db.Column(db.Boolean, default=False)  # 3. Publicidad
    step_4_certificate_completed = db.Column(db.Boolean, default=False)  # 4. Certificado
    step_5_kahoot_completed = db.Column(db.Boolean, default=False)  # 5. Kahoot
    # Salidas del evento (Carteles, Revistas, Libros)
    generates_poster = db.Column(db.Boolean, default=False)
    generates_magazine = db.Column(db.Boolean, default=False)
    generates_book = db.Column(db.Boolean, default=False)
    # Capacidad y registro
    capacity = db.Column(db.Integer, default=0)
    registered_count = db.Column(db.Integer, default=0)
    visibility = db.Column(db.String(20), default='members')  # members, public
    publish_status = db.Column(db.String(20), default='draft')  # draft, published, archived
    featured = db.Column(db.Boolean, default=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    registration_deadline = db.Column(db.DateTime)
    cover_image = db.Column(db.String(500))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    # Roles del evento: Moderador, Administrador, Expositor
    moderator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Moderador del evento
    administrator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Administrador del evento
    speaker_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Expositor/Conferencista principal
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    images = db.relationship('EventImage', backref='event', lazy=True, cascade='all, delete-orphan')
    discounts = db.relationship('EventDiscount', backref='event', lazy=True, cascade='all, delete-orphan')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_events')
    moderator = db.relationship('User', foreign_keys=[moderator_id], backref='moderated_events')
    administrator = db.relationship('User', foreign_keys=[administrator_id], backref='administered_events')
    speaker = db.relationship('User', foreign_keys=[speaker_id], backref='speaker_events')
    
    def get_notification_recipients(self):
        """Obtiene todos los usuarios que deben recibir notificaciones del evento"""
        recipients = []
        
        # Creador del evento
        if self.created_by:
            creator = User.query.get(self.created_by)
            if creator:
                recipients.append(creator)
        
        # Moderador
        if self.moderator_id:
            moderator = User.query.get(self.moderator_id)
            if moderator and moderator not in recipients:
                recipients.append(moderator)
        
        # Administrador del evento
        if self.administrator_id:
            administrator = User.query.get(self.administrator_id)
            if administrator and administrator not in recipients:
                recipients.append(administrator)
        
        # Expositor
        if self.speaker_id:
            speaker = User.query.get(self.speaker_id)
            if speaker and speaker not in recipients:
                recipients.append(speaker)
        
        # Si no hay roles asignados, notificar a todos los administradores del sistema
        if not recipients:
            admins = User.query.filter_by(is_admin=True).all()
            recipients.extend(admins)
        
        return recipients
    
    def cover_url(self):
        """Retorna la URL de la imagen de portada"""
        if self.cover_image:
            return self.cover_image
        return '/static/images/default-event.jpg'
    
    def pricing_for_membership(self, membership_type=None):
        """Calcula el precio final según el tipo de membresía"""
        base_price = self.base_price or 0.0
        discount = None
        final_price = base_price
        
        if membership_type:
            # Buscar descuento aplicable para este tipo de membresía
            event_discount = EventDiscount.query.join(Discount).filter(
                EventDiscount.event_id == self.id,
                Discount.membership_tier == membership_type,
                Discount.is_active == True
            ).order_by(EventDiscount.priority.asc()).first()
            
            if event_discount:
                discount = event_discount.discount
                if discount.discount_type == 'percentage':
                    final_price = base_price * (1 - discount.value / 100)
                elif discount.discount_type == 'fixed':
                    final_price = max(0, base_price - discount.value)
        
        return {
            'base_price': base_price,
            'final_price': final_price,
            'discount': discount
        }

class EventImage(db.Model):
    """Imágenes de galería para eventos"""
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    is_primary = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Discount(db.Model):
    """Descuentos reutilizables - Sistema de descuentos por categorías según diagrama:
    Básico (Ba), Pro 10%, R 20%, DX 30%"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True)
    description = db.Column(db.Text)
    discount_type = db.Column(db.String(20), default='percentage')  # percentage, fixed
    value = db.Column(db.Float, nullable=False)
    membership_tier = db.Column(db.String(50))  # basic, pro, premium, deluxe, r, dx
    category = db.Column(db.String(50), default='event')  # event, appointment, service
    applies_automatically = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    is_master = db.Column(db.Boolean, default=False)  # Descuento maestro global
    max_uses = db.Column(db.Integer)
    uses = db.Column(db.Integer, default=0)  # Alias para compatibilidad con esquema antiguo
    current_uses = db.Column(db.Integer, default=0)  # Contador de usos
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación con eventos y citas
    events = db.relationship('EventDiscount', backref='discount', lazy=True)
    
    def can_use(self):
        """Verifica si el descuento puede ser usado"""
        if not self.is_active:
            return False
        # Usar current_uses como fuente de verdad, con fallback a uses
        uses_count = self.current_uses if hasattr(self, 'current_uses') and self.current_uses is not None else (self.uses if hasattr(self, 'uses') and self.uses is not None else 0)
        if self.max_uses and uses_count >= self.max_uses:
            return False
        now = datetime.utcnow()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True

class EventDiscount(db.Model):
    """Relación muchos a muchos entre eventos y descuentos"""
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    discount_id = db.Column(db.Integer, db.ForeignKey('discount.id'), nullable=False)
    priority = db.Column(db.Integer, default=1)  # Orden de aplicación si hay múltiples
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class DiscountCode(db.Model):
    """Códigos promocionales que los usuarios introducen manualmente"""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Tipo y valor del descuento
    discount_type = db.Column(db.String(20), default='percentage')  # percentage, fixed
    value = db.Column(db.Float, nullable=False)
    
    # Alcance del descuento
    applies_to = db.Column(db.String(50), default='all')  # all, events, memberships, appointments
    event_ids = db.Column(db.Text)  # JSON array de event IDs (opcional)
    
    # Vigencia
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    
    # Límites de uso
    max_uses_total = db.Column(db.Integer)  # Límite total de usos
    max_uses_per_user = db.Column(db.Integer, default=1)  # Límite por usuario
    current_uses = db.Column(db.Integer, default=0)
    
    # Estado
    is_active = db.Column(db.Boolean, default=True)
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_discount_codes')
    applications = db.relationship('DiscountApplication', backref='discount_code', lazy=True, cascade='all, delete-orphan')
    
    def can_use(self, user_id=None):
        """Verifica si el código puede ser usado por un usuario"""
        if not self.is_active:
            return False, "Este código de descuento no está activo"
        
        # Verificar vigencia
        now = datetime.utcnow()
        if self.start_date and now < self.start_date:
            return False, f"Este código será válido a partir del {self.start_date.strftime('%d/%m/%Y')}"
        if self.end_date and now > self.end_date:
            return False, "Este código de descuento ha expirado"
        
        # Verificar límite total
        if self.max_uses_total and self.current_uses >= self.max_uses_total:
            return False, "Este código ha alcanzado su límite de usos"
        
        # Verificar límite por usuario
        if user_id and self.max_uses_per_user:
            user_uses = DiscountApplication.query.filter_by(
                discount_code_id=self.id,
                user_id=user_id
            ).count()
            if user_uses >= self.max_uses_per_user:
                return False, f"Ya has usado este código el máximo de veces permitidas ({self.max_uses_per_user})"
        
        return True, "Código válido"
    
    def apply_discount(self, amount):
        """Aplica el descuento a un monto"""
        if self.discount_type == 'percentage':
            return amount * (self.value / 100)
        elif self.discount_type == 'fixed':
            return min(self.value, amount)  # No puede ser mayor que el monto
        return 0


class DiscountApplication(db.Model):
    """Historial de aplicación de códigos de descuento"""
    id = db.Column(db.Integer, primary_key=True)
    discount_code_id = db.Column(db.Integer, db.ForeignKey('discount_code.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'), nullable=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=True)
    
    # Montos
    original_amount = db.Column(db.Float, nullable=False)  # Monto original
    discount_amount = db.Column(db.Float, nullable=False)  # Monto descontado
    final_amount = db.Column(db.Float, nullable=False)  # Monto final
    
    # Metadata
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    user = db.relationship('User', backref='discount_applications')
    payment = db.relationship('Payment', backref='discount_applications')
    cart = db.relationship('Cart', backref='discount_applications')


# ---------------------------------------------------------------------------
# Modelos adicionales para eventos según el diagrama de flujo
# ---------------------------------------------------------------------------
class EventParticipant(db.Model):
    """Participantes de eventos con categorías (participantes, asistentes, ponentes)"""
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    participation_category = db.Column(db.String(50), nullable=False)  # participant, attendee, speaker
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    check_in_time = db.Column(db.DateTime)  # Hora de llegada/check-in
    check_out_time = db.Column(db.DateTime)  # Hora de salida/check-out
    attendance_confirmed = db.Column(db.Boolean, default=False)
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid, refunded
    payment_amount = db.Column(db.Float, default=0.0)
    discount_applied = db.Column(db.Float, default=0.0)
    membership_type_at_registration = db.Column(db.String(50))  # Para aplicar descuentos históricos
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    event = db.relationship('Event', backref='participants')
    user = db.relationship('User', backref='event_participations')
    
    __table_args__ = (
        db.UniqueConstraint('event_id', 'user_id', name='uq_event_user'),
    )


class EventSpeaker(db.Model):
    """Ponentes/Exponentes de eventos"""
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Puede ser externo
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120))
    bio = db.Column(db.Text)
    photo_url = db.Column(db.String(500))
    organization = db.Column(db.String(200))  # Sede o Universidad
    country = db.Column(db.String(100))
    title = db.Column(db.String(200))  # Título de la presentación
    topic_description = db.Column(db.Text)  # Información del tema
    presentation_time = db.Column(db.DateTime)  # Hora de la presentación
    duration_minutes = db.Column(db.Integer, default=30)
    sort_order = db.Column(db.Integer, default=0)
    is_confirmed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    event = db.relationship('Event', backref='speakers')
    user = db.relationship('User', backref='speaker_appearances')


class EventCertificate(db.Model):
    """Certificados generados para participantes de eventos"""
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    participant_id = db.Column(db.Integer, db.ForeignKey('event_participant.id'), nullable=False)
    certificate_number = db.Column(db.String(100), unique=True, nullable=False)
    certificate_url = db.Column(db.String(500))  # URL del PDF generado
    preview_url = db.Column(db.String(500))  # URL del preview
    issued_date = db.Column(db.DateTime, default=datetime.utcnow)
    issued_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # Admin que emitió
    email_sent = db.Column(db.Boolean, default=False)
    email_sent_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    event = db.relationship('Event', backref='certificates')
    participant = db.relationship('EventParticipant', backref='certificates')
    issuer = db.relationship('User', backref='certificates_issued')


class EventWorkshop(db.Model):
    """Talleres dentro de eventos"""
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    instructor_name = db.Column(db.String(200))  # Si es externo
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200))  # Sala, link virtual, etc.
    capacity = db.Column(db.Integer, default=0)
    registered_count = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, default=0.0)
    is_included = db.Column(db.Boolean, default=True)  # Si está incluido en el evento
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    event = db.relationship('Event', backref='workshops')
    instructor = db.relationship('User', backref='workshops_taught')


class EventTopic(db.Model):
    """Temas/Presentaciones de eventos"""
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    speaker_id = db.Column(db.Integer, db.ForeignKey('event_speaker.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    topic_type = db.Column(db.String(50))  # presentation, panel, keynote, etc.
    start_time = db.Column(db.DateTime)
    duration_minutes = db.Column(db.Integer, default=30)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    event = db.relationship('Event', backref='topics')
    speaker = db.relationship('EventSpeaker', backref='topics')


class Notification(db.Model):
    """Sistema de notificaciones para eventos y movimientos del sistema"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=True)  # NULL si no es relacionado a evento
    notification_type = db.Column(db.String(50), nullable=False)  # event_registration, event_cancellation, event_confirmation, event_update, etc.
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    email_sent = db.Column(db.Boolean, default=False)
    email_sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    user = db.relationship('User', backref='notifications')
    event = db.relationship('Event', backref='notifications')
    
    def mark_as_read(self):
        """Marcar notificación como leída"""
        self.is_read = True
        # Commit removido - se hace en el endpoint


class EmailLog(db.Model):
    """Registro completo de todos los emails enviados por el sistema"""
    id = db.Column(db.Integer, primary_key=True)
    from_email = db.Column(db.String(200))  # Email del remitente
    to_email = db.Column(db.String(120), nullable=False)  # Email del destinatario (campo legacy, sinónimo de recipient_email)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # NULL si es email externo
    recipient_email = db.Column(db.String(120), nullable=False)  # Email del destinatario
    recipient_name = db.Column(db.String(200))  # Nombre del destinatario
    subject = db.Column(db.String(500), nullable=False)
    html_content = db.Column(db.Text)  # Contenido HTML del email
    text_content = db.Column(db.Text)  # Contenido de texto plano
    email_type = db.Column(db.String(50), nullable=False)  # membership_payment, event_registration, appointment_confirmation, etc.
    related_entity_type = db.Column(db.String(50))  # membership, event, appointment, payment, etc.
    related_entity_id = db.Column(db.Integer)  # ID de la entidad relacionada
    status = db.Column(db.String(20), default='sent')  # sent, failed, pending
    error_message = db.Column(db.Text)  # Mensaje de error si falló
    retry_count = db.Column(db.Integer, default=0)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    recipient = db.relationship('User', backref='email_logs', foreign_keys=[recipient_id])
    
    def to_dict(self):
        """Convertir a diccionario para JSON"""
        return {
            'id': self.id,
            'recipient_email': self.recipient_email,
            'recipient_name': self.recipient_name,
            'subject': self.subject,
            'email_type': self.email_type,
            'related_entity_type': self.related_entity_type,
            'related_entity_id': self.related_entity_id,
            'status': self.status,
            'retry_count': self.retry_count,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class EmailConfig(db.Model):
    """Configuración del servidor de correo SMTP"""
    id = db.Column(db.Integer, primary_key=True)
    mail_server = db.Column(db.String(200), nullable=False, default='smtp.gmail.com')
    mail_port = db.Column(db.Integer, nullable=False, default=587)
    mail_use_tls = db.Column(db.Boolean, default=True)
    mail_use_ssl = db.Column(db.Boolean, default=False)
    mail_username = db.Column(db.String(200))  # Se puede dejar vacío si se usa variable de entorno
    mail_password = db.Column(db.String(500))  # Encriptado o en variable de entorno
    mail_default_sender = db.Column(db.String(200), nullable=False, default='noreply@relaticpanama.org')
    use_environment_variables = db.Column(db.Boolean, default=True)  # Si usa vars de entorno o BD
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def get_active_config():
        """Obtener la configuración activa de email"""
        return EmailConfig.query.filter_by(is_active=True).first()
    
    def to_dict(self):
        """Convertir a diccionario para JSON (sin password)"""
        return {
            'id': self.id,
            'mail_server': self.mail_server,
            'mail_port': self.mail_port,
            'mail_use_tls': self.mail_use_tls,
            'mail_use_ssl': self.mail_use_ssl,
            'mail_username': self.mail_username if not self.use_environment_variables else '[Desde variables de entorno]',
            'mail_default_sender': self.mail_default_sender,
            'use_environment_variables': self.use_environment_variables,
            'is_active': self.is_active,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def apply_to_app(self, app_instance):
        """Aplicar esta configuración a la instancia de Flask"""
        if self.use_environment_variables:
            # Usar variables de entorno si está configurado así
            app_instance.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', self.mail_server)
            app_instance.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', self.mail_port))
            app_instance.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
            app_instance.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
            app_instance.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', self.mail_username or '')
            app_instance.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', self.mail_password or '')
            app_instance.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', self.mail_default_sender)
        else:
            # Usar valores de la base de datos
            app_instance.config['MAIL_SERVER'] = self.mail_server
            app_instance.config['MAIL_PORT'] = self.mail_port
            app_instance.config['MAIL_USE_TLS'] = self.mail_use_tls
            app_instance.config['MAIL_USE_SSL'] = self.mail_use_ssl
            app_instance.config['MAIL_USERNAME'] = self.mail_username
            app_instance.config['MAIL_PASSWORD'] = self.mail_password
            app_instance.config['MAIL_DEFAULT_SENDER'] = self.mail_default_sender

class PaymentConfig(db.Model):
    """Configuración de métodos de pago"""
    id = db.Column(db.Integer, primary_key=True)
    
    # Stripe
    stripe_secret_key = db.Column(db.String(500))
    stripe_publishable_key = db.Column(db.String(500))
    stripe_webhook_secret = db.Column(db.String(500))
    
    # PayPal
    paypal_client_id = db.Column(db.String(500))
    paypal_client_secret = db.Column(db.String(500))
    paypal_mode = db.Column(db.String(20), default='sandbox')  # sandbox o live
    paypal_return_url = db.Column(db.String(500))
    paypal_cancel_url = db.Column(db.String(500))
    
    # Banco General (CyberSource)
    banco_general_merchant_id = db.Column(db.String(200))
    banco_general_api_key = db.Column(db.String(500))
    banco_general_shared_secret = db.Column(db.String(500))
    banco_general_api_url = db.Column(db.String(500), default='https://api.cybersource.com')
    
    # Yappy
    yappy_api_key = db.Column(db.String(500))
    yappy_merchant_id = db.Column(db.String(200))
    yappy_api_url = db.Column(db.String(500), default='https://api.yappy.im')
    
    # Configuración general
    use_environment_variables = db.Column(db.Boolean, default=True)  # Si usa vars de entorno o BD
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convertir a diccionario para JSON (sin secrets)"""
        return {
            'id': self.id,
            'stripe_publishable_key': self.stripe_publishable_key if not self.use_environment_variables else '[Desde variables de entorno]',
            'paypal_mode': self.paypal_mode,
            'paypal_return_url': self.paypal_return_url,
            'paypal_cancel_url': self.paypal_cancel_url,
            'banco_general_merchant_id': self.banco_general_merchant_id if not self.use_environment_variables else '[Desde variables de entorno]',
            'banco_general_api_url': self.banco_general_api_url,
            'yappy_merchant_id': self.yappy_merchant_id if not self.use_environment_variables else '[Desde variables de entorno]',
            'yappy_api_url': self.yappy_api_url,
            'use_environment_variables': self.use_environment_variables,
            'is_active': self.is_active,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def get_active_config():
        """Obtener la configuración activa de pagos"""
        return PaymentConfig.query.filter_by(is_active=True).first()
    
    def get_stripe_secret_key(self):
        """Obtener Stripe secret key (de BD o variable de entorno)"""
        if self.use_environment_variables:
            return os.getenv('STRIPE_SECRET_KEY', '')
        return self.stripe_secret_key or ''
    
    def get_stripe_publishable_key(self):
        """Obtener Stripe publishable key"""
        if self.use_environment_variables:
            return os.getenv('STRIPE_PUBLISHABLE_KEY', '')
        return self.stripe_publishable_key or ''
    
    def get_paypal_client_id(self):
        """Obtener PayPal Client ID"""
        if self.use_environment_variables:
            return os.getenv('PAYPAL_CLIENT_ID', '')
        return self.paypal_client_id or ''
    
    def get_paypal_client_secret(self):
        """Obtener PayPal Client Secret"""
        if self.use_environment_variables:
            return os.getenv('PAYPAL_CLIENT_SECRET', '')
        return self.paypal_client_secret or ''
    
    def get_banco_general_merchant_id(self):
        """Obtener Banco General Merchant ID"""
        if self.use_environment_variables:
            return os.getenv('BANCO_GENERAL_MERCHANT_ID', '')
        return self.banco_general_merchant_id or ''
    
    def get_banco_general_api_key(self):
        """Obtener Banco General API Key"""
        if self.use_environment_variables:
            return os.getenv('BANCO_GENERAL_API_KEY', '')
        return self.banco_general_api_key or ''
    
    def get_yappy_api_key(self):
        """Obtener Yappy API Key"""
        if self.use_environment_variables:
            return os.getenv('YAPPY_API_KEY', '')
        return self.yappy_api_key or ''

class MediaConfig(db.Model):
    """Configuración de URLs de videos y audios para guías visuales"""
    id = db.Column(db.Integer, primary_key=True)
    
    # Identificador del procedimiento y paso
    procedure_key = db.Column(db.String(100), nullable=False)  # 'register', 'membership', etc.
    step_number = db.Column(db.Integer, nullable=False)  # 1, 2, 3, etc.
    
    # URLs de multimedia
    video_url = db.Column(db.String(500))  # URL del video
    audio_url = db.Column(db.String(500))  # URL del audio
    
    # Metadatos
    step_title = db.Column(db.String(200))  # Título del paso (para referencia)
    description = db.Column(db.Text)  # Descripción opcional
    
    # Control
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convertir a diccionario"""
        return {
            'id': self.id,
            'procedure_key': self.procedure_key,
            'step_number': self.step_number,
            'video_url': self.video_url,
            'audio_url': self.audio_url,
            'step_title': self.step_title,
            'description': self.description,
            'is_active': self.is_active
        }
    
    @staticmethod
    def get_all_configs():
        """Obtener todas las configuraciones activas"""
        return MediaConfig.query.filter_by(is_active=True).order_by(
            MediaConfig.procedure_key, MediaConfig.step_number
        ).all()
    
    @staticmethod
    def get_procedure_configs(procedure_key):
        """Obtener configuraciones de un procedimiento específico"""
        return MediaConfig.query.filter_by(
            procedure_key=procedure_key, 
            is_active=True
        ).order_by(MediaConfig.step_number).all()
    
    @staticmethod
    def get_config(procedure_key, step_number):
        """Obtener configuración específica"""
        return MediaConfig.query.filter_by(
            procedure_key=procedure_key,
            step_number=step_number,
            is_active=True
        ).first()

class EmailTemplate(db.Model):
    """Templates de correo editables desde el panel de administración"""
    id = db.Column(db.Integer, primary_key=True)
    template_key = db.Column(db.String(100), unique=True, nullable=True)  # welcome, membership_payment, etc. (nullable para compatibilidad con registros antiguos)
    name = db.Column(db.String(200), nullable=False)  # Nombre descriptivo
    subject = db.Column(db.String(500), nullable=False)  # Asunto del correo
    html_content = db.Column(db.Text, nullable=False)  # Contenido HTML
    text_content = db.Column(db.Text)  # Contenido de texto plano (opcional)
    category = db.Column(db.String(50))  # membership, event, appointment, system
    is_custom = db.Column(db.Boolean, default=False)  # Si es personalizado o usa el template por defecto
    variables = db.Column(db.Text)  # JSON con variables disponibles para este template
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convertir a diccionario para JSON"""
        return {
            'id': self.id,
            'template_key': self.template_key,
            'name': self.name,
            'subject': self.subject,
            'html_content': self.html_content,
            'text_content': self.text_content,
            'category': self.category,
            'is_custom': self.is_custom,
            'variables': self.variables,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def get_template(template_key):
        """Obtener template personalizado o None si usa el por defecto"""
        template = EmailTemplate.query.filter_by(template_key=template_key, is_custom=True).first()
        return template


class NotificationSettings(db.Model):
    """Configuración de notificaciones del sistema - permite activar/desactivar cada tipo"""
    id = db.Column(db.Integer, primary_key=True)
    notification_type = db.Column(db.String(50), unique=True, nullable=False)  # welcome, membership_payment, etc.
    name = db.Column(db.String(200), nullable=False)  # Nombre descriptivo
    description = db.Column(db.Text)  # Descripción de qué hace esta notificación
    enabled = db.Column(db.Boolean, default=True)  # Si está habilitada o no
    category = db.Column(db.String(50))  # membership, event, appointment, system
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convertir a diccionario para JSON"""
        return {
            'id': self.id,
            'notification_type': self.notification_type,
            'name': self.name,
            'description': self.description,
            'enabled': self.enabled,
            'category': self.category,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def is_enabled(notification_type):
        """Verificar si un tipo de notificación está habilitado"""
        setting = NotificationSettings.query.filter_by(notification_type=notification_type).first()
        # Si no existe la configuración, por defecto está habilitada (comportamiento actual)
        return setting.enabled if setting else True
    
    @staticmethod
    def get_all_settings():
        """Obtener todas las configuraciones agrupadas por categoría"""
        settings = NotificationSettings.query.order_by(NotificationSettings.category, NotificationSettings.name).all()
        result = {}
        for setting in settings:
            if setting.category not in result:
                result[setting.category] = []
            result[setting.category].append(setting.to_dict())
        return result


class EventRegistration(db.Model):
    """Registro completo de eventos con flujo de email y almacenamiento"""
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    registration_status = db.Column(db.String(20), default='pending')  # pending, confirmed, cancelled, completed
    # Flujo de emails
    confirmation_email_sent = db.Column(db.Boolean, default=False)
    confirmation_email_sent_at = db.Column(db.DateTime)
    reminder_email_sent = db.Column(db.Boolean, default=False)
    reminder_email_sent_at = db.Column(db.DateTime)
    certificate_email_sent = db.Column(db.Boolean, default=False)
    certificate_email_sent_at = db.Column(db.DateTime)
    # Integración Kahoot
    kahoot_link = db.Column(db.String(500))
    kahoot_participated = db.Column(db.Boolean, default=False)
    kahoot_score = db.Column(db.Integer)
    # Descuentos aplicados
    base_price = db.Column(db.Float, default=0.0)
    discount_applied = db.Column(db.Float, default=0.0)
    final_price = db.Column(db.Float, default=0.0)
    membership_type = db.Column(db.String(50))
    discount_code_used = db.Column(db.String(50))
    # Pagos
    payment_status = db.Column(db.String(20), default='pending')
    payment_method = db.Column(db.String(50))
    payment_reference = db.Column(db.String(100))
    payment_date = db.Column(db.DateTime)
    # Datos adicionales
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    event = db.relationship('Event', backref='registrations')
    user = db.relationship('User', backref='event_registrations')
    
    __table_args__ = (
        db.UniqueConstraint('event_id', 'user_id', name='uq_event_registration'),
    )


# ---------------------------------------------------------------------------
# Modelos de Citas / Appointments
# ---------------------------------------------------------------------------
class Advisor(db.Model):
    """Perfil de asesores internos que atienden citas."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    headline = db.Column(db.String(120))
    bio = db.Column(db.Text)
    specializations = db.Column(db.Text)
    meeting_url = db.Column(db.String(255))
    photo_url = db.Column(db.String(255))
    average_response_time = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('advisor_profile', uselist=False))
    advisor_assignments = db.relationship('AppointmentAdvisor', backref='advisor', lazy=True, cascade='all, delete-orphan')
    availability = db.relationship('AdvisorAvailability', backref='advisor', lazy=True, cascade='all, delete-orphan')
    slots = db.relationship('AppointmentSlot', backref='advisor', lazy=True, cascade='all, delete-orphan')
    appointments = db.relationship('Appointment', backref='advisor_profile', lazy=True)


class AppointmentType(db.Model):
    """Servicios configurables que pueden reservar los miembros."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    service_category = db.Column(db.String(100))
    duration_minutes = db.Column(db.Integer, default=60)
    is_group_allowed = db.Column(db.Boolean, default=False)
    max_participants = db.Column(db.Integer, default=1)
    base_price = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='USD')
    is_virtual = db.Column(db.Boolean, default=True)
    requires_confirmation = db.Column(db.Boolean, default=True)
    color_tag = db.Column(db.String(20), default='#0d6efd')
    icon = db.Column(db.String(50), default='fa-calendar-check')
    display_order = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    advisor_assignments = db.relationship('AppointmentAdvisor', backref='appointment_type', lazy=True, cascade='all, delete-orphan')
    pricing_rules = db.relationship('AppointmentPricing', backref='appointment_type', lazy=True, cascade='all, delete-orphan')
    slots = db.relationship('AppointmentSlot', backref='appointment_type', lazy=True, cascade='all, delete-orphan')
    appointments = db.relationship('Appointment', backref='appointment_type', lazy=True)

    def duration(self):
        return timedelta(minutes=self.duration_minutes or 60)

    def pricing_for_membership(self, membership_type=None):
        """Calcula el precio final considerando reglas por membresía."""
        base_price = self.base_price or 0.0
        final_price = base_price
        discount_percentage = 0.0
        is_included = False
        rule = None

        if membership_type:
            rule = AppointmentPricing.query.filter_by(
                appointment_type_id=self.id,
                membership_type=membership_type,
                is_active=True
            ).first()

        if rule:
            if rule.is_included:
                final_price = 0.0
                is_included = True
            elif rule.price is not None:
                final_price = rule.price
            elif rule.discount_percentage:
                discount_percentage = rule.discount_percentage
                final_price = max(0.0, base_price * (1 - discount_percentage / 100))

        return {
            'base_price': base_price,
            'final_price': final_price,
            'discount_percentage': discount_percentage,
            'is_included': is_included,
            'rule': rule
        }


class AppointmentAdvisor(db.Model):
    """Asignación de asesores a tipos de cita."""
    id = db.Column(db.Integer, primary_key=True)
    appointment_type_id = db.Column(db.Integer, db.ForeignKey('appointment_type.id'), nullable=False)
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisor.id'), nullable=False)
    priority = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('appointment_type_id', 'advisor_id', name='uq_type_advisor'),
    )


class AdvisorAvailability(db.Model):
    """Bloques semanales de disponibilidad declarados por cada asesor."""
    id = db.Column(db.Integer, primary_key=True)
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisor.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0 = lunes ... 6 = domingo
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    timezone = db.Column(db.String(50), default='America/Panama')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.CheckConstraint('end_time > start_time', name='ck_availability_time_window'),
    )


class AdvisorServiceAvailability(db.Model):
    """
    Horarios de disponibilidad de asesores por servicio/tipo de cita.
    Permite configurar horarios específicos para cada combinación asesor-servicio.
    Similar al Schedule Tab de Odoo.
    """
    id = db.Column(db.Integer, primary_key=True)
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisor.id'), nullable=False)
    appointment_type_id = db.Column(db.Integer, db.ForeignKey('appointment_type.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0 = lunes ... 6 = domingo
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    timezone = db.Column(db.String(50), default='America/Panama')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    advisor = db.relationship('Advisor', backref='service_availabilities')
    appointment_type = db.relationship('AppointmentType', backref='advisor_availabilities')
    created_by_user = db.relationship('User', backref='service_availabilities_created', foreign_keys=[created_by])

    __table_args__ = (
        db.CheckConstraint('end_time > start_time', name='ck_service_availability_time_window'),
        db.Index('idx_advisor_service_day', 'advisor_id', 'appointment_type_id', 'day_of_week'),
    )


class DailyServiceAvailability(db.Model):
    """
    Disponibilidad específica por día, servicio y asesor.
    Permite configurar horarios para días específicos en lugar de horarios semanales recurrentes.
    """
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)  # Día específico (ej: 2026-01-15)
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisor.id'), nullable=False)
    appointment_type_id = db.Column(db.Integer, db.ForeignKey('appointment_type.id'), nullable=False)
    start_time = db.Column(db.Time, nullable=False)  # Hora inicio del bloque (ej: 09:00)
    end_time = db.Column(db.Time, nullable=False)    # Hora fin del bloque (ej: 12:00)
    timezone = db.Column(db.String(50), default='America/Panama')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    advisor = db.relationship('Advisor', backref='daily_availabilities')
    appointment_type = db.relationship('AppointmentType', backref='daily_availabilities')
    created_by_user = db.relationship('User', backref='daily_availabilities_created', foreign_keys=[created_by])
    
    __table_args__ = (
        db.CheckConstraint('end_time > start_time', name='ck_daily_availability_time_window'),
        db.Index('idx_daily_availability', 'date', 'advisor_id', 'appointment_type_id'),
        db.Index('idx_daily_availability_date', 'date'),
    )


class AppointmentPricing(db.Model):
    """Reglas de precio/descuento por tipo de membresía."""
    id = db.Column(db.Integer, primary_key=True)
    appointment_type_id = db.Column(db.Integer, db.ForeignKey('appointment_type.id'), nullable=False)
    membership_type = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float)
    discount_percentage = db.Column(db.Float, default=0.0)
    is_included = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('appointment_type_id', 'membership_type', name='uq_pricing_membership'),
    )


class AppointmentSlot(db.Model):
    """Slots concretos de tiempo que pueden reservar los miembros."""
    id = db.Column(db.Integer, primary_key=True)
    appointment_type_id = db.Column(db.Integer, db.ForeignKey('appointment_type.id'), nullable=False)
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisor.id'), nullable=False)
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=False)
    capacity = db.Column(db.Integer, default=1)
    reserved_seats = db.Column(db.Integer, default=0)
    is_available = db.Column(db.Boolean, default=True)
    is_auto_generated = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by_user = db.relationship('User', backref='appointment_slots_created', foreign_keys=[created_by])
    appointment = db.relationship('Appointment', backref='slot', uselist=False)

    __table_args__ = (
        db.CheckConstraint('capacity >= 1', name='ck_slot_capacity_positive'),
        db.CheckConstraint('end_datetime > start_datetime', name='ck_slot_time_window'),
    )

    def remaining_seats(self):
        return max(0, (self.capacity or 1) - (self.reserved_seats or 0))


class Appointment(db.Model):
    """Reservas realizadas por miembros - Modelo inspirado en Odoo."""
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(40), unique=True, default=lambda: secrets.token_hex(4).upper())
    appointment_type_id = db.Column(db.Integer, db.ForeignKey('appointment_type.id'), nullable=False)
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisor.id'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('appointment_slot.id'), nullable=True)  # NULL cuando está en cola
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    membership_type = db.Column(db.String(50))
    is_group = db.Column(db.Boolean, default=False)
    start_datetime = db.Column(db.DateTime, nullable=True)  # NULL cuando está en cola, se asigna cuando el asesor confirma
    end_datetime = db.Column(db.DateTime, nullable=True)  # NULL cuando está en cola, se asigna cuando el asesor confirma
    status = db.Column(db.String(20), default='pending')  # pending (en cola), confirmed, cancelled, completed, no_show
    queue_position = db.Column(db.Integer, nullable=True)  # Posición en la cola (opcional, para ordenar)
    advisor_confirmed = db.Column(db.Boolean, default=False)
    advisor_confirmed_at = db.Column(db.DateTime)
    cancellation_reason = db.Column(db.Text)
    cancelled_by = db.Column(db.String(20))  # user, advisor, system
    cancelled_at = db.Column(db.DateTime)
    base_price = db.Column(db.Float, default=0.0)
    final_price = db.Column(db.Float, default=0.0)
    discount_applied = db.Column(db.Float, default=0.0)
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid, refunded, partial
    payment_method = db.Column(db.String(50))  # stripe, cash, bank_transfer, free
    payment_reference = db.Column(db.String(100))
    user_notes = db.Column(db.Text)
    advisor_notes = db.Column(db.Text)
    # Campos adicionales inspirados en Odoo
    calendar_sync_url = db.Column(db.String(500))  # URL para sincronizar con Google Calendar, Outlook, etc.
    calendar_event_id = db.Column(db.String(200))  # ID del evento en el calendario externo
    reminder_sent = db.Column(db.Boolean, default=False)  # Si se envió recordatorio
    reminder_sent_at = db.Column(db.DateTime)
    confirmation_sent = db.Column(db.Boolean, default=False)  # Si se envió confirmación
    confirmation_sent_at = db.Column(db.DateTime)
    cancellation_sent = db.Column(db.Boolean, default=False)  # Si se envió notificación de cancelación
    cancellation_sent_at = db.Column(db.DateTime)
    meeting_url = db.Column(db.String(500))  # URL de la reunión (Zoom, Teams, etc.)
    meeting_password = db.Column(db.String(100))  # Contraseña de la reunión si aplica
    check_in_time = db.Column(db.DateTime)  # Hora de llegada/check-in
    check_out_time = db.Column(db.DateTime)  # Hora de salida/check-out
    duration_actual = db.Column(db.Integer)  # Duración real en minutos
    rating = db.Column(db.Integer)  # Calificación del 1 al 5
    rating_comment = db.Column(db.Text)  # Comentario de la calificación
    # Campos para vincular con servicios
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=True)  # Servicio relacionado (para citas de diagnóstico)
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'), nullable=True)  # Pago relacionado
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref='appointments')
    participants = db.relationship('AppointmentParticipant', backref='appointment', lazy=True, cascade='all, delete-orphan')
    related_service = db.relationship('Service', foreign_keys=[service_id], backref='diagnostic_appointments')
    payment = db.relationship('Payment', foreign_keys=[payment_id], backref='appointments')

    def can_user_cancel(self):
        """Permite cancelar si faltan al menos 12 horas."""
        return self.start_datetime - datetime.utcnow() > timedelta(hours=12)
    
    def is_past(self):
        """Verifica si la cita ya pasó."""
        return self.end_datetime < datetime.utcnow()
    
    def is_upcoming(self):
        """Verifica si la cita está próxima (dentro de las próximas 24 horas)."""
        now = datetime.utcnow()
        return self.start_datetime > now and (self.start_datetime - now) <= timedelta(hours=24)
    
    def get_duration_minutes(self):
        """Calcula la duración en minutos."""
        if self.end_datetime and self.start_datetime:
            delta = self.end_datetime - self.start_datetime
            return int(delta.total_seconds() / 60)
        return 0


class AppointmentParticipant(db.Model):
    """Participantes adicionales (para citas grupales)."""
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    invited_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id], backref='appointment_participations')
    invited_by = db.relationship('User', foreign_keys=[invited_by_id], backref='appointment_invitations', lazy=True)


class ActivityLog(db.Model):
    """Log de actividades administrativas"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # create_event, update_event, etc.
    entity_type = db.Column(db.String(50), nullable=False)  # event, discount, user, etc.
    entity_id = db.Column(db.Integer)
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='activity_logs')
    
    @classmethod
    def log_activity(cls, user_id, action, entity_type, entity_id, description, request=None):
        """Método helper para registrar actividades"""
        log = cls(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get('User-Agent') if request else None
        )
        db.session.add(log)
        return log

# Modelos de Carrito de Compras

class HistoryTransaction(db.Model):
    """
    Historial de transacciones y eventos del sistema
    Registro inmutable de todas las acciones relevantes
    """
    __tablename__ = 'history_transaction'
    
    # Identificación
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False)
    
    # Temporal
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Tipo y Actor
    transaction_type = db.Column(db.String(50), nullable=False, index=True)
    # Valores: USER_ACTION, SYSTEM_ACTION, ERROR, WARNING, INFO, SECURITY_EVENT
    
    actor_type = db.Column(db.String(20), nullable=False)
    # Valores: 'user' | 'system'
    
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    # ID del usuario si actor_type='user', NULL si 'system'
    
    # Propietario y Visibilidad
    owner_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    # Usuario dueño de la transacción (para filtrado)
    
    visibility = db.Column(db.String(20), nullable=False, default='both')
    # Valores: 'admin' | 'user' | 'both'
    
    # Acción y Estado
    action = db.Column(db.String(200), nullable=False)
    # Descripción de la acción ejecutada
    
    status = db.Column(db.String(20), nullable=False, default='success', index=True)
    # Valores: 'pending' | 'success' | 'failed' | 'cancelled'
    
    # Contexto
    context_app = db.Column(db.String(100), nullable=True)
    context_screen = db.Column(db.String(100), nullable=True)
    context_module = db.Column(db.String(100), nullable=True)
    
    # Datos
    payload = db.Column(db.Text, nullable=True)
    # JSON serializado con datos de entrada
    
    result = db.Column(db.Text, nullable=True)
    # JSON serializado con resultado de la acción
    
    transaction_metadata = db.Column('transaction_transaction_metadata', db.Text, nullable=True)
    # JSON serializado: {ip, device, session_id, user_agent}
    # Nota: El nombre de la columna en BD es transaction_transaction_metadata por compatibilidad
    
    # Relaciones
    actor_user = db.relationship('User', foreign_keys=[actor_id], backref='history_as_actor')
    owner_user = db.relationship('User', foreign_keys=[owner_user_id], backref='history_transactions')
    
    def __init__(self, **kwargs):
        """Inicializar con UUID automático"""
        import uuid as uuid_lib
        if 'uuid' not in kwargs or not kwargs.get('uuid'):
            kwargs['uuid'] = str(uuid_lib.uuid4())
        super(HistoryTransaction, self).__init__(**kwargs)
    
    def to_dict(self, include_sensitive=False):
        """Serializar a diccionario"""
        data = {
            'id': self.id,
            'uuid': self.uuid,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'transaction_type': self.transaction_type,
            'actor_type': self.actor_type,
            'actor_id': self.actor_id,
            'owner_user_id': self.owner_user_id,
            'visibility': self.visibility,
            'action': self.action,
            'status': self.status,
            'context': {
                'app': self.context_app,
                'screen': self.context_screen,
                'module': self.context_module
            }
        }
        
        if include_sensitive:
            # Solo para admin
            import json
            data['payload'] = json.loads(self.payload) if self.payload else None
            data['result'] = json.loads(self.result) if self.result else None
            data['transaction_metadata'] = json.loads(self.transaction_metadata) if self.transaction_metadata else None
        else:
            # Para usuarios: solo resultado básico
            if self.result:
                import json
                try:
                    result_data = json.loads(self.result)
                    data['result_summary'] = result_data.get('summary', '')
                except:
                    data['result_summary'] = ''
        
        return data
    
    def __repr__(self):
        return f'<HistoryTransaction {self.id}: {self.action} ({self.status})>'

class Cart(db.Model):
    """Carrito de compras del usuario"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    
    # Códigos de descuento aplicados
    discount_code_id = db.Column(db.Integer, db.ForeignKey('discount_code.id'), nullable=True)
    master_discount_id = db.Column(db.Integer, db.ForeignKey('discount.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    user = db.relationship('User', backref='cart')
    items = db.relationship('CartItem', backref='cart', lazy=True, cascade='all, delete-orphan')
    discount_code = db.relationship('DiscountCode', foreign_keys=[discount_code_id], backref='carts')
    master_discount = db.relationship('Discount', foreign_keys=[master_discount_id], backref='carts')
    
    def get_subtotal(self):
        """Calcular el subtotal del carrito (sin descuentos)"""
        return sum(item.get_subtotal() for item in self.items)
    
    def get_total(self):
        """Calcular el total del carrito (con descuentos aplicados)"""
        return self.get_final_total()
    
    def get_items_count(self):
        """Obtener cantidad de items en el carrito"""
        return len(self.items)
    
    def get_master_discount_amount(self):
        """Obtener el descuento maestro aplicable"""
        if not self.master_discount_id:
            # Buscar descuento maestro activo
            master = Discount.query.filter_by(
                is_master=True,
                is_active=True
            ).first()
            
            if master and master.can_use():
                now = datetime.utcnow()
                if (not master.start_date or now >= master.start_date) and \
                   (not master.end_date or now <= master.end_date):
                    self.master_discount_id = master.id
                    db.session.commit()
                    return master
            return None
        
        master = Discount.query.get(self.master_discount_id)
        if master and master.can_use():
            return master
        return None
    
    def get_discount_breakdown(self):
        """Obtener desglose de descuentos aplicados"""
        subtotal = self.get_subtotal()
        breakdown = {
            'subtotal': subtotal,
            'master_discount': None,
            'code_discount': None,
            'total_discount': 0,
            'final_total': subtotal
        }
        
        # Aplicar descuento maestro
        master = self.get_master_discount_amount()
        if master:
            if master.discount_type == 'percentage':
                discount_amount = subtotal * (master.value / 100)
            else:
                discount_amount = min(master.value, subtotal)
            
            breakdown['master_discount'] = {
                'discount': master,
                'amount': discount_amount
            }
            breakdown['total_discount'] += discount_amount
            subtotal_after_master = subtotal - discount_amount
        else:
            subtotal_after_master = subtotal
        
        # Aplicar código promocional
        if self.discount_code_id:
            code = DiscountCode.query.get(self.discount_code_id)
            if code:
                can_use, message = code.can_use(self.user_id)
                if can_use:
                    discount_amount = code.apply_discount(subtotal_after_master)
                    breakdown['code_discount'] = {
                        'code': code,
                        'amount': discount_amount
                    }
                    breakdown['total_discount'] += discount_amount
                    subtotal_after_master -= discount_amount
        
        breakdown['final_total'] = max(0, subtotal - breakdown['total_discount'])
        return breakdown
    
    def get_final_total(self):
        """Calcular el total final con todos los descuentos"""
        breakdown = self.get_discount_breakdown()
        return breakdown['final_total']
    
    def apply_discount_code(self, code_string):
        """Aplicar un código de descuento al carrito"""
        code = DiscountCode.query.filter_by(code=code_string.upper().strip()).first()
        if not code:
            return False, "Código de descuento no encontrado"
        
        can_use, message = code.can_use(self.user_id)
        if not can_use:
            return False, message
        
        # Verificar que el código aplique a los productos del carrito
        if code.applies_to != 'all':
            # Verificar si hay items que califiquen
            has_qualifying_items = False
            for item in self.items:
                if code.applies_to == 'events' and item.product_type == 'event':
                    has_qualifying_items = True
                    break
                elif code.applies_to == 'memberships' and item.product_type == 'membership':
                    has_qualifying_items = True
                    break
            
            if not has_qualifying_items:
                return False, f"Este código solo aplica a {code.applies_to}"
        
        self.discount_code_id = code.id
        db.session.commit()
        return True, "Código aplicado correctamente"
    
    def remove_discount_code(self):
        """Remover el código de descuento del carrito"""
        self.discount_code_id = None
        db.session.commit()
        return True
    
    def clear(self):
        """Vaciar el carrito"""
        CartItem.query.filter_by(cart_id=self.id).delete()
        self.discount_code_id = None
        self.master_discount_id = None
        db.session.commit()


class CartItem(db.Model):
    """Items individuales en el carrito"""
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=False)
    
    # Tipo de producto: 'membership', 'event', 'service'
    product_type = db.Column(db.String(50), nullable=False)
    product_id = db.Column(db.Integer, nullable=False)  # ID del producto según su tipo
    
    # Información del producto (cache para evitar joins)
    product_name = db.Column(db.String(200), nullable=False)
    product_description = db.Column(db.Text)
    
    # Precio y cantidad
    unit_price = db.Column(db.Float, nullable=False)  # Precio unitario en centavos
    quantity = db.Column(db.Integer, default=1, nullable=False)
    
    # Metadata adicional (JSON para flexibilidad) - usando item_metadata para evitar conflicto con SQLAlchemy
    item_metadata = db.Column(db.Text)  # JSON con información adicional del producto
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_subtotal(self):
        """Calcular subtotal del item"""
        return self.unit_price * self.quantity
    
    def to_dict(self):
        """Convertir a diccionario para JSON"""
        return {
            'id': self.id,
            'product_type': self.product_type,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'product_description': self.product_description,
            'unit_price': self.unit_price,
            'quantity': self.quantity,
            'subtotal': self.get_subtotal(),
            'metadata': self.item_metadata
        }

# Modelos de Servicios
class Service(db.Model):
    """Modelo para servicios del catálogo"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(100))  # Clase de FontAwesome (ej: 'fas fa-newspaper')
    membership_type = db.Column(db.String(50), nullable=False)  # basic, pro, premium, deluxe, corporativo
    category_id = db.Column(db.Integer, db.ForeignKey('service_category.id'), nullable=True)  # Categoría del servicio
    external_link = db.Column(db.String(500))  # URL externa si aplica
    base_price = db.Column(db.Float, default=50.0)  # Precio base en USD
    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)  # Orden de visualización
    # Campos para cita de diagnóstico
    requires_diagnostic_appointment = db.Column(db.Boolean, default=False)  # Si requiere cita diagnóstico antes de usar
    diagnostic_appointment_type_id = db.Column(db.Integer, db.ForeignKey('appointment_type.id'), nullable=True)  # Tipo de cita de diagnóstico
    # Campos para sistema de citas con pago/abono
    appointment_type_id = db.Column(db.Integer, db.ForeignKey('appointment_type.id'), nullable=True)  # Tipo de cita asociado al servicio
    requires_payment_before_appointment = db.Column(db.Boolean, default=True)  # Si requiere pago antes de agendar
    deposit_amount = db.Column(db.Float, nullable=True)  # Abono fijo (ej: $50)
    deposit_percentage = db.Column(db.Float, nullable=True)  # Abono porcentual (ej: 0.5 = 50%)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación con reglas de precios
    pricing_rules = db.relationship('ServicePricingRule', backref='service', lazy=True, cascade='all, delete-orphan')
    # Relación con tipo de cita de diagnóstico
    diagnostic_appointment_type = db.relationship('AppointmentType', foreign_keys=[diagnostic_appointment_type_id], backref='diagnostic_services')
    
    def pricing_for_membership(self, user_membership_type=None):
        """Calcula el precio final considerando reglas por membresía y descuentos automáticos.
        
        IMPORTANTE: Los servicios siempre son facturables (nunca $0 por membresía),
        solo se aplican descuentos según la membresía del usuario.
        Solo se marcan como 'incluidos' si hay una regla explícita con is_included=True.
        """
        base_price = self.base_price or 0.0
        final_price = base_price
        discount_percentage = 0.0
        is_included = False
        
        # Si no hay precio base, el servicio es gratis
        if base_price <= 0:
            return {
                'base_price': 0.0,
                'final_price': 0.0,
                'discount_percentage': 0.0,
                'is_included': True
            }
        
        # Buscar regla explícita de precio para esta membresía
        if user_membership_type:
            rule = ServicePricingRule.query.filter_by(
                service_id=self.id,
                membership_type=user_membership_type,
                is_active=True
            ).first()
            
            if rule:
                # Si hay una regla explícita que dice que está incluido, respetarla
                if rule.is_included:
                    final_price = 0.0
                    is_included = True
                # Si hay un precio fijo, usarlo
                elif rule.price is not None:
                    final_price = rule.price
                # Si hay un descuento porcentual en la regla, aplicarlo
                elif rule.discount_percentage:
                    discount_percentage = rule.discount_percentage
                    final_price = max(0.0, base_price * (1 - discount_percentage / 100))
        
        # Si no hay regla explícita o no se aplicó descuento, aplicar descuento automático por membresía
        if not is_included and user_membership_type and discount_percentage == 0.0:
            # Obtener descuento automático desde MembershipDiscount
            # MembershipDiscount ya está definido en este mismo archivo, no necesita import
            discount_percentage = MembershipDiscount.get_discount(user_membership_type, product_type='service')
            if discount_percentage > 0:
                final_price = max(0.0, base_price * (1 - discount_percentage / 100))
        
        return {
            'base_price': base_price,
            'final_price': final_price,
            'discount_percentage': discount_percentage,
            'is_included': is_included
        }
    
    def calculate_deposit(self, user_membership_type=None):
        """
        Calcula el monto de abono requerido para este servicio.
        
        Retorna:
            dict con:
            - deposit_amount: monto a pagar como abono
            - final_price: precio total del servicio
            - remaining_balance: saldo pendiente después del abono
            - requires_full_payment: si requiere pago completo
        """
        pricing = self.pricing_for_membership(user_membership_type)
        final_price = pricing['final_price']
        
        # Si el servicio es gratuito, no requiere abono
        if final_price <= 0:
            return {
                'deposit_amount': 0.0,
                'final_price': 0.0,
                'remaining_balance': 0.0,
                'requires_full_payment': False
            }
        
        # Calcular abono
        deposit_amount = final_price  # Por defecto, pago completo
        
        if self.deposit_amount:
            # Abono fijo
            deposit_amount = min(self.deposit_amount, final_price)
        elif self.deposit_percentage:
            # Abono porcentual
            deposit_amount = final_price * self.deposit_percentage
        
        remaining_balance = max(0.0, final_price - deposit_amount)
        
        return {
            'deposit_amount': deposit_amount,
            'final_price': final_price,
            'remaining_balance': remaining_balance,
            'requires_full_payment': (remaining_balance == 0.0)
        }
    
    def requires_appointment(self):
        """Verifica si el servicio requiere cita."""
        return self.appointment_type_id is not None and self.is_active
    
    def is_free_service(self, user_membership_type=None):
        """Verifica si el servicio es gratuito para el usuario."""
        pricing = self.pricing_for_membership(user_membership_type)
        return pricing['final_price'] <= 0 or pricing['is_included']
    
    def to_dict(self):
        """Convertir a diccionario para JSON"""
        try:
            category_dict = None
            if self.category:
                try:
                    category_dict = self.category.to_dict()
                except:
                    # Si hay error al serializar categoría, solo incluir ID
                    category_dict = {'id': self.category.id, 'name': self.category.name} if self.category else None
        except:
            category_dict = None
        
        return {
            'id': self.id,
            'name': self.name or '',
            'description': self.description or '',
            'icon': self.icon or 'fas fa-cog',
            'membership_type': self.membership_type,
            'category_id': self.category_id,
            'category': category_dict,
            'external_link': self.external_link or '',
            'base_price': float(self.base_price) if self.base_price else 0.0,
            'is_active': self.is_active if self.is_active is not None else True,
            'display_order': self.display_order or 0,
            'requires_diagnostic_appointment': self.requires_diagnostic_appointment if self.requires_diagnostic_appointment is not None else False,
            'diagnostic_appointment_type_id': self.diagnostic_appointment_type_id,
            'appointment_type_id': self.appointment_type_id,
            'requires_payment_before_appointment': self.requires_payment_before_appointment if self.requires_payment_before_appointment is not None else True,
            'deposit_amount': float(self.deposit_amount) if self.deposit_amount else None,
            'deposit_percentage': float(self.deposit_percentage) if self.deposit_percentage else None
        }

class ServiceCategory(db.Model):
    """Categorías para organizar servicios"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    slug = db.Column(db.String(100), unique=True)  # URL-friendly identifier
    description = db.Column(db.Text)
    icon = db.Column(db.String(100))  # Clase FontAwesome (ej: 'fas fa-book')
    color = db.Column(db.String(20), default='primary')  # Color para badges/tarjetas
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación con servicios
    services = db.relationship('Service', backref='category', lazy=True)
    
    def to_dict(self):
        """Convertir a diccionario para JSON"""
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'icon': self.icon,
            'color': self.color,
            'display_order': self.display_order,
            'is_active': self.is_active,
            'services_count': len([s for s in self.services if s.is_active]) if self.services else 0
        }
    
    def __repr__(self):
        return f'<ServiceCategory {self.name}>'

class ServicePricingRule(db.Model):
    """Reglas de precio/descuento por tipo de membresía para servicios."""
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    membership_type = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float)  # Precio fijo (sobrescribe base_price)
    discount_percentage = db.Column(db.Float, default=0.0)  # Descuento porcentual
    is_included = db.Column(db.Boolean, default=False)  # Si está incluido (gratis) en la membresía
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('service_id', 'membership_type', name='uq_service_pricing_membership'),
    )

class MembershipDiscount(db.Model):
    """Descuentos por tipo de membresía aplicables a servicios y eventos en el carrito"""
    id = db.Column(db.Integer, primary_key=True)
    membership_type = db.Column(db.String(50), nullable=False)  # basic, pro, premium, deluxe, corporativo
    product_type = db.Column(db.String(50), nullable=False)  # service, event
    discount_percentage = db.Column(db.Float, nullable=False, default=0.0)  # 0-100
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('membership_type', 'product_type', name='uq_membership_discount'),
    )
    
    def to_dict(self):
        """Convertir a diccionario para JSON"""
        return {
            'id': self.id,
            'membership_type': self.membership_type,
            'product_type': self.product_type,
            'discount_percentage': float(self.discount_percentage),
            'is_active': self.is_active
        }
    
    def __repr__(self):
        return f'<MembershipDiscount {self.membership_type} - {self.product_type}: {self.discount_percentage}%>'
    
    @staticmethod
    def get_discount(membership_type, product_type='service'):
        """Obtener descuento para un tipo de membresía y producto"""
        discount = MembershipDiscount.query.filter_by(
            membership_type=membership_type,
            product_type=product_type,
            is_active=True
        ).first()
        
        if discount:
            return discount.discount_percentage
        return 0.0  # Sin descuento por defecto

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

# Rutas principales

@app.route('/api/notifications/<int:notification_id>/toggle-read', methods=['POST'])
@login_required
def toggle_notification_read(notification_id):
    """Toggle estado de lectura de notificación (leída <-> no leída)"""
    try:
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=current_user.id
        ).first()
        
        if not notification:
            return jsonify({
                'success': False,
                'error': 'Notificación no encontrada'
            }), 404
        
        # Toggle estado
        notification.is_read = not notification.is_read
        db.session.commit()
        
        action = 'leída' if notification.is_read else 'no leída'
        print(f"✅ Notificación {notification_id} marcada como {action} por usuario {current_user.id}")
        return jsonify({
            'success': True,
            'message': f'Notificación marcada como {action}',
            'notification': {
                'id': notification.id,
                'is_read': notification.is_read
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error cambiando estado de notificación {notification_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/notifications/delete-read', methods=['DELETE'])
@login_required
def delete_read_notifications():
    """Eliminar todas las notificaciones leídas del usuario"""
    try:
        deleted_count = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=True
        ).delete()
        
        db.session.commit()
        
        print(f"✅ {deleted_count} notificaciones leídas eliminadas por usuario {current_user.id}")
        return jsonify({
            'success': True,
            'message': f'{deleted_count} notificación(es) leída(s) eliminada(s)',
            'deleted_count': deleted_count
        })
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error eliminando notificaciones leídas: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/notifications/delete-all', methods=['DELETE'])
@login_required
def delete_all_notifications():
    """Eliminar todas las notificaciones del usuario"""
    try:
        deleted_count = Notification.query.filter_by(
            user_id=current_user.id
        ).delete()
        
        db.session.commit()
        
        print(f"✅ {deleted_count} notificaciones eliminadas por usuario {current_user.id}")
        return jsonify({
            'success': True,
            'message': f'{deleted_count} notificación(es) eliminada(s)',
            'deleted_count': deleted_count
        })
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error eliminando todas las notificaciones: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/')
def index():
    """Redirige a login (sin landing)."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/promocion')
def promocion():
    """Página de promoción de servicios - Standalone"""
    return render_template('promocion.html')

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
    """Enviar email de verificación al usuario"""
    try:
        if not EMAIL_TEMPLATES_AVAILABLE or not email_service:
            print(f"⚠️ Email service no disponible. No se enviará email de verificación a {user.email}")
            return False
        
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
            return True
        else:
            print(f"❌ Error al enviar email de verificación a {user.email}")
            # El token ya está guardado, así que el usuario puede intentar reenviar
            return False
            
    except Exception as e:
        print(f"❌ Error enviando email de verificación: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return False

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registro de nuevos usuarios"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()
        country = request.form.get('country', '').strip()
        cedula_or_passport = request.form.get('cedula_or_passport', '').strip()
        
        # Validar campos obligatorios
        if not email or not password or not first_name or not last_name:
            flash('Todos los campos obligatorios deben ser completados.', 'error')
            return render_template('register.html')
        
        # Validar país
        if country:
            is_valid, error_message = validate_country(country)
            if not is_valid:
                flash(error_message, 'error')
                return render_template('register.html')
        
        # Validar cédula o pasaporte
        if cedula_or_passport:
            is_valid, error_message = validate_cedula_or_passport(cedula_or_passport, country)
            if not is_valid:
                flash(error_message, 'error')
                return render_template('register.html')
        
        # Validar formato de email
        is_valid, error_message = validate_email_format(email)
        if not is_valid:
            flash(error_message, 'error')
            return render_template('register.html')
        
        # Verificar si el usuario ya existe
        if User.query.filter_by(email=email.lower()).first():
            flash('El correo electrónico ya está registrado.', 'error')
            return render_template('register.html')
        
        # Crear nuevo usuario
        user = User(
            email=email.lower(),
            first_name=first_name,
            last_name=last_name,
            phone=phone if phone else None,
            country=country if country else None,
            cedula_or_passport=cedula_or_passport if cedula_or_passport else None
        )
        user.set_password(password)
        user.email_verified = False
        
        db.session.add(user)
        db.session.commit()  # Commit inicial para obtener el ID del usuario

        # Registrar registro de usuario en historial
        try:
            from history_module import HistoryLogger
            HistoryLogger.log_user_action(
                user_id=user.id,
                action="Registro de nuevo usuario",
                status="success",
                context={"app": "web", "screen": "register", "module": "auth"},
                payload={"email": email, "first_name": first_name, "last_name": last_name},
                result={"user_id": user.id},
                request=request
            )
        except Exception as e:
            pass  # No romper el flujo si falla el historial
        
        # Enviar email de verificación (genera el token y hace commit)
        try:
            apply_email_config_from_db()
            send_verification_email(user)
        except Exception as e:
            print(f"❌ Error enviando email de verificación: {e}")
            import traceback
            traceback.print_exc()
        
        # Enviar notificación de bienvenida (solo si el email se envió correctamente)
        try:
            NotificationEngine.notify_welcome(user)
        except Exception as e:
            print(f"❌ Error enviando notificación de bienvenida: {e}")
        
        flash('Registro exitoso. Por favor, verifica tu email para acceder a todas las funciones. Revisa tu bandeja de entrada (y spam).', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', valid_countries=VALID_COUNTRIES)

@app.route('/verify-email/<token>')
def verify_email(token):
    """Verificar email con token"""
    try:
        # Buscar usuario con el token (sin importar si está verificado o no)
        user = User.query.filter_by(email_verification_token=token).first()
        
        if not user:
            print(f"❌ Token de verificación no encontrado: {token[:20]}...")
            flash('El enlace de verificación no es válido. Por favor, solicita uno nuevo.', 'error')
            return redirect(url_for('login'))
        
        print(f"🔍 Verificando email para usuario: {user.email} (ID: {user.id})")
        print(f"   Token expira: {user.email_verification_token_expires}")
        print(f"   Hora actual: {datetime.utcnow()}")
        print(f"   Ya verificado: {user.email_verified}")
        
        # Si ya está verificado, permitir acceso pero informar
        if user.email_verified:
            flash('Tu email ya está verificado. Puedes iniciar sesión normalmente.', 'info')
            if current_user.is_authenticated and current_user.id == user.id:
                return redirect(url_for('dashboard'))
            return redirect(url_for('login'))
        
        # Verificar si el token expiró
        if user.email_verification_token_expires:
            time_diff = (user.email_verification_token_expires - datetime.utcnow()).total_seconds()
            print(f"   Tiempo restante: {time_diff} segundos")
            
            if time_diff <= 0:
                print(f"❌ Token expirado para usuario {user.email}")
                flash('El enlace de verificación ha expirado. Por favor, solicita uno nuevo.', 'error')
                return redirect(url_for('resend_verification'))
        
        # Verificar email
        user.email_verified = True
        user.email_verification_token = None
        user.email_verification_token_expires = None
        db.session.commit()
        
        print(f"✅ Email verificado exitosamente para {user.email}")
        flash('¡Email verificado exitosamente! Ahora puedes iniciar sesión y acceder a todas las funciones.', 'success')
        
        # Si el usuario no está logueado, redirigir al login con mensaje claro
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        
        # Si está logueado pero es otro usuario, cerrar sesión y redirigir
        if current_user.id != user.id:
            logout_user()
            flash('Por favor, inicia sesión con tu cuenta.', 'info')
            return redirect(url_for('login'))
        
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        print(f"❌ Error en verify_email: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        flash('Ocurrió un error al verificar tu email. Por favor, intenta nuevamente o solicita un nuevo enlace.', 'error')
        return redirect(url_for('login'))

@app.route('/resend-verification', methods=['GET', 'POST'])
@login_required
def resend_verification():
    """Reenviar email de verificación"""
    if request.method == 'POST':
        if current_user.email_verified:
            flash('Tu email ya está verificado.', 'info')
            return redirect(url_for('dashboard'))
        
        try:
            apply_email_config_from_db()
            if send_verification_email(current_user):
                flash('Email de verificación reenviado. Revisa tu bandeja de entrada (y spam).', 'success')
            else:
                flash('Error al enviar el email de verificación. Por favor, intenta más tarde.', 'error')
        except Exception as e:
            flash('Error al reenviar el email de verificación.', 'error')
            print(f"❌ Error reenviando verificación: {e}")
        
        return redirect(url_for('dashboard'))
    
    # Si es GET, mostrar página simple para reenviar
    if current_user.email_verified:
        return redirect(url_for('dashboard'))
    
    return render_template('resend_verification.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Inicio de sesión"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password) and user.is_active:
            login_user(user)
            # Registrar en historial
            try:
                from history_module import HistoryLogger
                HistoryLogger.log_user_action(
                    user_id=user.id,
                    action="Login exitoso",
                    status="success",
                    context={"app": "web", "screen": "login", "module": "auth"},
                    request=request
                )
            except Exception as e:
                pass  # No romper el flujo si falla el historial
            
            # Verificar estado del usuario al iniciar sesión
            try:
                from user_status_checker import UserStatusChecker
                user_status = UserStatusChecker.check_user_status(user.id, db.session)
                if user_status.get('summary', {}).get('total_pending_actions', 0) > 0:
                    urgent_count = user_status['summary'].get('urgent_actions', 0)
                    if urgent_count > 0:
                        flash(f'Tienes {urgent_count} acción(es) urgente(s) pendiente(s). Revisa tu panel.', 'warning')
                    else:
                        flash(f'Tienes {user_status["summary"]["total_pending_actions"]} acción(es) pendiente(s).', 'info')
                session['user_status_checked'] = True
            except Exception as e:
                print(f"⚠️ Error verificando estado del usuario al iniciar sesión: {e}")
            
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Credenciales inválidas.', 'error')
    
    return render_template('login.html')


@app.route('/auth/<provider>/callback')
def oauth_callback(provider):
    """Callback OAuth: intercambia código por token, obtiene userinfo, crea/vincula usuario y hace login."""
    if not OAUTH_AVAILABLE or provider not in ('google', 'facebook', 'linkedin'):
        flash('Login social no disponible para este proveedor.', 'error')
        return redirect(url_for('login'))
    try:
        client = getattr(oauth, provider)
        token = client.authorize_access_token()
        # Google/OpenID: userinfo suele venir en token['userinfo']; Facebook/LinkedIN a veces hay que pedirlo
        userinfo = token.get('userinfo')
        if not userinfo and provider in ('facebook', 'linkedin'):
            ep = {
                'facebook': 'https://graph.facebook.com/v18.0/me?fields=id,name,email,first_name,last_name',
                'linkedin': 'https://api.linkedin.com/v2/userinfo',
            }
            resp = client.get(ep[provider], token=token)
            if resp and getattr(resp, 'status_code', 0) == 200:
                raw = resp.json()
                if provider == 'facebook':
                    userinfo = {
                        'sub': str(raw.get('id', '')),
                        'email': raw.get('email', ''),
                        'name': raw.get('name', ''),
                        'given_name': raw.get('first_name', ''),
                        'family_name': raw.get('last_name', ''),
                    }
                else:
                    userinfo = raw
        if not userinfo:
            flash('No se pudo obtener la información del perfil.', 'error')
            return redirect(url_for('login'))
        # Normalizar campos (OpenID: sub, email, name, given_name, family_name)
        sub = userinfo.get('sub') or userinfo.get('id') or ''
        email = (userinfo.get('email') or '').strip().lower()
        if not email:
            flash('El proveedor no compartió tu correo. Usa el registro con email.', 'error')
            return redirect(url_for('login'))
        name = userinfo.get('name') or ''
        given_name = userinfo.get('given_name') or name.split(None, 1)[0] if name else ''
        family_name = userinfo.get('family_name') or (name.split(None, 1)[1] if len(name.split(None, 1)) > 1 else '')
        provider_user_id = str(sub)
        # Buscar por SocialAuth o por email
        social = SocialAuth.query.filter_by(provider=provider, provider_user_id=provider_user_id).first()
        if social:
            user = User.query.get(social.user_id)
        else:
            user = User.query.filter_by(email=email).first()
        if not user:
            user = User(
                email=email,
                first_name=given_name or 'Usuario',
                last_name=family_name or 'Social',
                phone=None,
                country=None,
                cedula_or_passport=None,
            )
            user.set_password(secrets.token_urlsafe(32))
            user.email_verified = True
            db.session.add(user)
            db.session.flush()
            link = SocialAuth(user_id=user.id, provider=provider, provider_user_id=provider_user_id)
            db.session.add(link)
            db.session.commit()
        else:
            social_existing = SocialAuth.query.filter_by(user_id=user.id, provider=provider).first()
            if not social_existing:
                link = SocialAuth(user_id=user.id, provider=provider, provider_user_id=provider_user_id)
                db.session.add(link)
                db.session.commit()
        if not user.is_active:
            flash('Tu cuenta está desactivada.', 'error')
            return redirect(url_for('login'))
        login_user(user)
        next_page = request.args.get('next') or url_for('dashboard')
        return redirect(next_page)
    except Exception as e:
        print(f"❌ OAuth callback error ({provider}): {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        flash('Error al iniciar sesión con el proveedor. Intenta de nuevo o usa email/contraseña.', 'error')
        return redirect(url_for('login'))


@app.route('/auth/<provider>')
def oauth_login(provider):
    """Redirige al proveedor OAuth (Google, Facebook, LinkedIn)."""
    if not OAUTH_AVAILABLE or provider not in ('google', 'facebook', 'linkedin'):
        flash('Login social no disponible.', 'error')
        return redirect(url_for('login'))
    client = getattr(oauth, provider, None)
    if not client or not app.config.get(f'{provider.upper()}_CLIENT_ID'):
        flash(f'Login con {provider.capitalize()} no está configurado.', 'error')
        return redirect(url_for('login'))
    redirect_uri = url_for('oauth_callback', provider=provider, _external=True)
    return client.authorize_redirect(redirect_uri)


@app.route('/logout')
@login_required
def logout():
    """Cerrar sesión"""
    # Registrar logout en historial
    try:
        from history_module import HistoryLogger
        HistoryLogger.log_user_action(
            user_id=current_user.id,
            action="Logout",
            status="success",
            context={"app": "web", "screen": "logout", "module": "auth"},
            request=request
        )
    except Exception as e:
        pass  # No romper el flujo si falla el historial

    logout_user()
    flash('Has cerrado sesión exitosamente.', 'info')
    return redirect('https://relaticpanama.org')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Solicitar recuperación de contraseña"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Por favor, ingresa tu correo electrónico.', 'error')
            return render_template('forgot_password.html')
        
        # Buscar usuario por email
        user = User.query.filter_by(email=email).first()
        
        # Por seguridad, siempre mostrar mensaje de éxito aunque el email no exista
        # Esto previene enumeración de usuarios
        if user and user.is_active:
            # Generar token de recuperación
            reset_token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(hours=1)  # Válido por 1 hora
            
            # Guardar token en la base de datos
            user.password_reset_token = reset_token
            user.password_reset_token_expires = expires_at
            user.password_reset_sent_at = datetime.utcnow()
            db.session.commit()
            
            # Generar URL de recuperación
            reset_url = f"{request.url_root.rstrip('/')}/reset-password?token={reset_token}"
            
            # Enviar email de recuperación
            try:
                if EMAIL_TEMPLATES_AVAILABLE and email_service:
                    html_content = get_password_reset_email(user, reset_token, reset_url)
                    email_service.send_email(
                        to_email=user.email,
                        subject='Restablecer Contraseña - RelaticPanama',
                        html_content=html_content,
                        email_type='password_reset',
                        recipient_id=user.id,
                        recipient_email=user.email,
                        recipient_name=f"{user.first_name} {user.last_name}"
                    )
                    flash('Se ha enviado un enlace de recuperación a tu correo electrónico. Revisa tu bandeja de entrada y carpeta de spam.', 'success')
                else:
                    flash('Error: El servicio de email no está disponible. Contacta al administrador.', 'error')
            except Exception as e:
                print(f"Error enviando email de recuperación: {e}")
                flash('Error al enviar el email. Por favor, intenta nuevamente o contacta al soporte.', 'error')
        else:
            # Mostrar mensaje genérico para no revelar si el email existe
            flash('Si el correo electrónico existe en nuestro sistema, recibirás un enlace de recuperación.', 'info')
    
    return render_template('forgot_password.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Restablecer contraseña con token"""
    token = request.args.get('token') or request.form.get('token')
    
    if not token:
        flash('Token de recuperación no válido o faltante.', 'error')
        return redirect(url_for('forgot_password'))
    
    # Buscar usuario con token válido
    user = User.query.filter_by(password_reset_token=token).first()
    
    if not user:
        flash('Token de recuperación no válido o expirado.', 'error')
        return redirect(url_for('forgot_password'))
    
    # Verificar que el token no haya expirado
    if user.password_reset_token_expires and user.password_reset_token_expires < datetime.utcnow():
        flash('El enlace de recuperación ha expirado. Por favor, solicita uno nuevo.', 'error')
        # Limpiar token expirado
        user.password_reset_token = None
        user.password_reset_token_expires = None
        db.session.commit()
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        new_password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Validaciones
        if not new_password:
            flash('Por favor, ingresa una nueva contraseña.', 'error')
            return render_template('reset_password.html', token=token, user=user)
        
        if len(new_password) < 8:
            flash('La contraseña debe tener al menos 8 caracteres.', 'error')
            return render_template('reset_password.html', token=token, user=user)
        
        if new_password != confirm_password:
            flash('Las contraseñas no coinciden.', 'error')
            return render_template('reset_password.html', token=token, user=user)
        
        # Actualizar contraseña
        user.set_password(new_password)
        
        # Limpiar token de recuperación
        user.password_reset_token = None
        user.password_reset_token_expires = None
        user.password_reset_sent_at = None
        
        db.session.commit()
        
        # Registrar en historial
        try:
            from history_module import HistoryLogger
            HistoryLogger.log_user_action(
                user_id=user.id,
                action="Contraseña restablecida",
                status="success",
                context={"app": "web", "screen": "reset_password", "module": "auth"},
                request=request
            )
        except Exception as e:
            pass
        
        flash('Tu contraseña ha sido restablecida exitosamente. Puedes iniciar sesión ahora.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html', token=token, user=user)

@app.route('/dashboard')
@login_required
def dashboard():
    """Panel de control del usuario con verificación completa de estado"""
    from app import Appointment, EventRegistration, Event
    from user_status_checker import UserStatusChecker
    
    # Verificar estado completo del usuario
    user_status = UserStatusChecker.check_user_status(current_user.id, db.session)
    
    active_membership = current_user.get_active_membership()
    benefits = Benefit.query.filter_by(is_active=True).all()
    
    # Calcular días desde inicio y días restantes
    days_active = None
    days_remaining = None
    now = datetime.utcnow()
    
    if active_membership:
        if active_membership.start_date:
            days_active = (now - active_membership.start_date).days
        if active_membership.end_date:
            days_remaining = (active_membership.end_date - now).days
    
    # Estadísticas del usuario
    upcoming_appointments = Appointment.query.filter(
        Appointment.user_id == current_user.id,
        Appointment.start_datetime >= now,
        Appointment.status.in_(['pending', 'confirmed'])
    ).order_by(Appointment.start_datetime.asc()).limit(5).all()
    
    past_appointments_count = Appointment.query.filter(
        Appointment.user_id == current_user.id,
        Appointment.start_datetime < now
    ).count()
    
    upcoming_events = EventRegistration.query.join(Event).filter(
        EventRegistration.user_id == current_user.id,
        EventRegistration.registration_status == 'confirmed',
        Event.start_date >= now
    ).order_by(Event.start_date.asc()).limit(5).all()
    
    registered_events_count = EventRegistration.query.filter(
        EventRegistration.user_id == current_user.id,
        EventRegistration.registration_status == 'confirmed'
    ).count()
    
    # Obtener todos los eventos públicos para el calendario
    all_public_events = Event.query.filter(
        Event.publish_status == 'published',
        Event.start_date.isnot(None)
    ).order_by(Event.start_date.asc()).all()
    
    # Detectar si es un usuario nuevo (creado en las últimas 24 horas)
    is_new_user = False
    if current_user.created_at:
        hours_since_creation = (now - current_user.created_at).total_seconds() / 3600
        is_new_user = hours_since_creation < 24
    
    # Verificar si el usuario ha visto el onboarding
    onboarding_seen = session.get('onboarding_seen', False)
    show_onboarding = is_new_user and not onboarding_seen
    
    return render_template('dashboard.html', 
                         membership=active_membership, 
                         benefits=benefits,
                         days_active=days_active,
                         days_remaining=days_remaining,
                         now=now,
                         upcoming_appointments=upcoming_appointments,
                         past_appointments_count=past_appointments_count,
                         upcoming_events=upcoming_events,
                         registered_events_count=registered_events_count,
                         all_public_events=all_public_events,
                         show_onboarding=show_onboarding,
                         is_new_user=is_new_user,
                         user_status=user_status)  # Pasar estado del usuario al template

@app.route('/api/onboarding/seen', methods=['POST'])
@login_required
def mark_onboarding_seen():
    """Marca el onboarding como visto"""
    session['onboarding_seen'] = True
    return jsonify({'success': True})

@app.route('/api/user/status', methods=['GET'])
@login_required
def get_user_status():
    """API endpoint para obtener el estado completo del usuario"""
    try:
        from user_status_checker import UserStatusChecker
        user_status = UserStatusChecker.check_user_status(current_user.id, db.session)
        return jsonify({'success': True, 'status': user_status}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/user/dashboard', methods=['GET'])
@login_required
def get_user_dashboard():
    """API endpoint para obtener datos completos del dashboard"""
    try:
        from user_status_checker import UserStatusChecker
        dashboard_data = UserStatusChecker.get_user_dashboard_data(current_user.id, db.session)
        return jsonify({'success': True, 'dashboard': dashboard_data}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/membership')
@login_required
def membership():
    """Página de membresía"""
    active_membership = current_user.get_active_membership()
    
    # Precios de membresías (en dólares)
    pricing_monthly = {
        'basic': 0,
        'pro': 5,  # $5/mes = $60/año
        'premium': 10,  # $10/mes = $120/año
        'deluxe': 15,  # $15/mes = $180/año
        'corporativo': 25  # $25/mes = $300/año
    }
    
    pricing_yearly = {
        'basic': 0,
        'pro': 60,  # $60/año
        'premium': 120,  # $120/año
        'deluxe': 200,  # $200/año
        'corporativo': 300  # $300/año
    }
    
    # Obtener todos los servicios activos de la base de datos
    all_services = Service.query.filter_by(is_active=True).order_by(Service.display_order, Service.name).all()
    
    # Jerarquía de membresías
    membership_hierarchy = {
        'basic': 0,
        'pro': 1,
        'premium': 2,
        'deluxe': 3,
        'corporativo': 4
    }
    
    # Para cada servicio, determinar en qué planes está disponible
    # Esto se usará en el template para mostrar checkmarks
    services_with_plans = []
    for service in all_services:
        # Obtener todas las reglas de precio activas para este servicio
        pricing_rules = ServicePricingRule.query.filter_by(
            service_id=service.id,
            is_active=True
        ).all()
        
        available_plans = []
        
        # SIEMPRE incluir el membership_type base del servicio (CRÍTICO)
        # Esto asegura que un servicio con membership_type='corporativo' siempre aparezca en corporativo
        if service.membership_type:
            if service.membership_type not in available_plans:
                available_plans.append(service.membership_type)
        
        # Si tiene reglas de precio, agregar también esos planes
        # Las pricing_rules permiten que un servicio aparezca en múltiples planes
        if pricing_rules:
            for rule in pricing_rules:
                if rule.membership_type and rule.membership_type not in available_plans:
                    available_plans.append(rule.membership_type)
        else:
            # Si no tiene reglas, agregar también a todos los planes superiores (jerarquía)
            # Esto permite que servicios básicos aparezcan en todos los planes superiores
            # IMPORTANTE: Excluir 'corporativo' de la herencia automática
            # Solo servicios explícitamente marcados como corporativo aparecen en ese plan
            service_tier = membership_hierarchy.get(service.membership_type, -1)
            if service_tier >= 0:  # Solo si el tier es válido
                for plan_type, tier in membership_hierarchy.items():
                    # Excluir corporativo de la herencia automática
                    if tier > service_tier and plan_type != 'corporativo' and plan_type not in available_plans:
                        available_plans.append(plan_type)
        
        services_with_plans.append({
            'service': service,
            'available_plans': available_plans
        })
    
    return render_template('membership.html', 
                         membership=active_membership,
                         pricing_monthly=pricing_monthly,
                         pricing_yearly=pricing_yearly,
                         services_with_plans=services_with_plans,
                         membership_hierarchy=membership_hierarchy)



@app.route('/api/history', methods=['GET'])
@login_required
def api_get_history():
    """
    API endpoint para obtener historial de transacciones del usuario
    Filtros: transaction_type, status, start_date, end_date
    Paginación: page, per_page
    """
    try:
        from history_module import HistoryLogger
        from app import HistoryTransaction
        
        # Parámetros de filtro
        transaction_type = request.args.get('transaction_type')  # USER_ACTION, SYSTEM_ACTION, ERROR, etc.
        status = request.args.get('status')  # success, failed, pending, cancelled
        start_date = request.args.get('start_date')  # YYYY-MM-DD
        end_date = request.args.get('end_date')  # YYYY-MM-DD
        search = request.args.get('search')  # Búsqueda en action
        
        # Parámetros de paginación
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)  # Máximo 100 por página
        
        # Construir query base - solo transacciones del usuario o visibles para el usuario
        query = HistoryTransaction.query.filter(
            (HistoryTransaction.owner_user_id == current_user.id) |
            (HistoryTransaction.visibility.in_(['user', 'both']))
        )
        
        # Aplicar filtros
        if transaction_type:
            query = query.filter(HistoryTransaction.transaction_type == transaction_type)
        
        if status:
            query = query.filter(HistoryTransaction.status == status)
        
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(HistoryTransaction.timestamp >= start_dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                # Agregar 23:59:59 al final del día
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                query = query.filter(HistoryTransaction.timestamp <= end_dt)
            except ValueError:
                pass
        
        if search:
            query = query.filter(HistoryTransaction.action.contains(search))
        
        # Ordenar por timestamp descendente (más recientes primero)
        query = query.order_by(HistoryTransaction.timestamp.desc())
        
        # Paginación
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Serializar resultados
        transactions = []
        for transaction in pagination.items:
            transactions.append(transaction.to_dict(include_sensitive=False))
        
        return jsonify({
            'success': True,
            'transactions': transactions,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Error obteniendo historial: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/history/<int:transaction_id>', methods=['GET'])
@login_required
def api_get_history_detail(transaction_id):
    """
    API endpoint para obtener detalles de una transacción específica
    """
    try:
        from app import HistoryTransaction
        
        # Buscar transacción
        transaction = HistoryTransaction.query.filter_by(id=transaction_id).first()
        
        if not transaction:
            return jsonify({
                'success': False,
                'error': 'Transacción no encontrada'
            }), 404
        
        # Verificar permisos: debe ser del usuario o visible para el usuario
        if transaction.owner_user_id != current_user.id and transaction.visibility not in ['user', 'both']:
            return jsonify({
                'success': False,
                'error': 'No tienes permiso para ver esta transacción'
            }), 403
        
        # Retornar detalles (sin información sensible para usuarios normales)
        include_sensitive = current_user.is_admin if hasattr(current_user, 'is_admin') else False
        
        return jsonify({
            'success': True,
            'transaction': transaction.to_dict(include_sensitive=include_sensitive)
        }), 200
        
    except Exception as e:
        print(f"❌ Error obteniendo detalle de transacción: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/history/stats', methods=['GET'])
@login_required
def api_get_history_stats():
    """
    API endpoint para obtener estadísticas del historial del usuario
    """
    try:
        from app import HistoryTransaction
        from collections import Counter
        
        # Obtener todas las transacciones del usuario
        transactions = HistoryTransaction.query.filter(
            (HistoryTransaction.owner_user_id == current_user.id) |
            (HistoryTransaction.visibility.in_(['user', 'both']))
        ).all()
        
        # Contar por tipo
        type_counts = Counter(t.transaction_type for t in transactions)
        
        # Contar por status
        status_counts = Counter(t.status for t in transactions)
        
        # Transacciones recientes (últimos 7 días)
        from datetime import timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_count = HistoryTransaction.query.filter(
            (HistoryTransaction.owner_user_id == current_user.id) |
            (HistoryTransaction.visibility.in_(['user', 'both'])),
            HistoryTransaction.timestamp >= week_ago
        ).count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total': len(transactions),
                'recent_7_days': recent_count,
                'by_type': dict(type_counts),
                'by_status': dict(status_counts)
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas de historial: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



# ============================================================================
# API ADMIN - HISTORIAL DE TRANSACCIONES
# ============================================================================

@app.route('/api/admin/history', methods=['GET'])
@admin_required
def api_admin_get_history():
    """
    API endpoint ADMIN para obtener historial de transacciones de todos los usuarios
    Filtros avanzados: user_id, transaction_type, status, start_date, end_date, search
    Paginación: page, per_page
    """
    try:
        from app import HistoryTransaction, User
        
        # Parámetros de filtro
        user_id = request.args.get('user_id', type=int)  # Filtrar por usuario específico
        transaction_type = request.args.get('transaction_type')
        status = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        search = request.args.get('search')
        actor_type = request.args.get('actor_type')  # 'user' o 'system'
        visibility = request.args.get('visibility')  # 'admin', 'user', 'both'
        
        # Parámetros de paginación
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 200)  # Máximo 200 por página para admin
        
        # Construir query base - ADMIN puede ver TODAS las transacciones
        query = HistoryTransaction.query
        
        # Aplicar filtros
        if user_id:
            query = query.filter(
                (HistoryTransaction.owner_user_id == user_id) |
                (HistoryTransaction.actor_id == user_id)
            )
        
        if transaction_type:
            query = query.filter(HistoryTransaction.transaction_type == transaction_type)
        
        if status:
            query = query.filter(HistoryTransaction.status == status)
        
        if actor_type:
            query = query.filter(HistoryTransaction.actor_type == actor_type)
        
        if visibility:
            query = query.filter(HistoryTransaction.visibility == visibility)
        
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(HistoryTransaction.timestamp >= start_dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                query = query.filter(HistoryTransaction.timestamp <= end_dt)
            except ValueError:
                pass
        
        if search:
            query = query.filter(HistoryTransaction.action.contains(search))
        
        # Ordenar por timestamp descendente
        query = query.order_by(HistoryTransaction.timestamp.desc())
        
        # Paginación
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Serializar resultados con información completa (admin)
        transactions = []
        for transaction in pagination.items:
            trans_dict = transaction.to_dict(include_sensitive=True)
            # Agregar información del usuario si existe
            if transaction.actor_id:
                actor = User.query.get(transaction.actor_id)
                if actor:
                    trans_dict['actor'] = {
                        'id': actor.id,
                        'email': actor.email,
                        'first_name': actor.first_name,
                        'last_name': actor.last_name
                    }
            if transaction.owner_user_id:
                owner = User.query.get(transaction.owner_user_id)
                if owner:
                    trans_dict['owner'] = {
                        'id': owner.id,
                        'email': owner.email,
                        'first_name': owner.first_name,
                        'last_name': owner.last_name
                    }
            transactions.append(trans_dict)
        
        return jsonify({
            'success': True,
            'transactions': transactions,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Error obteniendo historial admin: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/history/<int:transaction_id>', methods=['GET'])
@admin_required
def api_admin_get_history_detail(transaction_id):
    """
    API endpoint ADMIN para obtener detalles completos de una transacción
    Incluye toda la información sensible (payload, result, metadata)
    """
    try:
        from app import HistoryTransaction, User
        
        # Buscar transacción
        transaction = HistoryTransaction.query.filter_by(id=transaction_id).first()
        
        if not transaction:
            return jsonify({
                'success': False,
                'error': 'Transacción no encontrada'
            }), 404
        
        # ADMIN puede ver TODAS las transacciones
        trans_dict = transaction.to_dict(include_sensitive=True)
        
        # Agregar información de usuarios relacionados
        if transaction.actor_id:
            actor = User.query.get(transaction.actor_id)
            if actor:
                trans_dict['actor'] = {
                    'id': actor.id,
                    'email': actor.email,
                    'first_name': actor.first_name,
                    'last_name': actor.last_name
                }
        
        if transaction.owner_user_id:
            owner = User.query.get(transaction.owner_user_id)
            if owner:
                trans_dict['owner'] = {
                    'id': owner.id,
                    'email': owner.email,
                    'first_name': owner.first_name,
                    'last_name': owner.last_name
                }
        
        return jsonify({
            'success': True,
            'transaction': trans_dict
        }), 200
        
    except Exception as e:
        print(f"❌ Error obteniendo detalle admin de transacción: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/history/stats', methods=['GET'])
@admin_required
def api_admin_get_history_stats():
    """
    API endpoint ADMIN para obtener estadísticas globales del historial
    """
    try:
        from app import HistoryTransaction, User
        from collections import Counter
        from datetime import timedelta
        
        # Parámetros opcionales
        user_id = request.args.get('user_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Construir query base
        query = HistoryTransaction.query
        
        if user_id:
            query = query.filter(
                (HistoryTransaction.owner_user_id == user_id) |
                (HistoryTransaction.actor_id == user_id)
            )
        
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(HistoryTransaction.timestamp >= start_dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                query = query.filter(HistoryTransaction.timestamp <= end_dt)
            except ValueError:
                pass
        
        transactions = query.all()
        
        # Estadísticas generales
        total = len(transactions)
        
        # Contar por tipo
        type_counts = Counter(t.transaction_type for t in transactions)
        
        # Contar por status
        status_counts = Counter(t.status for t in transactions)
        
        # Contar por actor_type
        actor_type_counts = Counter(t.actor_type for t in transactions)
        
        # Transacciones recientes
        week_ago = datetime.utcnow() - timedelta(days=7)
        month_ago = datetime.utcnow() - timedelta(days=30)
        
        recent_7_days = sum(1 for t in transactions if t.timestamp >= week_ago)
        recent_30_days = sum(1 for t in transactions if t.timestamp >= month_ago)
        
        # Top usuarios por número de transacciones
        user_transaction_counts = Counter()
        for t in transactions:
            if t.owner_user_id:
                user_transaction_counts[t.owner_user_id] += 1
        
        top_users = []
        for user_id, count in user_transaction_counts.most_common(10):
            user = User.query.get(user_id)
            if user:
                top_users.append({
                    'user_id': user_id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'transaction_count': count
                })
        
        # Errores recientes
        errors_recent = sum(1 for t in transactions 
                           if t.transaction_type == 'ERROR' and t.timestamp >= week_ago)
        
        # Eventos de seguridad recientes
        security_recent = sum(1 for t in transactions 
                             if t.transaction_type == 'SECURITY_EVENT' and t.timestamp >= week_ago)
        
        return jsonify({
            'success': True,
            'stats': {
                'total': total,
                'recent_7_days': recent_7_days,
                'recent_30_days': recent_30_days,
                'by_type': dict(type_counts),
                'by_status': dict(status_counts),
                'by_actor_type': dict(actor_type_counts),
                'errors_recent_7_days': errors_recent,
                'security_events_recent_7_days': security_recent,
                'top_users': top_users
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas admin de historial: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/history/export', methods=['GET'])
@admin_required
def api_admin_export_history():
    """
    API endpoint ADMIN para exportar historial en formato CSV
    """
    try:
        from app import HistoryTransaction, User
        from flask import Response
        import csv
        import io
        
        # Parámetros de filtro (mismos que /api/admin/history)
        user_id = request.args.get('user_id', type=int)
        transaction_type = request.args.get('transaction_type')
        status = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Construir query (misma lógica que api_admin_get_history)
        query = HistoryTransaction.query
        
        if user_id:
            query = query.filter(
                (HistoryTransaction.owner_user_id == user_id) |
                (HistoryTransaction.actor_id == user_id)
            )
        
        if transaction_type:
            query = query.filter(HistoryTransaction.transaction_type == transaction_type)
        
        if status:
            query = query.filter(HistoryTransaction.status == status)
        
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(HistoryTransaction.timestamp >= start_dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                query = query.filter(HistoryTransaction.timestamp <= end_dt)
            except ValueError:
                pass
        
        transactions = query.order_by(HistoryTransaction.timestamp.desc()).limit(10000).all()
        
        # Crear CSV en memoria
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Encabezados
        writer.writerow([
            'ID', 'UUID', 'Timestamp', 'Transaction Type', 'Actor Type', 
            'Actor ID', 'Owner User ID', 'Visibility', 'Action', 'Status',
            'Context App', 'Context Screen', 'Context Module'
        ])
        
        # Datos
        for t in transactions:
            writer.writerow([
                t.id, t.uuid, t.timestamp.isoformat() if t.timestamp else '',
                t.transaction_type, t.actor_type, t.actor_id or '',
                t.owner_user_id or '', t.visibility, t.action, t.status,
                t.context_app or '', t.context_screen or '', t.context_module or ''
            ])
        
        # Crear respuesta
        output.seek(0)
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=history_export.csv'}
        )
        
        return response
        
    except Exception as e:
        print(f"❌ Error exportando historial: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/payments/history')
@login_required
def payments_history():
    """Historial de pagos del usuario con información completa de compras"""
    from datetime import datetime, timedelta
    from collections import Counter
    import json
    
    # Obtener todos los pagos del usuario ordenados por fecha (más recientes primero)
    payments = Payment.query.filter_by(user_id=current_user.id).order_by(
        Payment.created_at.desc()
    ).all()
    
    # Calcular conteos por estado
    status_counts = Counter(payment.status for payment in payments)
    
    # Obtener pagos pendientes por más de 5 minutos
    current_time = datetime.utcnow()
    long_pending_payments = []
    
    # Enriquecer cada pago con información adicional
    payments_with_details = []
    for payment in payments:
        payment_data = {
            'payment': payment,
            'subscriptions': [],
            'event_registrations': [],
            'purchased_items': [],
            'discount_applications': [],
            'history_transactions': []
        }
        
        # Obtener suscripciones creadas por este pago
        subscriptions = Subscription.query.filter_by(payment_id=payment.id).all()
        payment_data['subscriptions'] = subscriptions
        
        # Obtener eventos registrados por este pago
        # Buscar por payment_reference
        event_registrations = []
        if payment.payment_reference:
            event_registrations = EventRegistration.query.filter(
                EventRegistration.payment_reference == payment.payment_reference,
                EventRegistration.user_id == current_user.id
            ).all()
        
        # Si no se encontraron, buscar por payment_reference como string del payment_id
        if not event_registrations:
            event_registrations = EventRegistration.query.filter(
                EventRegistration.payment_reference == str(payment.id),
                EventRegistration.user_id == current_user.id
            ).all()
        
        # Si aún no se encontraron, buscar por fecha de pago cercana (últimos 10 minutos)
        if not event_registrations and payment.paid_at:
            from datetime import timedelta
            time_window_start = payment.paid_at - timedelta(minutes=10)
            time_window_end = payment.paid_at + timedelta(minutes=10)
            event_registrations = EventRegistration.query.filter(
                EventRegistration.user_id == current_user.id,
                EventRegistration.payment_date >= time_window_start,
                EventRegistration.payment_date <= time_window_end,
                EventRegistration.payment_status == 'paid'
            ).all()
        
        # Obtener información del historial de transacciones relacionado (ANTES de usarlo)
        history_transactions = HistoryTransaction.query.filter(
            HistoryTransaction.owner_user_id == current_user.id
        ).filter(
            HistoryTransaction.payload.contains(f'"payment_id": {payment.id}')
        ).order_by(HistoryTransaction.timestamp.desc()).limit(5).all()
        
        # También buscar en el historial de transacciones para eventos
        if not event_registrations:
            for transaction in history_transactions:
                if 'Compra realizada' in transaction.action and transaction.result:
                    try:
                        result = json.loads(transaction.result)
                        if 'events' in result and result['events']:
                            event_ids = [e.get('event_id') for e in result['events'] if e.get('event_id')]
                            if event_ids:
                                found_events = EventRegistration.query.filter(
                                    EventRegistration.event_id.in_(event_ids),
                                    EventRegistration.user_id == current_user.id
                                ).all()
                                if found_events:
                                    event_registrations = found_events
                                    break
                    except:
                        pass
        
        payment_data['event_registrations'] = event_registrations
        
        # Obtener descuentos aplicados
        discount_applications = DiscountApplication.query.filter_by(payment_id=payment.id).all()
        payment_data['discount_applications'] = discount_applications
        
        # Extraer items comprados del historial
        for transaction in history_transactions:
            try:
                if transaction.payload:
                    payload = json.loads(transaction.payload)
                    if 'items' in payload:
                        payment_data['purchased_items'] = payload['items']
                    if 'discount_breakdown' in payload:
                        payment_data['discount_breakdown'] = payload['discount_breakdown']
            except:
                pass
            
            # Si es una transacción de compra, obtener items del result
            if 'Compra realizada' in transaction.action:
                try:
                    if transaction.result:
                        result = json.loads(transaction.result)
                        if 'subscriptions' in result:
                            payment_data['subscriptions_info'] = result['subscriptions']
                        if 'events' in result:
                            # Obtener eventos desde los IDs del historial
                            event_ids = [e.get('event_id') for e in result['events']]
                            if event_ids:
                                event_registrations = EventRegistration.query.filter(
                                    EventRegistration.event_id.in_(event_ids),
                                    EventRegistration.user_id == current_user.id
                                ).all()
                                payment_data['event_registrations'] = event_registrations
                except:
                    pass
        
        # Si no hay items en el historial, intentar obtenerlos del payment_metadata
        if not payment_data['purchased_items'] and payment.payment_metadata:
            try:
                metadata = json.loads(payment.payment_metadata)
                if 'items' in metadata:
                    payment_data['purchased_items'] = metadata['items']
            except:
                pass
        
        # Agregar información de historial de transacciones
        payment_data['history_transactions'] = [
            {
                'id': t.id,
                'action': t.action,
                'timestamp': t.timestamp,
                'status': t.status
            }
            for t in history_transactions
        ]
        
        payments_with_details.append(payment_data)
        
        # Para pagos pendientes
        if payment.status in ['pending', 'awaiting_confirmation'] and payment.created_at:
            time_elapsed = (current_time - payment.created_at).total_seconds() / 60
            if time_elapsed > 5:  # Más de 5 minutos
                hours = int(time_elapsed / 60)
                minutes = int(time_elapsed % 60)
                if hours > 0:
                    time_elapsed_str = f"{hours}h {minutes}m"
                else:
                    time_elapsed_str = f"{minutes}m"
                
                long_pending_payments.append({
                    'payment': payment,
                    'time_elapsed': time_elapsed,
                    'time_elapsed_str': time_elapsed_str
                })
    
    return render_template('payments_history.html',
                         payments=payments_with_details,
                         status_counts=status_counts,
                         long_pending_payments=long_pending_payments,
                         current_time=current_time)

@app.route('/benefits')
@login_required
def benefits():
    """Página de beneficios"""
    active_membership = current_user.get_active_membership()
    if not active_membership:
        flash('Necesitas una membresía activa para acceder a los beneficios.', 'warning')
        return redirect(url_for('membership'))
    
    benefits = Benefit.query.filter_by(
        membership_type=active_membership.membership_type,
        is_active=True
    ).all()
    
    return render_template('benefits.html', benefits=benefits)

@app.route('/profile')
@login_required
def profile():
    """Perfil del usuario"""
    return render_template('profile.html')

@app.route('/profile/upload-photo', methods=['POST'])
@login_required
def upload_profile_photo():
    """Subir foto de perfil del usuario"""
    try:
        if 'photo' not in request.files:
            return jsonify({'success': False, 'error': 'No se proporcionó ninguna imagen'}), 400
        
        file = request.files['photo']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionó ningún archivo'}), 400
        
        if file and allowed_file(file.filename):
            # Validar que sea una imagen
            if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                return jsonify({'success': False, 'error': 'Formato de archivo no válido. Solo se permiten imágenes (PNG, JPG, JPEG, GIF, WEBP)'}), 400
            
            # Crear directorio si no existe
            upload_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'uploads', 'profiles')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generar nombre único para el archivo
            file_ext = os.path.splitext(file.filename)[1]
            filename = f"{current_user.id}_{int(datetime.utcnow().timestamp())}{file_ext}"
            filepath = os.path.join(upload_dir, filename)
            
            # Guardar el archivo
            file.save(filepath)
            
            # Eliminar foto anterior si existe
            if current_user.profile_picture:
                old_filepath = os.path.join(upload_dir, current_user.profile_picture)
                if os.path.exists(old_filepath):
                    try:
                        os.remove(old_filepath)
                    except:
                        pass  # Ignorar errores al eliminar archivo antiguo
            
            # Actualizar en la base de datos
            current_user.profile_picture = filename
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'message': 'Foto de perfil actualizada correctamente',
                'photo_url': current_user.get_profile_picture_url()
            })
        else:
            return jsonify({'success': False, 'error': 'Formato de archivo no permitido'}), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Error al subir la foto: {str(e)}'}), 500

@app.route('/profile/remove-photo', methods=['POST'])
@login_required
def remove_profile_photo():
    """Eliminar foto de perfil del usuario"""
    try:
        if current_user.profile_picture:
            # Eliminar archivo físico
            upload_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'uploads', 'profiles')
            filepath = os.path.join(upload_dir, current_user.profile_picture)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass
            
            # Actualizar en la base de datos
            current_user.profile_picture = None
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'message': 'Foto de perfil eliminada correctamente'
            })
        else:
            return jsonify({'success': False, 'error': 'No hay foto de perfil para eliminar'}), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Error al eliminar la foto: {str(e)}'}), 500

@app.route('/services')
@login_required
def services():
    """Módulo de Servicios"""
    active_membership = current_user.get_active_membership()
    membership_type = active_membership.membership_type if active_membership else 'basic'
    
    # Obtener servicios desde BD agrupados por plan
    services_by_plan = {}
    plans_info = {
        'basic': {'name': 'GRATIS / BÁSICO', 'price': '$0', 'badge': 'Incluido con la membresía gratuita', 'color': 'bg-success'},
        'pro': {'name': 'PRO', 'price': '$60/año', 'badge': 'Plan recomendado', 'color': 'bg-info'},
        'premium': {'name': 'PREMIUM', 'price': '$120/año', 'badge': 'Más beneficios', 'color': 'bg-primary'},
        'deluxe': {'name': 'DE LUXE', 'price': '$200/año', 'badge': 'Experiencia completa', 'color': 'bg-warning text-dark'},
        'corporativo': {'name': 'CORPORATIVO', 'price': '$300/año', 'badge': 'Para empresas', 'color': 'bg-dark text-white'}
    }
    
    # Obtener todas las categorías activas
    categories = ServiceCategory.query.filter_by(is_active=True).order_by(ServiceCategory.display_order, ServiceCategory.name).all()
    
    # Obtener todos los servicios activos ordenados
    all_services = Service.query.filter_by(is_active=True).order_by(Service.display_order, Service.name).all()
    
    # Agrupar servicios por categoría primero, luego por plan
    services_by_category = {}
    services_without_category = []
    
    for service in all_services:
        if service.category_id and service.category:
            cat_id = service.category_id
            if cat_id not in services_by_category:
                services_by_category[cat_id] = {
                    'category': service.category,
                    'services_by_plan': {}
                }
            # Agregar servicio al plan correspondiente dentro de la categoría
            # (lógica similar a la anterior)
        else:
            services_without_category.append(service)
    
    # Agrupar servicios por plan (para compatibilidad con template actual)
    # Un servicio puede aparecer en múltiples planes si tiene reglas de precio para cada uno
    for service in all_services:
        # Obtener todas las reglas de precio activas para este servicio
        pricing_rules = ServicePricingRule.query.filter_by(
            service_id=service.id,
            is_active=True
        ).all()
        
        # Planes donde este servicio está disponible
        available_plans = set()
        
        # SIEMPRE incluir el membership_type base del servicio
        if service.membership_type:
            available_plans.add(service.membership_type)
        
        # Si tiene reglas de precio, agregar también esos planes
        if pricing_rules:
            for rule in pricing_rules:
                available_plans.add(rule.membership_type)
        
        # Calcular precio para el usuario actual (con descuento según su membresía)
        user_pricing = service.pricing_for_membership(membership_type)
        
        # Agregar el servicio a todos los planes donde está disponible
        # IMPORTANTE: Mostrar el precio con descuento según la membresía del usuario actual
        for plan_type in available_plans:
            if plan_type not in services_by_plan:
                services_by_plan[plan_type] = []
            
            # Para mostrar en la lista, usar el precio calculado según la membresía del usuario actual
            # Esto permite que el usuario vea el precio con descuento desde el inicio
            service_data = {
                'id': service.id,
                'name': service.name,
                'description': service.description,
                'icon': service.icon or 'fas fa-cog',
                'external_link': service.external_link,
                'base_price': service.base_price,
                'pricing': user_pricing,  # Precio con descuento según membresía del usuario actual
                'requires_diagnostic_appointment': service.requires_diagnostic_appointment if service.requires_diagnostic_appointment is not None else False,
                'appointment_type_id': service.appointment_type_id,
                'requires_appointment': service.requires_appointment(),
                'is_free': service.is_free_service(membership_type)
            }
            
            services_by_plan[plan_type].append(service_data)
    
    # Obtener todas las categorías activas para filtros
    categories = ServiceCategory.query.filter_by(is_active=True).order_by(ServiceCategory.display_order, ServiceCategory.name).all()
    
    return render_template('services.html', 
                         membership=active_membership,
                         services_by_plan=services_by_plan,
                         plans_info=plans_info,
                         categories=categories,
                         user_membership_type=membership_type,
                         membership_type=membership_type)  # Para usar en el template


@app.route('/services/<int:service_id>/request-appointment')
@login_required
def service_request_appointment(service_id):
    """
    Muestra el formulario para solicitar una cita de un servicio.
    """
    # Guardar URL de retorno ANTES de iniciar el proceso (punto de retorno seguro)
    # Prioridad: 1) Parámetro return_url, 2) Referrer, 3) Página de servicios
    return_url = request.args.get('return_url') or request.referrer or url_for('services')
    # Solo guardar si es una URL válida del mismo dominio (seguridad)
    if return_url and (return_url.startswith('/') or return_url.startswith(request.url_root)):
        session['appointment_return_url'] = return_url
    
    # Validar servicio
    service = Service.query.get_or_404(service_id)
    if not service.is_active:
        flash('Este servicio no está disponible.', 'error')
        return redirect(url_for('services'))
    
    # Verificar que el servicio requiere cita
    if not service.requires_appointment():
        flash('Este servicio no requiere cita.', 'info')
        return redirect(url_for('services'))
    
    # Verificar membresía activa
    membership = current_user.get_active_membership()
    if not membership:
        flash('Necesitas una membresía activa para solicitar citas.', 'warning')
        return redirect(url_for('services'))
    
    membership_type = membership.membership_type
    
    # Verificar si el servicio es gratuito
    if service.is_free_service(membership_type):
        flash('Este servicio es gratuito y no requiere cita con pago.', 'info')
        return redirect(url_for('services'))
    
    # Obtener tipo de cita asociado
    appointment_type = AppointmentType.query.get(service.appointment_type_id)
    if not appointment_type or not appointment_type.is_active:
        flash('El tipo de cita asociado no está disponible.', 'error')
        return redirect(url_for('services'))
    
    # Calcular precios y abono
    pricing = service.pricing_for_membership(membership_type)
    deposit_info = service.calculate_deposit(membership_type)
    
    # Obtener asesores asignados con información completa
    # Solo incluir asesores que tengan horarios configurados
    advisors_list = []
    advisors_with_schedules = set()
    
    for assignment in appointment_type.advisor_assignments:
        if assignment.is_active and assignment.advisor.is_active:
            advisor = assignment.advisor
            advisor_id = advisor.id
            
            # Verificar si tiene horarios configurados (específicos, generales o diarios)
            has_specific_availability = AdvisorServiceAvailability.query.filter_by(
                advisor_id=advisor_id,
                appointment_type_id=service.appointment_type_id,
                is_active=True
            ).first() is not None
            
            has_general_availability = AdvisorAvailability.query.filter_by(
                advisor_id=advisor_id,
                is_active=True
            ).first() is not None
            
            # Verificar disponibilidad diaria (configurada desde el calendario)
            # También verificar si hay slots generados (que se crean automáticamente desde disponibilidad)
            today = datetime.utcnow().date()
            future_date = today + timedelta(days=90)  # Verificar próximos 90 días
            
            # Verificar DailyServiceAvailability (disponibilidad diaria configurada)
            # DailyServiceAvailability está definido en este mismo archivo (app.py)
            has_daily_availability = False
            try:
                has_daily_availability = DailyServiceAvailability.query.filter(
                    DailyServiceAvailability.advisor_id == advisor_id,
                    DailyServiceAvailability.appointment_type_id == service.appointment_type_id,
                    DailyServiceAvailability.date >= today,
                    DailyServiceAvailability.date <= future_date,
                    DailyServiceAvailability.is_active == True
                ).first() is not None
            except Exception as e:
                # Si hay error, simplemente no considerar disponibilidad diaria
                print(f"Error verificando DailyServiceAvailability: {e}")
                has_daily_availability = False
            
            # También verificar si hay slots disponibles (generados desde disponibilidad)
            has_available_slots = AppointmentSlot.query.filter(
                AppointmentSlot.advisor_id == advisor_id,
                AppointmentSlot.appointment_type_id == service.appointment_type_id,
                AppointmentSlot.start_datetime >= datetime.utcnow(),
                AppointmentSlot.start_datetime <= datetime.utcnow() + timedelta(days=90),
                AppointmentSlot.is_available == True
            ).first() is not None
            
            # Solo incluir si tiene algún tipo de disponibilidad o slots disponibles
            if has_specific_availability or has_general_availability or has_daily_availability or has_available_slots:
                advisors_list.append({
                    'id': advisor.id,
                    'name': f"{advisor.user.first_name} {advisor.user.last_name}" if advisor.user else 'Asesor',
                    'bio': advisor.bio,
                    'specializations': advisor.specializations,
                    'photo_url': advisor.photo_url
                })
                advisors_with_schedules.add(advisor_id)
    
    # Si no hay asesores con horarios, mostrar error
    if not advisors_list:
        flash('Este servicio no tiene asesores con horarios configurados. Por favor, contacta al administrador.', 'error')
        return redirect(url_for('services'))
    
    # Validar anticipación mínima y máxima (inspirado en Odoo)
    # Valores por defecto: mínimo 24 horas de anticipación, máximo 90 días
    now = datetime.utcnow()
    min_schedule_hours = 24  # Mínimo 24 horas de anticipación
    max_schedule_days = 90   # Máximo 90 días hacia adelante
    
    min_datetime = now + timedelta(hours=min_schedule_hours)
    max_datetime = now + timedelta(days=max_schedule_days)
    
    # Obtener TODOS los slots disponibles para este servicio (sin filtrar por asesor)
    # Primero, generar slots para todos los asesores asignados si no hay suficientes
    for advisor_id in advisors_with_schedules:
        try:
            existing_slots_count = AppointmentSlot.query.filter(
                AppointmentSlot.advisor_id == advisor_id,
                AppointmentSlot.appointment_type_id == service.appointment_type_id,
                AppointmentSlot.start_datetime >= datetime.utcnow(),
                AppointmentSlot.start_datetime <= datetime.utcnow() + timedelta(days=30)
            ).count()
            
            if existing_slots_count < 10:
                try:
                    generate_slots_from_availability(advisor_id, service.appointment_type_id, days_ahead=30)
                except Exception as e:
                    # Si falla la generación de slots, continuar sin generar
                    print(f"Error generando slots para asesor {advisor_id}: {e}")
                    pass
        except Exception as e:
            print(f"Error verificando slots para asesor {advisor_id}: {e}")
            continue
    
    # Obtener todos los slots disponibles del servicio (con relaciones cargadas)
    from sqlalchemy.orm import joinedload
    available_slots = AppointmentSlot.query.options(
        joinedload(AppointmentSlot.advisor).joinedload(Advisor.user)
    ).filter(
        AppointmentSlot.appointment_type_id == service.appointment_type_id,
        AppointmentSlot.start_datetime >= datetime.utcnow(),
        AppointmentSlot.start_datetime <= datetime.utcnow() + timedelta(days=30),
        AppointmentSlot.is_available == True
    ).order_by(AppointmentSlot.start_datetime.asc()).limit(200).all()
    
    # Obtener asesor seleccionado (si viene en query param para filtrar)
    selected_advisor_id = request.args.get('advisor_id', type=int)
    
    # Preparar slots para JSON (con información del asesor)
    slots_data = []
    for slot in available_slots:
        try:
            advisor_name = 'Asesor'
            if slot.advisor:
                if slot.advisor.user:
                    advisor_name = f"{slot.advisor.user.first_name} {slot.advisor.user.last_name}"
                else:
                    advisor_name = f"Asesor #{slot.advisor.id}"
            
            slots_data.append({
                'id': slot.id,
                'advisor_id': slot.advisor_id,
                'advisor_name': advisor_name,
                'start_datetime': slot.start_datetime.isoformat() if slot.start_datetime else None,
                'end_datetime': slot.end_datetime.isoformat() if slot.end_datetime else None,
                'capacity': slot.capacity if slot.capacity else 1,
                'remaining_seats': slot.remaining_seats() if hasattr(slot, 'remaining_seats') else 1
            })
        except Exception as e:
            print(f"Error procesando slot {slot.id}: {e}")
            continue
    
    import json
    try:
        return render_template('services/request_appointment.html',
                             service=service,
                             appointment_type=appointment_type,
                             advisors=advisors_list,
                             selected_advisor_id=selected_advisor_id,
                             membership=membership,
                             pricing=pricing,
                             deposit_info=deposit_info,
                             available_slots_json=json.dumps(slots_data),
                             available_slots=available_slots,  # Mantener para compatibilidad
                             user=current_user)
    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f'Error al cargar la página de solicitud de cita: {str(e)}', 'error')
        return redirect(url_for('services'))


@app.route('/services/<int:service_id>/request-appointment', methods=['POST'])
@login_required
def service_request_appointment_submit(service_id):
    """
    Agrega el servicio con cita al carrito en lugar de procesar el pago directamente.
    """
    import json
    
    # Validar servicio
    service = Service.query.get_or_404(service_id)
    if not service.is_active or not service.requires_appointment():
        flash('Este servicio no está disponible para citas.', 'error')
        return redirect(url_for('services'))
    
    # Verificar membresía
    membership = current_user.get_active_membership()
    if not membership:
        flash('Necesitas una membresía activa.', 'warning')
        return redirect(url_for('services'))
    
    # Validar datos del formulario
    slot_id = request.form.get('slot_id', type=int)
    case_description = request.form.get('case_description', '').strip()
    
    # Validar descripción del caso
    if not case_description or len(case_description) < 20:
        flash('La descripción del caso debe tener al menos 20 caracteres.', 'error')
        return redirect(url_for('service_request_appointment', service_id=service_id))
    
    if len(case_description) > 1000:
        flash('La descripción del caso no puede exceder 1000 caracteres.', 'error')
        return redirect(url_for('service_request_appointment', service_id=service_id))
    
    # Validar slot
    if not slot_id:
        flash('Debes seleccionar un horario disponible.', 'error')
        return redirect(url_for('service_request_appointment', service_id=service_id))
    
    slot = AppointmentSlot.query.get_or_404(slot_id)
    
    # Verificar que el slot pertenece al tipo de cita del servicio
    if slot.appointment_type_id != service.appointment_type_id:
        flash('El horario seleccionado no corresponde a este servicio.', 'error')
        return redirect(url_for('service_request_appointment', service_id=service_id))
    
    # Verificar disponibilidad del slot
    if not slot.is_available or slot.remaining_seats() <= 0:
        flash('Este horario ya no está disponible. Por favor selecciona otro.', 'warning')
        return redirect(url_for('service_request_appointment', service_id=service_id))
    
    # Calcular precios
    membership_type = membership.membership_type
    pricing = service.pricing_for_membership(membership_type)
    final_price = pricing['final_price']
    
    # Preparar metadata para el carrito
    cart_metadata = {
        'service_id': service.id,
        'service_name': service.name,
        'slot_id': slot.id,
        'slot_datetime': slot.start_datetime.isoformat(),
        'case_description': case_description,
        'final_price': final_price,
        'appointment_type_id': service.appointment_type_id,
        'advisor_id': slot.advisor_id,
        'requires_appointment': True,
        'slot_end_datetime': slot.end_datetime.isoformat() if slot.end_datetime else None
    }
    
    # Agregar al carrito
    try:
        cart = add_to_cart(
            user_id=current_user.id,
            product_type='service',
            product_id=service.id,
            product_name=f"{service.name} - Cita",
            unit_price=int(final_price * 100),  # Convertir a centavos
            quantity=1,
            product_description=f"Servicio con cita agendada: {case_description[:100]}...",
            metadata=cart_metadata
        )
        
        flash('Servicio agregado al carrito exitosamente. Puedes continuar con el proceso de pago desde tu carrito.', 'success')
        return redirect(url_for('cart'))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error al agregar al carrito: {str(e)}', 'error')
        return redirect(url_for('service_request_appointment', service_id=service_id))


@app.route('/api/payments/<int:payment_id>/success')
@login_required
def service_payment_success_callback(payment_id):
    """
    Callback cuando un pago de servicio es exitoso. Crea el appointment.
    """
    import json
    
    payment = Payment.query.get_or_404(payment_id)
    
    # Verificar que el pago pertenece al usuario
    if payment.user_id != current_user.id:
        flash('No tienes permiso para acceder a este pago.', 'error')
        return redirect(url_for('services'))
    
    # Solo procesar si es un pago de servicio (service_appointment)
    if payment.membership_type != 'service_appointment':
        # Si no es de servicio, usar el callback genérico
        return redirect(url_for('payment_success_callback', payment_id=payment_id))
    
    # Verificar que el pago fue exitoso
    if payment.status not in ['succeeded', 'awaiting_confirmation']:
        flash('El pago no se ha completado aún.', 'warning')
        return redirect(url_for('payment_status', payment_id=payment_id))
    
    # Verificar que no se haya creado ya el appointment
    existing_appointment = Appointment.query.filter_by(payment_id=payment_id).first()
    if existing_appointment:
        flash('La cita ya fue creada anteriormente.', 'info')
        return redirect(url_for('appointments.appointments_home'))
    
    # Extraer metadata
    try:
        metadata = json.loads(payment.payment_metadata)
    except:
        flash('Error al procesar los datos del pago.', 'error')
        return redirect(url_for('services'))
    
    service_id = metadata.get('service_id')
    slot_id = metadata.get('slot_id')
    case_description = metadata.get('case_description')
    final_price = metadata.get('final_price', 0.0)
    deposit_amount = metadata.get('deposit_amount', 0.0)
    
    # Validar que el servicio y slot aún existen
    service = Service.query.get(service_id)
    slot = AppointmentSlot.query.get(slot_id)
    
    if not service or not slot:
        flash('Error: El servicio o horario seleccionado ya no está disponible.', 'error')
        return redirect(url_for('services'))
    
    # Verificar disponibilidad del slot
    if not slot.is_available or slot.remaining_seats() <= 0:
        flash('El horario seleccionado ya no está disponible. Contacta a soporte.', 'error')
        return redirect(url_for('services'))
    
    # Determinar estado de pago
    if deposit_amount >= final_price:
        payment_status = 'paid'
    else:
        payment_status = 'partial'
    
    # Obtener membresía
    membership = current_user.get_active_membership()
    membership_type = membership.membership_type if membership else None
    
    # Calcular precios finales
    pricing = service.pricing_for_membership(membership_type)
    
    # Crear Appointment
    appointment = Appointment(
        appointment_type_id=service.appointment_type_id,
        advisor_id=slot.advisor_id,
        slot_id=slot.id,
        service_id=service.id,
        payment_id=payment.id,
        user_id=current_user.id,
        membership_type=membership_type,
        start_datetime=slot.start_datetime,
        end_datetime=slot.end_datetime,
        status='pending',  # Esperando confirmación del asesor
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
    db.session.commit()
    
    # Log actividad
    ActivityLog.log_activity(
        current_user.id,
        'service_appointment_created',
        'appointment',
        appointment.id,
        f'Cita creada para servicio {service.name} - Referencia: {appointment.reference}',
        request
    )
    
    flash(f'¡Cita agendada exitosamente! Referencia: {appointment.reference}', 'success')
    
    # Retornar a la URL guardada antes de iniciar el proceso (si existe)
    # Si no hay return_url guardado, usar comportamiento por defecto
    return_url = session.pop('appointment_return_url', None)
    if return_url and (return_url.startswith('/') or return_url.startswith(request.url_root)):
        return redirect(return_url)
    
    # Fallback seguro: comportamiento original
    return redirect(url_for('appointments.appointments_home'))


@app.route('/office365')
@login_required
def office365():
    """Módulo de Office 365"""
    active_membership = current_user.get_active_membership()
    return render_template('office365.html', membership=active_membership)

@app.route('/foros')
@login_required
def foros():
    """Módulo de Foros para miembros"""
    active_membership = current_user.get_active_membership()
    if not active_membership:
        flash('Necesitas una membresía activa para acceder a los Foros.', 'warning')
        return redirect(url_for('membership'))
    return render_template('foros.html', membership=active_membership)

@app.route('/grupos')
@login_required
def grupos():
    """Módulo de Grupos para miembros"""
    active_membership = current_user.get_active_membership()
    if not active_membership:
        flash('Necesitas una membresía activa para acceder a los Grupos.', 'warning')
        return redirect(url_for('membership'))
    return render_template('grupos.html', membership=active_membership)

@app.route('/settings')
@login_required
def settings():
    """Módulo de Configuración"""
    return render_template('settings.html')

@app.route('/notifications')
@app.route('/notifications')
@login_required
def notifications():
    """Módulo de Notificaciones"""
    try:
        # Obtener todas las notificaciones del usuario
        user_notifications = Notification.query.filter_by(
            user_id=current_user.id
        ).order_by(Notification.created_at.desc()).all()
        
        # Contar no leídas
        unread_count = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).count()
        
        # Logging para debug
        print(f"📬 Usuario {current_user.id} ({current_user.email}):")
        print(f"   Total notificaciones: {len(user_notifications)}")
        print(f"   No leídas: {unread_count}")
        if user_notifications:
            for n in user_notifications[:5]:  # Mostrar primeras 5
                print(f"   - ID {n.id}: {n.title} (leída: {n.is_read})")
        
        return render_template('notifications.html', 
                             notifications=user_notifications,
                             unread_count=unread_count)
    except Exception as e:
        print(f"❌ Error en endpoint /notifications: {e}")
        import traceback
        traceback.print_exc()
        # Retornar página vacía en caso de error
        return render_template('notifications.html', 
                             notifications=[],
                             unread_count=0)

@app.route('/help')
@login_required
def help():
    """Módulo de Ayuda"""
    return render_template('help.html')

# Rutas de pago
@app.route('/checkout')
@login_required
@email_verified_required
def checkout():
    """Página de checkout para pagos desde el carrito"""
    cart = get_or_create_cart(current_user.id)
    
    if cart.get_items_count() == 0:
        flash('Tu carrito está vacío. Agrega productos antes de proceder al pago.', 'warning')
        return redirect(url_for('cart'))
    
    # Obtener desglose de descuentos
    discount_breakdown = cart.get_discount_breakdown()
    total_amount = discount_breakdown['final_total']
    
    # Obtener métodos de pago disponibles
    payment_methods = PAYMENT_METHODS if PAYMENT_PROCESSORS_AVAILABLE else {'stripe': 'Stripe (Tarjeta de Crédito)'}
    
    return render_template('checkout.html', 
                         cart=cart,
                         total_amount=total_amount,
                         discount_breakdown=discount_breakdown,
                         stripe_publishable_key=STRIPE_PUBLISHABLE_KEY if stripe else None,
                         payment_methods=payment_methods)

@app.route('/checkout/<membership_type>')
@login_required
def checkout_membership(membership_type):
    """Página de checkout directo para membresía (compatibilidad con sistema anterior)"""
    if membership_type not in ['basic', 'pro', 'premium', 'deluxe', 'corporativo']:
        flash('Tipo de membresía inválido.', 'error')
        return redirect(url_for('membership'))
    
    # Agregar al carrito automáticamente
    prices = {
        'basic': 0,
        'pro': 6000,
        'premium': 12000,
        'deluxe': 20000
    }
    
    # Generar ID único basado en el tipo de membresía
    import hashlib
    product_id = int(hashlib.md5(membership_type.encode()).hexdigest()[:8], 16) % 1000000
    
    add_to_cart(
        current_user.id,
        'membership',
        product_id,
        f"Membresía {membership_type.title()}",
        prices[membership_type],
        1,
        f"Plan de membresía {membership_type.title()} - 1 año",
        {'membership_type': membership_type}
    )
    
    # Redirigir al checkout del carrito
    return redirect(url_for('checkout'))

@app.route('/api/cart/apply-discount-code', methods=['POST'])
@login_required
def api_apply_discount_code():
    """API para aplicar código de descuento al carrito"""
    try:
        data = request.get_json()
        code = data.get('code', '').strip().upper()
        
        if not code:
            return jsonify({'success': False, 'error': 'El código es requerido'}), 400
        
        cart = get_or_create_cart(current_user.id)
        success, message = cart.apply_discount_code(code)
        
        if success:
            # Recalcular desglose
            breakdown = cart.get_discount_breakdown()
            return jsonify({
                'success': True,
                'message': message,
                'breakdown': {
                    'subtotal': breakdown['subtotal'],
                    'master_discount_amount': breakdown['master_discount']['amount'] if breakdown['master_discount'] else 0,
                    'code_discount_amount': breakdown['code_discount']['amount'] if breakdown['code_discount'] else 0,
                    'total_discount': breakdown['total_discount'],
                    'final_total': breakdown['final_total']
                }
            })
        else:
            return jsonify({'success': False, 'error': message}), 400
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def _make_absolute_url(url):
    """
    Convierte una URL relativa a absoluta si es necesario.
    Retorna None si la URL no es válida.
    """
    if not url:
        return None
    if url.startswith('http://') or url.startswith('https://'):
        return url
    if url.startswith('/'):
        return request.url_root.rstrip('/') + url
    return None


def redirect_to_stripe_checkout(payment, service, slot):
    """
    Crea una sesión de Stripe Checkout y redirige al usuario.
    """
    if not STRIPE_AVAILABLE or not stripe:
        flash('El método de pago con tarjeta no está disponible.', 'error')
        return redirect(url_for('service_request_appointment', service_id=service.id))
    
    try:
        # Crear sesión de checkout
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'Cita: {service.name}',
                        'description': f'Abono para cita el {slot.start_datetime.strftime("%d/%m/%Y %H:%M")}'
                    },
                    'unit_amount': int(payment.amount),  # Ya está en centavos
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('service_payment_success_callback', payment_id=payment.id, _external=True),
            # Cancel URL: usar return_url guardado si existe (convertir a absoluto), sino usar la página de solicitud
            cancel_url=_make_absolute_url(session.get('appointment_return_url')) or url_for('service_request_appointment', service_id=service.id, _external=True),
            metadata={
                'payment_id': str(payment.id),
                'service_id': str(service.id),
                'slot_id': str(slot.id)
            }
        )
        
        # Guardar referencia de Stripe
        payment.payment_reference = checkout_session.id
        payment.payment_url = checkout_session.url
        db.session.commit()
        
        return redirect(checkout_session.url)
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error al crear la sesión de pago: {str(e)}', 'error')
        return redirect(url_for('service_request_appointment', service_id=service.id))


def generate_external_payment_url(payment, payment_method):
    """
    Genera URL para pagos externos (Banco General, Yappy).
    """
    # URL base del sistema
    base_url = request.url_root.rstrip('/')
    
    # URL de callback
    callback_url = url_for('payment_success_callback', payment_id=payment.id, _external=True)
    cancel_url = url_for('services', _external=True)
    
    # Generar URL según el método
    if payment_method == 'banco_general':
        # TODO: Integrar con API de Banco General
        # Por ahora, retornar URL de confirmación manual
        return url_for('payment_status', payment_id=payment.id, _external=True)
    
    elif payment_method == 'yappy':
        # TODO: Integrar con API de Yappy
        # Por ahora, retornar URL de confirmación manual
        return url_for('payment_status', payment_id=payment.id, _external=True)
    
    return callback_url


@app.route('/api/cart/remove-discount-code', methods=['POST'])
@login_required
def api_remove_discount_code():
    """API para remover código de descuento del carrito"""
    try:
        cart = get_or_create_cart(current_user.id)
        cart.remove_discount_code()
        
        # Recalcular desglose
        breakdown = cart.get_discount_breakdown()
        return jsonify({
            'success': True,
            'message': 'Código de descuento removido',
            'breakdown': {
                'subtotal': breakdown['subtotal'],
                'master_discount_amount': breakdown['master_discount']['amount'] if breakdown['master_discount'] else 0,
                'code_discount_amount': 0,
                'total_discount': breakdown['total_discount'],
                'final_total': breakdown['final_total']
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/create-payment-intent', methods=['POST'])
@email_verified_required
def create_payment_intent():
    """Crear Payment Intent o iniciar pago con el método seleccionado"""
    try:
        # Manejar tanto JSON como FormData (para métodos manuales con archivos)
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        
        payment_method = data.get('payment_method', 'stripe')
        
        # Manejar archivo de comprobante si existe (métodos manuales)
        receipt_file = None
        receipt_filename = None
        receipt_url = None
        ocr_data = None
        ocr_status = 'pending'
        
        if 'receipt' in request.files:
            file = request.files['receipt']
            if file and file.filename != '' and allowed_file(file.filename):
                # Generar nombre único para el archivo
                import secrets
                file_ext = file.filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{current_user.id}_{secrets.token_hex(8)}.{file_ext}"
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(file_path)
                receipt_filename = file.filename
                receipt_url = f"/static/uploads/receipts/{unique_filename}"
                print(f"✅ Comprobante guardado: {receipt_url}")
                
                # Procesar con OCR si está disponible
                try:
                    from ocr_processor import get_ocr_processor
                    ocr_processor = get_ocr_processor()
                    if ocr_processor:
                        print(f"🔄 Procesando documento con OCR...")
                        extracted_data, ocr_error = ocr_processor.extract_payment_data(file_path)
                        if extracted_data:
                            ocr_data = json.dumps(extracted_data)
                            print(f"✅ OCR completado. Datos extraídos: {extracted_data}")
                        elif ocr_error:
                            print(f"⚠️ Error en OCR: {ocr_error}")
                except Exception as e:
                    print(f"⚠️ Error procesando OCR: {e}")
                    import traceback
                    traceback.print_exc()
        
        cart = get_or_create_cart(current_user.id)
        
        if cart.get_items_count() == 0:
            return jsonify({'error': 'El carrito está vacío'}), 400
        
        # Usar el total con descuentos aplicados
        discount_breakdown = cart.get_discount_breakdown()
        total_amount = discount_breakdown['final_total']
        
        # Validar método de pago
        if payment_method not in PAYMENT_METHODS:
            return jsonify({'error': f'Método de pago no válido: {payment_method}'}), 400
        
        # Obtener procesador de pago
        if not PAYMENT_PROCESSORS_AVAILABLE:
            return jsonify({'error': 'Sistema de pagos no disponible'}), 500
        
        # Obtener configuración de pagos de la BD
        payment_config = PaymentConfig.get_active_config()
        processor = get_payment_processor(payment_method, payment_config)
        
        # Crear metadata para el pago
        import json
        metadata = {
            'user_id': current_user.id,
            'cart_id': cart.id,
            'items_count': cart.get_items_count()
        }
        
        # Crear pago con el procesador
        success, payment_data, error_message = processor.create_payment(
            amount=total_amount,
            currency='usd',
            metadata=metadata
        )
        
        if not success:
            return jsonify({'error': error_message or 'Error al crear el pago'}), 400
        
        # Detectar si estamos en modo demo
        is_demo_mode = payment_data.get('demo_mode', False)
        
        # Si es modo demo, también verificar si no hay credenciales configuradas
        if not is_demo_mode:
            if payment_method == 'stripe':
                if payment_config:
                    has_stripe_key = bool(payment_config.get_stripe_secret_key() and 
                                        not payment_config.get_stripe_secret_key().startswith('sk_test_your_'))
                else:
                    has_stripe_key = bool(os.getenv('STRIPE_SECRET_KEY') and 
                                        not os.getenv('STRIPE_SECRET_KEY', '').startswith('sk_test_your_'))
                is_demo_mode = not has_stripe_key
            elif payment_method == 'paypal':
                if payment_config:
                    has_paypal_creds = bool(payment_config.get_paypal_client_id() and payment_config.get_paypal_client_secret())
                else:
                    has_paypal_creds = bool(os.getenv('PAYPAL_CLIENT_ID') and os.getenv('PAYPAL_CLIENT_SECRET'))
                is_demo_mode = not has_paypal_creds
            else:
                # Métodos manuales siempre están en modo demo hasta que se configuren APIs
                is_demo_mode = True
        
        # Validar datos OCR si existen
        ocr_verified = False
        if ocr_data:
            try:
                extracted = json.loads(ocr_data)
                expected_amount = total_amount / 100.0  # Convertir de centavos a dólares
                extracted_amount = extracted.get('amount')
                
                # Verificar si el monto coincide (con tolerancia de 0.01)
                if extracted_amount and abs(extracted_amount - expected_amount) < 0.01:
                    ocr_status = 'verified'
                    ocr_verified = True
                    print(f"✅ Monto verificado: ${extracted_amount} coincide con ${expected_amount}")
                else:
                    ocr_status = 'needs_review'
                    print(f"⚠️ Monto no coincide: OCR=${extracted_amount}, Esperado=${expected_amount}")
            except Exception as e:
                print(f"⚠️ Error validando OCR: {e}")
                ocr_status = 'needs_review'
        
        # Determinar estado inicial del pago
        # Si es método manual con OCR verificado, aprobar automáticamente
        # Si es modo demo sin OCR, aprobar automáticamente
        # Si OCR necesita revisión, dejar en pending
        if ocr_verified:
            initial_status = 'succeeded'
        elif is_demo_mode and not receipt_url:  # Demo sin archivo
            initial_status = 'succeeded'
        else:
            initial_status = 'pending'
        
        # Guardar pago en la base de datos
        payment = Payment(
            user_id=current_user.id,
            payment_method=payment_method,
            payment_reference=payment_data.get('payment_reference', ''),
            amount=total_amount,
            currency='usd',
            status=initial_status,
            membership_type='cart',
            payment_url=payment_data.get('payment_url'),
            payment_metadata=json.dumps(metadata),
            receipt_url=receipt_url,
            receipt_filename=receipt_filename,
            ocr_data=ocr_data,
            ocr_status=ocr_status
        )
        
        if initial_status == 'succeeded':
            payment.paid_at = datetime.utcnow()
            if ocr_verified:
                payment.ocr_verified_at = datetime.utcnow()
        
        db.session.add(payment)
        db.session.commit()
        
        # Registrar creación de pago en historial
        try:
            from history_module import HistoryLogger
            cart_items = []
            for item in cart.items:
                cart_items.append({
                    'product_type': item.product_type,
                    'product_id': item.product_id,
                    'product_name': item.product_name,
                    'quantity': item.quantity,
                    'unit_price': item.unit_price,
                    'total_price': item.unit_price * item.quantity
                })
            
            HistoryLogger.log_user_action(
                user_id=current_user.id,
                action=f"Pago creado - {payment_method.upper()} - ${total_amount/100:.2f}",
                status=initial_status,
                context={"app": "web", "screen": "checkout", "module": "payment"},
                payload={
                    "payment_id": payment.id,
                    "payment_method": payment_method,
                    "amount": total_amount,
                    "currency": "usd",
                    "cart_id": cart.id,
                    "items_count": cart.get_items_count(),
                    "items": cart_items,
                    "discount_breakdown": discount_breakdown,
                    "demo_mode": is_demo_mode,
                    "ocr_status": ocr_status,
                    "ocr_verified": ocr_verified
                },
                result={
                    "payment_id": payment.id,
                    "status": initial_status,
                    "payment_reference": payment.payment_reference
                },
                visibility="both"
            )
        except Exception as e:
            print(f"⚠️ Error registrando creación de pago en historial: {e}")
        
        # Si el pago está aprobado (demo o OCR verificado), procesar el carrito inmediatamente
        if initial_status == 'succeeded':
            try:
                process_cart_after_payment(cart, payment)
                cart.clear()
                db.session.commit()
                print(f"✅ Pago en modo demo procesado exitosamente. Payment ID: {payment.id}")
                
                # Enviar webhook a Odoo (no bloquea si falla)
                try:
                    send_payment_to_odoo(payment, current_user, cart)
                except Exception as e:
                    print(f"⚠️ Error enviando pago a Odoo (no crítico): {e}")
            except Exception as e:
                print(f"⚠️ Error procesando carrito en modo demo: {e}")
                import traceback
                traceback.print_exc()
                db.session.rollback()
        
        # Si OCR necesita revisión, enviar notificaciones después del commit
        if ocr_status == 'needs_review':
            try:
                send_ocr_review_notifications(payment, current_user, json.loads(ocr_data) if ocr_data else None)
            except Exception as e:
                print(f"⚠️ Error enviando notificaciones OCR: {e}")
        
        # Preparar respuesta según el método
        response_data = {
            'payment_id': payment.id,
            'payment_method': payment_method,
            'amount': total_amount,
            'status': initial_status,
            'demo_mode': is_demo_mode,
            'ocr_data': json.loads(ocr_data) if ocr_data else None,
            'ocr_status': ocr_status,
            'ocr_verified': ocr_verified
        }
        
        # Agregar datos específicos según el método
        if payment_method == 'stripe':
            response_data['client_secret'] = payment_data.get('client_secret', 'demo_client_secret')
        elif payment_method == 'paypal':
            response_data['payment_url'] = payment_data.get('payment_url')
            response_data['order_id'] = payment_data.get('payment_reference')
        elif payment_method == 'banco_general':
            response_data['bank_account'] = payment_data.get('bank_account')
            response_data['payment_reference'] = payment_data.get('payment_reference')
            response_data['manual'] = True
        elif payment_method == 'yappy':
            response_data['yappy_info'] = payment_data.get('yappy_info')
            response_data['payment_reference'] = payment_data.get('payment_reference')
            response_data['manual'] = True
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error en create_payment_intent: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Ruta legacy para compatibilidad (solo Stripe)
@app.route('/create-payment-intent-legacy', methods=['POST'])
@email_verified_required
def create_payment_intent_legacy():
    """Crear Payment Intent de Stripe desde el carrito (método legacy)"""
    try:
        cart = get_or_create_cart(current_user.id)
        
        if cart.get_items_count() == 0:
            return jsonify({'error': 'El carrito está vacío'}), 400
        
        total_amount = cart.get_total()
        
        # Modo Demo - Simular pago exitoso
        demo_mode = True  # Cambiar a False cuando tengas Stripe configurado
        
        if demo_mode:
            # Simular Payment Intent
            fake_intent_id = f"pi_demo_{current_user.id}_{datetime.utcnow().timestamp()}"
            
            # Guardar en la base de datos
            payment = Payment(
                user_id=current_user.id,
                payment_method='stripe',
                payment_reference=fake_intent_id,
                amount=total_amount,
                membership_type='cart',  # Indica que es un pago del carrito
                status='succeeded'  # Simular pago exitoso
            )
            db.session.add(payment)
            db.session.commit()
            
            # Procesar cada item del carrito
            subscriptions_created = []
            items_processed = 0
            import json
            
            # Crear copia de la lista antes de procesar
            cart_items_list = list(cart.items)
            
            for item in cart_items_list:
                items_processed += 1
                
                if item.product_type == 'membership':
                    metadata = json.loads(item.item_metadata) if item.item_metadata else {}
                    membership_type = metadata.get('membership_type', 'basic')
                    
                    # Crear suscripción
                    end_date = datetime.utcnow() + timedelta(days=365)
                    subscription = Subscription(
                        user_id=current_user.id,
                        payment_id=payment.id,
                        membership_type=membership_type,
                        status='active',
                        end_date=end_date
                    )
                    db.session.add(subscription)
                    subscriptions_created.append(subscription)
                
                elif item.product_type == 'event':
                    # Registrar al evento (si existe la funcionalidad)
                    metadata = json.loads(item.item_metadata) if item.item_metadata else {}
                    event_id = metadata.get('event_id')
                    if event_id:
                        # Aquí se podría registrar al evento automáticamente
                        pass
                
            
            db.session.commit()
            
            # Vaciar el carrito después del pago exitoso
            cart.clear()
            
            return jsonify({
                'client_secret': 'demo_client_secret',
                'payment_id': payment.id,
                'demo_mode': True,
                'items_processed': items_processed
            })
        else:
            # Modo real con Stripe
            # Crear metadata con información del carrito
            import json
            cart_metadata = {
                'user_id': current_user.id,
                'items_count': cart.get_items_count(),
                'items': [item.to_dict() for item in cart.items]
            }
            
            intent = stripe.PaymentIntent.create(
                amount=total_amount,
                currency='usd',
                metadata={
                    'user_id': str(current_user.id),
                    'cart_id': str(cart.id),
                    'items': json.dumps(cart_metadata['items'])
                }
            )
            
            # Guardar en la base de datos
            payment = Payment(
                user_id=current_user.id,
                payment_method='stripe',
                payment_reference=intent.id,
                amount=total_amount,
                membership_type='cart',
                status='pending'
            )
            db.session.add(payment)
            db.session.commit()
            
            return jsonify({
                'client_secret': intent.client_secret,
                'payment_id': payment.id,
                'demo_mode': False
            })
        
    except Exception as e:
        print(f"Error en create_payment_intent: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

@app.route('/payment-success')
@login_required
def payment_success():
    """Página de éxito del pago"""
    payment_id = request.args.get('payment_id')
    if payment_id:
        payment = Payment.query.get(payment_id)
        if payment and payment.user_id == current_user.id:
            # Registrar confirmación de pago en historial si cambió de estado
            if payment.status == 'succeeded':
                try:
                    from history_module import HistoryLogger
                    HistoryLogger.log_user_action(
                        user_id=current_user.id,
                        action=f"Pago confirmado - {payment.payment_method.upper()} - ${payment.amount/100:.2f}",
                        status="success",
                        context={"app": "web", "screen": "payment_success", "module": "payment"},
                        payload={
                            "payment_id": payment.id,
                            "payment_method": payment.payment_method,
                            "amount": payment.amount,
                            "payment_reference": payment.payment_reference
                        },
                        result={
                            "payment_id": payment.id,
                            "status": "succeeded",
                            "paid_at": payment.paid_at.isoformat() if payment.paid_at else None
                        },
                        visibility="both"
                    )
                except Exception as e:
                    print(f"⚠️ Error registrando confirmación de pago en historial: {e}")
            
            # Procesar items del carrito si el pago fue exitoso y aún no se procesó
            if payment.status == 'succeeded':
                cart = get_or_create_cart(current_user.id)
                
                # Verificar si el carrito ya fue procesado (tiene items)
                # Si el carrito está vacío, significa que ya fue procesado en modo demo
                if cart.get_items_count() > 0:
                    try:
                        process_cart_after_payment(cart, payment)
                        cart.clear()
                        db.session.commit()
                        print(f"✅ Carrito procesado en payment_success para Payment ID: {payment.id}")
                    except Exception as e:
                        print(f"⚠️ Error procesando carrito en payment_success: {e}")
                        import traceback
                        traceback.print_exc()
                        db.session.rollback()
                else:
                    print(f"ℹ️ Carrito ya procesado previamente para Payment ID: {payment.id}")
                
                # Enviar webhook a Odoo (no bloquea si falla)
                try:
                    send_payment_to_odoo(payment, current_user, cart)
                except Exception as e:
                    print(f"⚠️ Error enviando pago a Odoo (no crítico): {e}")
            
            return render_template('payment_success.html', payment=payment)
    
    flash('Información de pago no encontrada.', 'error')
    return redirect(url_for('membership'))

@app.route('/payment/paypal/return', methods=['GET'])
@login_required
def paypal_return():
    """Callback de retorno de PayPal después del pago"""
    token = request.args.get('token')
    payment_id = request.args.get('payment_id')
    
    if not token or not payment_id:
        flash('Error en el proceso de pago de PayPal.', 'error')
        return redirect(url_for('checkout'))
    
    payment = Payment.query.get(payment_id)
    if not payment or payment.user_id != current_user.id:
        flash('Pago no encontrado.', 'error')
        return redirect(url_for('checkout'))
    
    # Capturar el pago de PayPal
    if PAYMENT_PROCESSORS_AVAILABLE:
        try:
            payment_config = PaymentConfig.get_active_config()
            processor = get_payment_processor('paypal', payment_config)
            # PayPal ya captura automáticamente, solo verificamos
            success, status, payment_data = processor.verify_payment(token)
            
            if success and status == 'succeeded':
                payment.status = 'succeeded'
                payment.paid_at = datetime.utcnow()
                db.session.commit()
                
                # Registrar confirmación de pago en historial
                try:
                    from history_module import HistoryLogger
                    HistoryLogger.log_user_action(
                        user_id=current_user.id,
                        action=f"Pago confirmado - PayPal - ${payment.amount/100:.2f}",
                        status="success",
                        context={"app": "web", "screen": "paypal_return", "module": "payment"},
                        payload={
                            "payment_id": payment.id,
                            "payment_method": "paypal",
                            "amount": payment.amount,
                            "payment_reference": payment.payment_reference,
                            "token": token
                        },
                        result={
                            "payment_id": payment.id,
                            "status": "succeeded",
                            "paid_at": payment.paid_at.isoformat() if payment.paid_at else None
                        },
                        visibility="both"
                    )
                except Exception as e:
                    print(f"⚠️ Error registrando confirmación de pago PayPal en historial: {e}")
                
                # Procesar carrito
                cart = get_or_create_cart(current_user.id)
                process_cart_after_payment(cart, payment)
                cart.clear()
                db.session.commit()
                
                # Enviar webhook a Odoo (no bloquea si falla)
                try:
                    send_payment_to_odoo(payment, current_user, cart)
                except Exception as e:
                    print(f"⚠️ Error enviando pago a Odoo (no crítico): {e}")
                
                return redirect(url_for('payment_success', payment_id=payment.id))
            else:
                payment.status = 'failed'
                db.session.commit()
                flash('El pago no se pudo completar.', 'error')
        except Exception as e:
            print(f"Error procesando retorno de PayPal: {e}")
            flash('Error procesando el pago.', 'error')
    
    return redirect(url_for('checkout'))

@app.route('/payment/paypal/cancel', methods=['GET'])
@login_required
def paypal_cancel():
    """Callback de cancelación de PayPal"""
    payment_id = request.args.get('payment_id')
    
    if payment_id:
        payment = Payment.query.get(payment_id)
        if payment and payment.user_id == current_user.id:
            payment.status = 'cancelled'
            db.session.commit()
    
    flash('Pago cancelado.', 'warning')
    return redirect(url_for('checkout'))

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
                        
                        # Crear Appointment
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
                            status='pending',  # Esperando confirmación del asesor
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

@app.route('/payment-cancel')
@login_required
def payment_cancel():
    """Página de cancelación del pago"""
    flash('El pago fue cancelado. Puedes intentar nuevamente.', 'warning')
    return redirect(url_for('membership'))

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
    """Obtener o crear carrito para el usuario"""
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.session.add(cart)
        db.session.commit()
    return cart

def add_to_cart(user_id, product_type, product_id, product_name, unit_price, quantity=1, product_description=None, metadata=None):
    """Agregar producto al carrito"""
    cart = get_or_create_cart(user_id)
    
    # Verificar si el producto ya está en el carrito
    existing_item = CartItem.query.filter_by(
        cart_id=cart.id,
        product_type=product_type,
        product_id=product_id
    ).first()
    
    if existing_item:
        # Actualizar cantidad
        existing_item.quantity += quantity
        existing_item.updated_at = datetime.utcnow()
    else:
        # Crear nuevo item
        import json
        metadata_json = json.dumps(metadata) if metadata else None
        
        new_item = CartItem(
            cart_id=cart.id,
            product_type=product_type,
            product_id=product_id,
            product_name=product_name,
            product_description=product_description,
            unit_price=unit_price,
            quantity=quantity,
            item_metadata=metadata_json
        )
        db.session.add(new_item)
    
    cart.updated_at = datetime.utcnow()
    db.session.commit()
    return cart

# Rutas del Carrito de Compras
@app.route('/cart')
@login_required
def cart():
    """Ver carrito de compras"""
    cart = get_or_create_cart(current_user.id)
    return render_template('cart.html', cart=cart)

@app.route('/cart/add', methods=['POST'])
@login_required
@email_verified_required
def cart_add():
    """Agregar producto al carrito"""
    try:
        data = request.get_json() if request.is_json else request.form
        product_type = data.get('product_type')
        quantity = int(data.get('quantity', 1))
        
        # Validar tipo de producto
        if product_type not in ['membership', 'event', 'service']:
            return jsonify({'success': False, 'error': 'Tipo de producto inválido'}), 400
        
        # Si el usuario ya tiene membresía activa, verificar que no intente comprar otra membresía del mismo tipo
        if product_type == 'membership':
            active_membership = current_user.get_active_membership()
            if active_membership:
                membership_type_requested = data.get('membership_type')
                if membership_type_requested == active_membership.membership_type:
                    return jsonify({
                        'success': False, 
                        'error': f'Ya tienes una membresía {membership_type_requested.title()} activa'
                    }), 400
        
        # Obtener información del producto según su tipo
        product_name = ""
        product_description = ""
        unit_price = 0
        metadata = {}
        product_id = 0  # Inicializar product_id
        
        if product_type == 'membership':
            membership_type = data.get('membership_type')
            if not membership_type:
                return jsonify({'success': False, 'error': 'Tipo de membresía no especificado'}), 400
            
            prices = {
                'basic': 0,
                'pro': 6000,
                'premium': 12000,
                'deluxe': 20000
            }
            unit_price = prices.get(membership_type, 0)
            product_name = f"Membresía {membership_type.title()}"
            product_description = f"Plan de membresía {membership_type.title()} - 1 año"
            metadata = {'membership_type': membership_type}
            # Generar ID único basado en el tipo de membresía
            import hashlib
            product_id = int(hashlib.md5(membership_type.encode()).hexdigest()[:8], 16) % 1000000
            
            
        elif product_type == 'event':
            product_id = int(data.get('product_id', 0))
            if product_id == 0:
                return jsonify({'success': False, 'error': 'ID de evento no especificado'}), 400
            event = Event.query.get(product_id)
            if not event:
                return jsonify({'success': False, 'error': 'Evento no encontrado'}), 404
            
            # Calcular precio según membresía del usuario
            active_membership = current_user.get_active_membership()
            membership_type = active_membership.membership_type if active_membership else 'basic'
            pricing = event.pricing_for_membership(membership_type)
            
            unit_price = int(pricing['final_price'] * 100)  # Convertir a centavos
            product_name = event.title
            product_description = event.summary or event.description[:200] if event.description else ""
            metadata = {
                'event_id': event.id,
                'event_slug': event.slug,
                'base_price': pricing['base_price'],
                'final_price': pricing['final_price'],
                'discount_applied': pricing['discount'] is not None
            }
        
        elif product_type == 'service':
            # Obtener información del servicio
            product_id = int(data.get('product_id', 0))
            if product_id == 0:
                return jsonify({'success': False, 'error': 'ID de servicio no especificado'}), 400
            
            service = Service.query.get(product_id)
            if not service:
                return jsonify({'success': False, 'error': 'Servicio no encontrado'}), 404
            
            # Para servicios con diagnóstico: NO se requiere slot, va a cola
            # El slot se asignará después por el asesor
            
            # Calcular precio usando el método del servicio (respeta reglas y descuentos)
            active_membership = current_user.get_active_membership()
            membership_type = active_membership.membership_type if active_membership else 'basic'
            
            # Usar pricing_for_membership() que respeta ServicePricingRule y MembershipDiscount
            pricing = service.pricing_for_membership(membership_type)
            final_price = pricing['final_price']
            
            # Convertir a centavos para almacenar en CartItem
            unit_price = int(final_price * 100)
            
            product_name = service.name
            product_description = service.description or 'Servicio de RELATIC'
            metadata = {
                'service_id': service.id,
                'base_price': pricing['base_price'],
                'final_price': pricing['final_price'],
                'discount_percentage': pricing['discount_percentage'],
                'is_included': pricing['is_included'],
                'membership_type': membership_type,
                'discount_applied': pricing['discount_percentage'] > 0,
                'requires_diagnostic': service.requires_diagnostic_appointment
            }
        
        # Agregar al carrito
        cart = add_to_cart(
            current_user.id,
            product_type,
            product_id,
            product_name,
            unit_price,
            quantity,
            product_description,
            metadata
        )
        
        return jsonify({
            'success': True,
            'message': 'Producto agregado al carrito',
            'cart_items_count': cart.get_items_count(),
            'cart_total': cart.get_total()
        })
        
    except ValueError as e:
        # Error de conversión de tipos
        print(f"Error de validación agregando al carrito: {e}")
        return jsonify({'success': False, 'error': f'Error de validación: {str(e)}'}), 400
    except Exception as e:
        print(f"Error agregando al carrito: {e}")
        import traceback
        traceback.print_exc()
        # Asegurar que siempre devolvemos JSON
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def cart_remove(item_id):
    """Eliminar item del carrito"""
    try:
        cart = get_or_create_cart(current_user.id)
        item = CartItem.query.filter_by(id=item_id, cart_id=cart.id).first()
        
        if not item:
            return jsonify({'success': False, 'error': 'Item no encontrado'}), 404
        
        db.session.delete(item)
        cart.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Producto eliminado del carrito',
            'cart_items_count': cart.get_items_count(),
            'cart_total': cart.get_total()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def cart_update(item_id):
    """Actualizar cantidad de un item en el carrito"""
    try:
        data = request.get_json() if request.is_json else request.form
        quantity = int(data.get('quantity', 1))
        
        if quantity < 1:
            return jsonify({'success': False, 'error': 'La cantidad debe ser al menos 1'}), 400
        
        cart = get_or_create_cart(current_user.id)
        item = CartItem.query.filter_by(id=item_id, cart_id=cart.id).first()
        
        if not item:
            return jsonify({'success': False, 'error': 'Item no encontrado'}), 404
        
        item.quantity = quantity
        item.updated_at = datetime.utcnow()
        cart.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Cantidad actualizada',
            'cart_items_count': cart.get_items_count(),
            'cart_total': cart.get_total(),
            'item_subtotal': item.get_subtotal()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/cart/count', methods=['GET'])
@login_required
def cart_count():
    """Obtener cantidad de items en el carrito (API)"""
    cart = get_or_create_cart(current_user.id)
    return jsonify({
        'count': cart.get_items_count(),
        'total': cart.get_total()
    })

@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    """Webhook de Stripe para confirmar pagos"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv('STRIPE_WEBHOOK_SECRET', 'whsec_test')
        )
    except ValueError:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError:
        return 'Invalid signature', 400
    
    # Manejar el evento
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        handle_successful_payment(payment_intent)
    
    return jsonify({'status': 'success'})

def handle_successful_payment(payment_intent):
    """Manejar pago exitoso"""
    try:
        # Buscar el pago en la base de datos
        payment = Payment.query.filter_by(
            payment_reference=payment_intent['id']
        ).first()
        
        if payment:
            # Actualizar estado del pago
            payment.status = 'succeeded'
            payment.paid_at = datetime.utcnow()
            db.session.commit()
            
            # Registrar confirmación de pago vía webhook en historial
            try:
                from history_module import HistoryLogger
                # Registrar como acción del usuario (el pago es del usuario)
                HistoryLogger.log_user_action(
                    user_id=payment.user_id,
                    action=f"Pago confirmado - Stripe Webhook - ${payment.amount/100:.2f}",
                    status="success",
                    context={"app": "webhook", "screen": "payment", "module": "stripe"},
                    payload={
                        "payment_id": payment.id,
                        "payment_method": "stripe",
                        "amount": payment.amount,
                        "event_type": event.get('type') if 'event' in locals() else None
                    },
                    result={
                        "payment_id": payment.id,
                        "status": "succeeded",
                        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None
                    },
                    visibility="both"
                )
            except Exception as e:
                print(f"⚠️ Error registrando confirmación de pago Stripe en historial: {e}")
            
            # Crear suscripción
            end_date = datetime.utcnow() + timedelta(days=365)  # 1 año
            subscription = Subscription(
                user_id=payment.user_id,
                payment_id=payment.id,
                membership_type=payment.membership_type,
                status='active',
                end_date=end_date
            )
            db.session.add(subscription)
            db.session.commit()
            
            # Enviar notificación y email de confirmación
            NotificationEngine.notify_membership_payment(payment.user, payment, subscription)
            
            # Enviar webhook a Odoo (no bloquea si falla)
            try:
                cart = get_or_create_cart(payment.user_id)
                send_payment_to_odoo(payment, payment.user, cart)
            except Exception as e:
                print(f"⚠️ Error enviando pago a Odoo (no crítico): {e}")
            
    except Exception as e:
        print(f"Error handling payment: {e}")

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
                message=f'Tu cita con {advisor.first_name} {advisor.last_name} ha sido confirmada para el {appointment.appointment_date.strftime("%d/%m/%Y")} a las {appointment.appointment_time}.'
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
                        to_email=user.email,
                        subject='Cita Agendada - RelaticPanama',
                        html_content=html_content,
                        email_type='appointment_created',
                        related_entity_type='appointment',
                        related_entity_id=appointment.id,
                        recipient_id=user.id,
                        recipient_email=user.email,
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
                        to_email=advisor.email,
                        subject='Nueva Cita Pendiente de Confirmación - RelaticPanama',
                        html_content=html_content,
                        email_type='appointment_new_advisor',
                        related_entity_type='appointment',
                        related_entity_id=appointment.id,
                        recipient_id=advisor.id,
                        recipient_email=advisor.email,
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
                            to_email=admin.email,
                            subject='Nueva Cita Creada - RelaticPanama',
                            html_content=html_content,
                            email_type='appointment_new_admin',
                            related_entity_type='appointment',
                            related_entity_id=appointment.id,
                            recipient_id=admin.id,
                            recipient_email=admin.email,
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

@app.route('/api/user/membership')
@login_required
def api_user_membership():
    """API para obtener información de membresía del usuario"""
    membership = current_user.get_active_membership()
    if membership:
        return jsonify({
            'type': membership.membership_type,
            'start_date': membership.start_date.isoformat(),
            'end_date': membership.end_date.isoformat(),
            'is_active': membership.is_active,
            'payment_status': membership.payment_status
        })
    return jsonify({'error': 'No active membership found'}), 404

# Rutas de administración
@app.route('/admin')
@admin_required
def admin_dashboard():
    """Panel de administración principal"""
    try:
        # Contar pagos pendientes de revisión OCR (si el campo existe)
        try:
            pending_payments_count = Payment.query.filter(
                Payment.ocr_status.in_(['pending', 'needs_review']),
                Payment.status == 'pending'
            ).count()
        except AttributeError:
            # Si ocr_status no existe, contar solo pendientes
            pending_payments_count = Payment.query.filter_by(status='pending').count()
        
        total_users = User.query.count()
        
        # Usar Subscription en lugar de Membership si es necesario
        try:
            total_memberships = Membership.query.count()
            active_memberships = Membership.query.filter_by(is_active=True).count()
            recent_memberships = Membership.query.order_by(Membership.created_at.desc()).limit(5).all()
        except (AttributeError, Exception) as e:
            # Fallback a Subscription
            print(f"⚠️ Error con Membership, usando Subscription: {e}")
            total_memberships = Subscription.query.filter_by(status='active').count()
            active_memberships = Subscription.query.filter_by(status='active').count()
            recent_memberships = Subscription.query.order_by(Subscription.created_at.desc()).limit(5).all()
        
        total_payments = Payment.query.filter_by(status='succeeded').count()
        
        # Calcular revenue de forma segura
        try:
            succeeded_payments = Payment.query.filter_by(status='succeeded').all()
            total_revenue = sum([p.amount for p in succeeded_payments]) / 100.0
        except Exception as e:
            print(f"⚠️ Error calculando revenue: {e}")
            total_revenue = 0.0
        
        # Usuarios recientes
        recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
        
        return render_template('admin/dashboard.html',
                             total_users=total_users,
                             total_memberships=total_memberships,
                             active_memberships=active_memberships,
                             total_payments=total_payments,
                             total_revenue=total_revenue,
                             recent_users=recent_users,
                             recent_memberships=recent_memberships,
                             pending_payments_count=pending_payments_count)
    except Exception as e:
        print(f"❌ Error en admin_dashboard: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Error al cargar el panel de administración: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/admin/users')
@admin_required
def admin_users():
    """Gestión de usuarios con filtros"""
    # Obtener parámetros de filtro
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'all')
    admin_filter = request.args.get('admin', 'all')
    advisor_filter = request.args.get('advisor', 'all')
    group_filter = request.args.get('group', 'all')
    tag_filter = request.args.get('tag', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Construir query base
    query = User.query
    
    # Filtro de búsqueda (nombre, email, teléfono)
    if search:
        query = query.filter(
            db.or_(
                User.first_name.ilike(f'%{search}%'),
                User.last_name.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%'),
                User.phone.ilike(f'%{search}%')
            )
        )
    
    # Filtro de estado
    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'inactive':
        query = query.filter_by(is_active=False)
    
    # Filtro de admin
    if admin_filter == 'yes':
        query = query.filter_by(is_admin=True)
    elif admin_filter == 'no':
        query = query.filter_by(is_admin=False)
    
    # Filtro de asesor
    if advisor_filter == 'yes':
        query = query.filter_by(is_advisor=True)
    elif advisor_filter == 'no':
        query = query.filter_by(is_advisor=False)
    
    # Filtro de grupo
    if group_filter != 'all' and group_filter:
        query = query.filter_by(user_group=group_filter)
    
    # Filtro de etiqueta
    if tag_filter:
        query = query.filter(User.tags.ilike(f'%{tag_filter}%'))
    
    # Ordenar y paginar
    query = query.order_by(User.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items
    
    # Obtener grupos únicos para el filtro
    groups = db.session.query(User.user_group).distinct().filter(User.user_group.isnot(None)).all()
    groups = [g[0] for g in groups if g[0]]
    
    # Obtener etiquetas únicas para el filtro (extraer de todos los tags)
    all_tags = db.session.query(User.tags).filter(User.tags.isnot(None)).all()
    unique_tags = set()
    for tag_str in all_tags:
        if tag_str[0]:
            unique_tags.update([t.strip() for t in tag_str[0].split(',') if t.strip()])
    unique_tags = sorted(list(unique_tags))
    
    # Obtener membresías activas para cada usuario (para mostrar en la tabla)
    user_memberships = {}
    for user in users:
        active_membership = user.get_active_membership()
        if active_membership:
            # Determinar tipo de membresía y fecha de expiración
            if isinstance(active_membership, Subscription):
                user_memberships[user.id] = {
                    'type': active_membership.membership_type,
                    'end_date': active_membership.end_date,
                    'status': active_membership.status,
                    'is_subscription': True
                }
            else:
                user_memberships[user.id] = {
                    'type': active_membership.membership_type,
                    'end_date': active_membership.end_date,
                    'status': 'active' if active_membership.is_active else 'expired',
                    'is_subscription': False
                }
    
    return render_template('admin/users.html', 
                         users=users,
                         pagination=pagination,
                         search=search,
                         status_filter=status_filter,
                         admin_filter=admin_filter,
                         advisor_filter=advisor_filter,
                         group_filter=group_filter,
                         tag_filter=tag_filter,
                         groups=groups,
                         unique_tags=unique_tags,
                         valid_countries=VALID_COUNTRIES,
                         user_memberships=user_memberships)


@app.route('/admin/users/<int:user_id>/update', methods=['POST'])
@admin_required
def admin_update_user(user_id):
    """Actualizar atributos básicos del usuario (admin, asesor, estado)."""
    user = User.query.get_or_404(user_id)
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    phone = request.form.get('phone', '').strip()
    country = request.form.get('country', '').strip()
    cedula_or_passport = request.form.get('cedula_or_passport', '').strip()

    if first_name:
        user.first_name = first_name
    if last_name:
        user.last_name = last_name
    user.phone = phone or None
    
    # Actualizar país con validación
    if country:
        is_valid, error_message = validate_country(country)
        if not is_valid:
            flash(error_message, 'error')
            return redirect(url_for('admin_users'))
        user.country = country
    else:
        user.country = None
    
    # Actualizar cédula o pasaporte con validación
    if cedula_or_passport:
        is_valid, error_message = validate_cedula_or_passport(cedula_or_passport, country or user.country)
        if not is_valid:
            flash(error_message, 'error')
            return redirect(url_for('admin_users'))
        user.cedula_or_passport = cedula_or_passport
    else:
        user.cedula_or_passport = None
    
    # Actualizar tags y grupo
    user.tags = request.form.get('tags', '').strip() or None
    user.user_group = request.form.get('user_group', '').strip() or None
    
    # Actualizar email si cambió
    new_email = request.form.get('email', '').strip()
    if new_email and new_email != user.email:
        # Validar formato de email
        is_valid, error_message = validate_email_format(new_email)
        if not is_valid:
            flash(error_message, 'error')
            return redirect(url_for('admin_users'))
        # Verificar que el nuevo email no esté en uso
        if User.query.filter_by(email=new_email.lower()).first():
            flash('El email ya está en uso por otro usuario.', 'error')
            return redirect(url_for('admin_users'))
        user.email = new_email.lower()
    
    # Actualizar contraseña si se proporcionó
    new_password = request.form.get('password', '').strip()
    if new_password:
        if len(new_password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'error')
            return redirect(url_for('admin_users'))
        from werkzeug.security import generate_password_hash
        user.password_hash = generate_password_hash(new_password)

    user.is_active = bool(request.form.get('is_active'))
    user.is_admin = bool(request.form.get('is_admin'))
    wants_advisor = bool(request.form.get('is_advisor'))

    if wants_advisor and not user.is_advisor:
        user.is_advisor = True
        if not user.advisor_profile:
            new_profile = Advisor(
                user_id=user.id,
                headline=request.form.get('advisor_headline', '').strip() or 'Asesor RELATIC',
                specializations=request.form.get('advisor_specializations', '').strip(),
                meeting_url=request.form.get('advisor_meeting_url', '').strip(),
            )
            db.session.add(new_profile)
    elif not wants_advisor and user.is_advisor:
        user.is_advisor = False
        if user.advisor_profile:
            db.session.delete(user.advisor_profile)

    db.session.commit()
    flash('Usuario actualizado correctamente.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/create', methods=['POST'])
@admin_required
def admin_create_user():
    """Crear un nuevo usuario"""
    try:
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        phone = request.form.get('phone', '').strip()
        country = request.form.get('country', '').strip()
        cedula_or_passport = request.form.get('cedula_or_passport', '').strip()
        is_active = bool(request.form.get('is_active'))
        is_admin = bool(request.form.get('is_admin'))
        is_advisor = bool(request.form.get('is_advisor'))
        tags = request.form.get('tags', '').strip() or None
        user_group = request.form.get('user_group', '').strip() or None
        
        # Validaciones
        if not first_name or not last_name or not email or not password:
            flash('Todos los campos obligatorios deben ser completados.', 'error')
            return redirect(url_for('admin_users'))
        
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'error')
            return redirect(url_for('admin_users'))
        
        # Validar formato de email
        is_valid, error_message = validate_email_format(email)
        if not is_valid:
            flash(error_message, 'error')
            return redirect(url_for('admin_users'))
        
        # Validar país si se proporciona
        if country:
            is_valid, error_message = validate_country(country)
            if not is_valid:
                flash(error_message, 'error')
                return redirect(url_for('admin_users'))
        
        # Validar cédula o pasaporte si se proporciona
        if cedula_or_passport:
            is_valid, error_message = validate_cedula_or_passport(cedula_or_passport, country)
            if not is_valid:
                flash(error_message, 'error')
                return redirect(url_for('admin_users'))
        
        # Verificar si el email ya existe
        if User.query.filter_by(email=email.lower()).first():
            flash('El email ya está registrado.', 'error')
            return redirect(url_for('admin_users'))
        
        # Crear usuario
        from werkzeug.security import generate_password_hash
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email.lower(),
            password_hash=generate_password_hash(password),
            phone=phone or None,
            country=country if country else None,
            cedula_or_passport=cedula_or_passport if cedula_or_passport else None,
            tags=tags,
            user_group=user_group,
            is_active=is_active,
            is_admin=is_admin,
            is_advisor=is_advisor
        )
        db.session.add(new_user)
        db.session.commit()
        
        # Si es asesor, crear perfil
        if is_advisor:
            new_profile = Advisor(
                user_id=new_user.id,
                headline='Asesor RELATIC',
                specializations='',
                meeting_url=''
            )
            db.session.add(new_profile)
            db.session.commit()
        
        flash(f'Usuario {first_name} {last_name} creado correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al crear usuario: {str(e)}', 'error')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    """Eliminar un usuario"""
    user = User.query.get_or_404(user_id)
    
    # No permitir eliminar al usuario actual
    if user.id == current_user.id:
        flash('No puedes eliminar tu propio usuario.', 'error')
        return redirect(url_for('admin_users'))
    
    try:
        user_name = f"{user.first_name} {user.last_name}"
        
        # Eliminar perfil de asesor si existe
        if user.advisor_profile:
            db.session.delete(user.advisor_profile)
        
        # Eliminar usuario
        db.session.delete(user)
        db.session.commit()
        
        flash(f'Usuario {user_name} eliminado correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar usuario: {str(e)}', 'error')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/memberships')
@admin_required
def admin_memberships():
    """Gestión de membresías (incluye Membership y Subscription) con filtros y paginación"""
    # Obtener membresías antiguas (Membership)
    old_memberships = Membership.query.order_by(Membership.created_at.desc()).all()
    subscriptions = Subscription.query.order_by(Subscription.created_at.desc()).all()
    all_memberships = []
    for sub in subscriptions:
        all_memberships.append({
            'id': sub.id,
            'user': sub.user,
            'membership_type': sub.membership_type,
            'start_date': sub.start_date,
            'end_date': sub.end_date,
            'amount': sub.payment.amount / 100.0 if sub.payment else 0.0,
            'is_active': sub.is_currently_active(),
            'payment_status': 'paid' if sub.payment and sub.payment.status == 'succeeded' else 'pending',
            'payment_id': sub.payment_id,
            'is_subscription': True,
            'created_at': sub.created_at
        })
    for mem in old_memberships:
        all_memberships.append({
            'id': mem.id,
            'user': mem.user,
            'membership_type': mem.membership_type,
            'start_date': mem.start_date,
            'end_date': mem.end_date,
            'amount': mem.amount if hasattr(mem, 'amount') else 0.0,
            'is_active': mem.is_active if hasattr(mem, 'is_active') else False,
            'payment_status': mem.payment_status if hasattr(mem, 'payment_status') else 'unknown',
            'payment_id': None,
            'is_subscription': False,
            'created_at': mem.created_at if hasattr(mem, 'created_at') else datetime.utcnow()
        })
    all_memberships.sort(key=lambda x: x['created_at'], reverse=True)
    membership_types = sorted(set(m.get('membership_type') or '' for m in all_memberships if m.get('membership_type')))

    # Filtros
    search = request.args.get('search', '').strip().lower()
    type_filter = request.args.get('type', 'all')
    status_filter = request.args.get('status', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)

    if search:
        all_memberships = [m for m in all_memberships if m['user'] and (
            (m['user'].first_name or '').lower().find(search) >= 0 or
            (m['user'].last_name or '').lower().find(search) >= 0 or
            (m['user'].email or '').lower().find(search) >= 0
        )]
    if type_filter != 'all':
        all_memberships = [m for m in all_memberships if (m.get('membership_type') or '').lower() == type_filter.lower()]
    if status_filter == 'active':
        all_memberships = [m for m in all_memberships if m.get('is_active')]
    elif status_filter == 'inactive':
        all_memberships = [m for m in all_memberships if not m.get('is_active')]

    total = len(all_memberships)
    pages = max(1, (total + per_page - 1) // per_page) if per_page else 1
    page = min(max(1, page), pages)
    start = (page - 1) * per_page
    memberships = all_memberships[start:start + per_page]

    def _iter_pages(left_edge=1, right_edge=1, left_current=2, right_current=2):
        for p in range(1, pages + 1):
            yield p
    pagination = type('Pagination', (), {'page': page, 'per_page': per_page, 'total': total, 'pages': pages, 'has_prev': page > 1, 'has_next': page < pages, 'prev_num': page - 1, 'next_num': page + 1, 'iter_pages': lambda le=1, re=1, lc=2, rc=2: _iter_pages(le, re, lc, rc)})()

    return render_template('admin/memberships.html',
                         memberships=memberships,
                         subscriptions=subscriptions,
                         old_memberships=old_memberships,
                         pagination=pagination,
                         search=search,
                         type_filter=type_filter,
                         status_filter=status_filter,
                         membership_types=membership_types)

# Rutas administrativas para gestión de mensajería
@app.route('/admin/messaging')
@admin_required
def admin_messaging():
    """Lista de todos los emails enviados"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    email_type = request.args.get('type', 'all')
    status = request.args.get('status', 'all')
    search = request.args.get('search', '')
    
    # Construir query
    query = EmailLog.query
    
    # Filtros
    if email_type != 'all':
        query = query.filter_by(email_type=email_type)
    
    if status != 'all':
        query = query.filter_by(status=status)
    
    if search:
        query = query.filter(
            db.or_(
                EmailLog.recipient_email.ilike(f'%{search}%'),
                EmailLog.subject.ilike(f'%{search}%'),
                EmailLog.recipient_name.ilike(f'%{search}%')
            )
        )
    
    # Ordenar por fecha más reciente
    query = query.order_by(EmailLog.created_at.desc())
    
    # Paginación
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    emails = pagination.items
    
    # Estadísticas
    total_emails = EmailLog.query.count()
    sent_emails = EmailLog.query.filter_by(status='sent').count()
    failed_emails = EmailLog.query.filter_by(status='failed').count()
    
    # Tipos de email únicos para el filtro
    email_types = db.session.query(EmailLog.email_type).distinct().all()
    email_types = [t[0] for t in email_types if t[0]]
    
    # Obtener notificaciones sin email enviado (para diagnóstico)
    notifications_without_email = Notification.query.filter_by(email_sent=False).order_by(Notification.created_at.desc()).limit(10).all()
    
    return render_template('admin/messaging.html',
                         emails=emails,
                         pagination=pagination,
                         total_emails=total_emails,
                         sent_emails=sent_emails,
                         failed_emails=failed_emails,
                         email_types=email_types,
                         current_type=email_type,
                         current_status=status,
                         search=search,
                         notifications_without_email=notifications_without_email)

@app.route('/admin/messaging/<int:email_id>')
@admin_required
def admin_messaging_detail(email_id):
    """Detalle de un email específico"""
    email_log = EmailLog.query.get_or_404(email_id)
    return render_template('admin/messaging_detail.html', email_log=email_log)

@app.route('/admin/messaging/<int:email_id>/resend', methods=['POST'])
@admin_required
def admin_messaging_resend(email_id):
    """Reenviar un email que falló"""
    email_log = EmailLog.query.get_or_404(email_id)
    
    if email_log.status == 'sent':
        flash('Este email ya fue enviado exitosamente.', 'info')
        return redirect(url_for('admin_messaging_detail', email_id=email_id))
    
    try:
        # Intentar reenviar
        if email_service:
            success = email_service.send_email(
                subject=email_log.subject,
                recipients=[email_log.recipient_email],
                html_content=email_log.html_content or '',
                text_content=email_log.text_content,
                email_type=email_log.email_type,
                related_entity_type=email_log.related_entity_type,
                related_entity_id=email_log.related_entity_id,
                recipient_id=email_log.recipient_id,
                recipient_name=email_log.recipient_name
            )
            
            if success:
                email_log.status = 'sent'
                email_log.sent_at = datetime.utcnow()
                email_log.error_message = None
                db.session.commit()
                flash('Email reenviado exitosamente.', 'success')
            else:
                email_log.status = 'failed'
                email_log.retry_count += 1
                db.session.commit()
                flash('Error al reenviar el email. Verifica la configuración del servidor de correo.', 'error')
        else:
            flash('Servicio de email no disponible.', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al reenviar: {str(e)}', 'error')
    
    return redirect(url_for('admin_messaging_detail', email_id=email_id))

@app.route('/admin/messaging/<int:email_id>/delete', methods=['POST'])
@admin_required
def admin_messaging_delete(email_id):
    """Eliminar un registro de email"""
    email_log = EmailLog.query.get_or_404(email_id)
    
    try:
        db.session.delete(email_log)
        db.session.commit()
        flash('Registro de email eliminado.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar: {str(e)}', 'error')
    
    return redirect(url_for('admin_messaging'))

@app.route('/api/admin/messaging/stats')
@admin_required
def api_messaging_stats():
    """API para obtener estadísticas de mensajería"""
    total = EmailLog.query.count()
    sent = EmailLog.query.filter_by(status='sent').count()
    failed = EmailLog.query.filter_by(status='failed').count()
    
    # Estadísticas por tipo
    from sqlalchemy import func
    stats_by_type = db.session.query(
        EmailLog.email_type,
        func.count(EmailLog.id).label('count')
    ).group_by(EmailLog.email_type).all()
    
    # Estadísticas por día (últimos 30 días)
    from datetime import timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    stats_by_day = db.session.query(
        func.date(EmailLog.created_at).label('date'),
        func.count(EmailLog.id).label('count')
    ).filter(
        EmailLog.created_at >= thirty_days_ago
    ).group_by(func.date(EmailLog.created_at)).all()
    
    return jsonify({
        'total': total,
        'sent': sent,
        'failed': failed,
        'by_type': {t[0]: t[1] for t in stats_by_type},
        'by_day': [{'date': str(d[0]), 'count': d[1]} for d in stats_by_day]
    })

# Rutas de administración para configuración de notificaciones
@app.route('/admin/notifications')
@admin_required
def admin_notifications():
    """Panel de configuración de notificaciones"""
    settings = NotificationSettings.get_all_settings()
    return render_template('admin/notifications.html', settings=settings)

@app.route('/api/admin/notifications')
@admin_required
def api_notifications_list():
    """API para obtener todas las configuraciones de notificaciones"""
    settings = NotificationSettings.query.order_by(NotificationSettings.category, NotificationSettings.name).all()
    return jsonify({
        'settings': [s.to_dict() for s in settings]
    })

@app.route('/api/admin/notifications/<int:setting_id>', methods=['PUT'])
@admin_required
def api_notification_update(setting_id):
    """API para actualizar una configuración de notificación"""
    setting = NotificationSettings.query.get_or_404(setting_id)
    
    data = request.get_json()
    if 'enabled' in data:
        setting.enabled = bool(data['enabled'])
        setting.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Notificación "{setting.name}" {"habilitada" if setting.enabled else "deshabilitada"}',
            'setting': setting.to_dict()
        })
    
    return jsonify({'success': False, 'error': 'Datos inválidos'}), 400

@app.route('/api/admin/notifications/bulk-update', methods=['POST'])
@admin_required
def api_notifications_bulk_update():
    """API para actualizar múltiples configuraciones a la vez"""
    data = request.get_json()
    updates = data.get('updates', [])
    
    updated_count = 0
    for update in updates:
        setting_id = update.get('id')
        enabled = update.get('enabled')
        
        if setting_id and enabled is not None:
            setting = NotificationSettings.query.get(setting_id)
            if setting:
                setting.enabled = bool(enabled)
                setting.updated_at = datetime.utcnow()
                updated_count += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'{updated_count} configuración(es) actualizada(s)',
        'updated': updated_count
    })

# Rutas de administración para configuración de email
@app.route('/admin/email')
@admin_required
def admin_email():
    """Panel de configuración de email (SMTP y templates)"""
    email_config = EmailConfig.get_active_config()
    templates = EmailTemplate.query.order_by(EmailTemplate.category, EmailTemplate.name).all()
    
    # Agrupar templates por categoría
    templates_by_category = {}
    for template in templates:
        if template.category not in templates_by_category:
            templates_by_category[template.category] = []
        templates_by_category[template.category].append(template.to_dict())
    
    return render_template('admin/email.html', 
                         email_config=email_config.to_dict() if email_config else None,
                         templates=templates_by_category)

@app.route('/api/admin/email/config', methods=['GET', 'POST', 'PUT'])
@admin_required
def api_email_config():
    """API para obtener y actualizar configuración SMTP"""
    if request.method == 'GET':
        config = EmailConfig.get_active_config()
        if config:
            return jsonify({'success': True, 'config': config.to_dict()})
        else:
            return jsonify({'success': False, 'message': 'No hay configuración activa'})
    
    elif request.method in ['POST', 'PUT']:
        data = request.get_json()
        
        # Desactivar todas las configuraciones anteriores
        EmailConfig.query.update({'is_active': False})
        
        # Buscar si existe una configuración
        config = EmailConfig.query.first()
        
        if not config:
            # Crear nueva configuración
            config = EmailConfig(
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
            db.session.add(config)
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
            db.session.commit()
            
            # Aplicar nueva configuración
            config.apply_to_app(app)
            global mail
            mail = Mail(app)
            if EMAIL_TEMPLATES_AVAILABLE:
                global email_service
                email_service = EmailService(mail)
            
            return jsonify({
                'success': True,
                'message': 'Configuración de email actualizada exitosamente',
                'config': config.to_dict()
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

@app.route('/api/admin/email/test', methods=['POST'])
@admin_required
def api_email_test():
    """API para probar la configuración de email enviando un correo de prueba"""
    data = request.get_json()
    test_email = data.get('email', current_user.email)
    
    # Validar email de destino
    if not test_email or '@' not in test_email:
        return jsonify({
            'success': False,
            'error': 'Email de destino inválido'
        }), 400
    
    # Verificar configuración antes de enviar
    email_config = EmailConfig.get_active_config()
    if not email_config:
        return jsonify({
            'success': False,
            'error': 'No hay configuración de email activa. Configura el servidor SMTP primero.',
            'details': 'Ve a /admin/email y configura el servidor SMTP'
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
        validation_errors.append('Usuario SMTP no parece ser un email válido')
    
    if not email_config.mail_password:
        validation_errors.append('Contraseña SMTP no configurada')
    elif len(email_config.mail_password) < 8:
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
    
    # Aplicar configuración antes de enviar
    try:
        email_config.apply_to_app(app)
        # Reinicializar mail con nueva configuración
        global mail
        mail = Mail(app)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error al aplicar configuración: {str(e)}'
        }), 500
    
    # Intentar enviar el correo
    try:
        # Crear mensaje de prueba
        from flask_mail import Message
        msg = Message(
            subject='[Prueba] Configuración de Email - RelaticPanama',
            recipients=[test_email],
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
        mail.send(msg)
        
        return jsonify({
            'success': True,
            'message': f'Correo de prueba enviado exitosamente a {test_email}',
            'config_used': {
                'server': email_config.mail_server,
                'sender': email_config.mail_default_sender
            }
        })
    except Exception as e:
        error_msg = str(e)
        error_details = []
        
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

@app.route('/api/admin/email/test-welcome', methods=['POST'])
@admin_required
def api_email_test_welcome():
    """API para probar el template de bienvenida"""
    data = request.get_json()
    test_email = data.get('email', current_user.email)
    
    try:
        # Crear usuario de prueba
        class MockUser:
            def __init__(self, email):
                self.id = 1
                self.first_name = "Juan"
                self.last_name = "Pérez"
                self.email = email
        
        user = MockUser(test_email)
        
        # Generar HTML del template de bienvenida
        html_content = get_welcome_email(user)
        
        # Enviar email de prueba
        from flask_mail import Message
        msg = Message(
            subject='[Prueba] Email de Bienvenida - RelaticPanama',
            recipients=[test_email],
            html=html_content
        )
        mail.send(msg)
        
        return jsonify({
            'success': True,
            'message': f'Email de bienvenida de prueba enviado exitosamente a {test_email}'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error al enviar email de prueba: {str(e)}'
        }), 500

@app.route('/api/admin/email/preview/<template_key>', methods=['GET'])
@admin_required
def api_email_preview_template(template_key):
    """API para previsualizar cualquier template de email sin enviarlo"""
    try:
        # Crear datos de prueba según el tipo de template
        class MockUser:
            def __init__(self):
                self.id = 1
                self.first_name = "Juan"
                self.last_name = "Pérez"
                self.email = "juan.perez@example.com"
        
        class MockPayment:
            def __init__(self):
                self.membership_type = "pro"
                self.amount = 60.00
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
            def __init__(self):
                self.appointment_type = type('obj', (object,), {'name': 'Asesoría en Revisión de Artículos'})()
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
        
        user = MockUser()
        
        # Generar HTML según el template_key
        if template_key == 'welcome':
            html_content = get_welcome_email(user)
        elif template_key == 'membership_payment':
            payment = MockPayment()
            subscription = MockSubscription()
            html_content = get_membership_payment_confirmation_email(user, payment, subscription)
        elif template_key == 'membership_expiring':
            subscription = MockSubscription()
            html_content = get_membership_expiring_email(user, subscription, days_left=7)
        elif template_key == 'membership_expired':
            subscription = MockSubscription()
            html_content = get_membership_expired_email(user, subscription)
        elif template_key == 'membership_renewed':
            subscription = MockSubscription()
            html_content = get_membership_renewed_email(user, subscription)
        elif template_key == 'event_registration':
            event = MockEvent()
            registration = MockRegistration()
            try:
                # Intentar usar el template HTML nuevo primero
                from flask import render_template
                from app import get_public_image_url
                import os
                
                logo_path_png = os.path.join(os.path.dirname(__file__), '..', 'static', 'public', 'emails', 'logos', 'logo-relatic.png')
                logo_path_svg = os.path.join(os.path.dirname(__file__), '..', 'static', 'images', 'logo-relatic.svg')
                base_url = request.url_root.rstrip('/') if request else 'https://miembros.relatic.org'
                
                if os.path.exists(logo_path_png):
                    logo_url = get_public_image_url('emails/logos/logo-relatic.png', absolute=True)
                elif os.path.exists(logo_path_svg):
                    logo_url = f"{base_url}/static/images/logo-relatic.svg"
                else:
                    logo_url = None
                
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
                html_content = get_event_registration_email(event, user, registration)
        elif template_key == 'event_cancellation':
            event = MockEvent()
            html_content = get_event_cancellation_email(event, user)
        elif template_key == 'event_update':
            event = MockEvent()
            html_content = get_event_update_email(event, user, changes=["Fecha actualizada", "Nueva ubicación"])
        elif template_key == 'appointment_confirmation':
            appointment = MockAppointment()
            advisor = MockAdvisor()
            try:
                # Usar el template HTML nuevo
                from flask import render_template
                from app import get_public_image_url
                import os
                
                logo_path_png = os.path.join(os.path.dirname(__file__), '..', 'static', 'public', 'emails', 'logos', 'logo-relatic.png')
                logo_path_svg = os.path.join(os.path.dirname(__file__), '..', 'static', 'images', 'logo-relatic.svg')
                base_url = request.url_root.rstrip('/') if request else 'https://miembros.relatic.org'
                
                if os.path.exists(logo_path_png):
                    logo_url = get_public_image_url('emails/logos/logo-relatic.png', absolute=True)
                elif os.path.exists(logo_path_svg):
                    logo_url = f"{base_url}/static/images/logo-relatic.svg"
                else:
                    logo_url = None
                
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
                html_content = get_appointment_confirmation_email(appointment, user, advisor)
        elif template_key == 'appointment_reminder':
            appointment = MockAppointment()
            advisor = MockAdvisor()
            try:
                # Usar el template HTML nuevo
                from flask import render_template
                from app import get_public_image_url
                import os
                
                logo_path_png = os.path.join(os.path.dirname(__file__), '..', 'static', 'public', 'emails', 'logos', 'logo-relatic.png')
                logo_path_svg = os.path.join(os.path.dirname(__file__), '..', 'static', 'images', 'logo-relatic.svg')
                base_url = request.url_root.rstrip('/') if request else 'https://miembros.relatic.org'
                
                if os.path.exists(logo_path_png):
                    logo_url = get_public_image_url('emails/logos/logo-relatic.png', absolute=True)
                elif os.path.exists(logo_path_svg):
                    logo_url = f"{base_url}/static/images/logo-relatic.svg"
                else:
                    logo_url = None
                
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
                html_content = get_appointment_reminder_email(appointment, user, advisor, hours_before=24)
        elif template_key == 'password_reset':
            reset_token = "abc123xyz"
            reset_url = f"{request.url_root.rstrip('/')}/reset-password?token={reset_token}"
            html_content = get_password_reset_email(user, reset_token, reset_url)
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
@app.route('/api/admin/email/preview-welcome', methods=['GET'])
@admin_required
def api_email_preview_welcome():
    """API para previsualizar el template de bienvenida sin enviarlo (compatibilidad)"""
    return api_email_preview_template('welcome')

@app.route('/api/admin/email/upload-logo', methods=['POST'])
@admin_required
def api_upload_logo():
    """API para subir el logo para emails"""
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
        
        if not allowed_file(file.filename):
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
        logo_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'public', 'emails', 'logos')
        os.makedirs(logo_dir, exist_ok=True)
        
        # Guardar como logo-relatic.png (convertir SVG a PNG si es necesario)
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        # Si es SVG, mantener como SVG, pero recomendamos PNG
        if ext == 'svg':
            logo_path = os.path.join(logo_dir, 'logo-relatic.svg')
            file.save(logo_path)
            logo_url = get_public_image_url('emails/logos/logo-relatic.svg', absolute=True)
            # También copiar a ubicación antigua para compatibilidad
            old_logo_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'images', 'logo-relatic.svg')
            try:
                import shutil
                os.makedirs(os.path.dirname(old_logo_path), exist_ok=True)
                shutil.copy2(logo_path, old_logo_path)
            except Exception as e:
                print(f"⚠️ No se pudo copiar logo a ubicación antigua: {e}")
        else:
            # Para PNG, JPG, etc., guardar como PNG
            logo_path = os.path.join(logo_dir, 'logo-relatic.png')
            file.save(logo_path)
            logo_url = get_public_image_url('emails/logos/logo-relatic.png', absolute=True)
            # También copiar a ubicación antigua para compatibilidad
            old_logo_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'images')
            os.makedirs(old_logo_dir, exist_ok=True)
            try:
                import shutil
                # Copiar PNG también a images/ para compatibilidad
                old_logo_path_png = os.path.join(old_logo_dir, 'logo-relatic.png')
                shutil.copy2(logo_path, old_logo_path_png)
            except Exception as e:
                print(f"⚠️ No se pudo copiar logo a ubicación antigua: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Logo subido exitosamente y disponible en todo el sistema',
            'logo_url': logo_url
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error al subir logo: {str(e)}'
        }), 500

@app.route('/api/admin/email/delete-logo', methods=['POST'])
@admin_required
def api_delete_logo():
    """API para eliminar el logo"""
    try:
        logo_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'public', 'emails', 'logos')
        logo_path_png = os.path.join(logo_dir, 'logo-relatic.png')
        logo_path_svg = os.path.join(logo_dir, 'logo-relatic.svg')
        
        deleted = False
        if os.path.exists(logo_path_png):
            os.remove(logo_path_png)
            deleted = True
        if os.path.exists(logo_path_svg):
            os.remove(logo_path_svg)
            deleted = True
        
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

@app.route('/api/admin/email/logo-status', methods=['GET'])
@admin_required
def api_logo_status():
    """API para verificar si existe el logo"""
    try:
        logo_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'public', 'emails', 'logos')
        logo_path_png = os.path.join(logo_dir, 'logo-relatic.png')
        logo_path_svg = os.path.join(logo_dir, 'logo-relatic.svg')
        
        logo_exists = os.path.exists(logo_path_png) or os.path.exists(logo_path_svg)
        
        logo_url = None
        if logo_exists:
            if os.path.exists(logo_path_png):
                logo_url = get_public_image_url('emails/logos/logo-relatic.png', absolute=True)
            elif os.path.exists(logo_path_svg):
                logo_url = get_public_image_url('emails/logos/logo-relatic.svg', absolute=True)
        
        return jsonify({
            'success': True,
            'logo_exists': logo_exists,
            'logo_url': logo_url
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error al verificar logo: {str(e)}'
        }), 500

@app.route('/api/admin/email/templates')
@admin_required
def api_email_templates():
    """API para obtener todos los templates de correo"""
    templates = EmailTemplate.query.order_by(EmailTemplate.category, EmailTemplate.name).all()
    return jsonify({
        'success': True,
        'templates': [t.to_dict() for t in templates]
    })

@app.route('/api/admin/email/templates/<int:template_id>', methods=['GET', 'PUT'])
@admin_required
def api_email_template(template_id):
    """API para obtener y actualizar un template de correo"""
    template = EmailTemplate.query.get_or_404(template_id)
    
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
            db.session.commit()
            return jsonify({
                'success': True,
                'message': f'Template "{template.name}" actualizado exitosamente',
                'template': template.to_dict()
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

# Rutas de administración para configuración de multimedia
@app.route('/admin/media')
@admin_required
def admin_media():
    """Panel de configuración de videos y audios para guías visuales"""
    # Obtener todas las configuraciones agrupadas por procedimiento
    all_configs = MediaConfig.get_all_configs()
    
    # Agrupar por procedimiento
    procedures = {}
    for config in all_configs:
        if config.procedure_key not in procedures:
            procedures[config.procedure_key] = []
        procedures[config.procedure_key].append(config.to_dict())
    
    # Definir procedimientos disponibles
    available_procedures = {
        'register': 'Registro de Usuario',
        'membership': 'Compra de Membresía',
        'payment': 'Proceso de Pago',
        'events': 'Registro a Eventos',
        'appointments': 'Reserva de Citas',
        'admin-payments': 'Configuración de Métodos de Pago'
    }
    
    return render_template('admin/media.html',
                         procedures=procedures,
                         available_procedures=available_procedures)

@app.route('/api/admin/media/config', methods=['GET', 'POST', 'PUT', 'DELETE'])
@admin_required
def api_media_config():
    """API para gestionar configuración de multimedia"""
    if request.method == 'GET':
        # Obtener todas las configuraciones
        configs = MediaConfig.get_all_configs()
        return jsonify({
            'success': True,
            'configs': [c.to_dict() for c in configs]
        })
    
    elif request.method == 'POST':
        # Crear nueva configuración
        data = request.get_json()
        
        # Verificar si ya existe
        existing = MediaConfig.query.filter_by(
            procedure_key=data.get('procedure_key'),
            step_number=data.get('step_number')
        ).first()
        
        if existing:
            return jsonify({
                'success': False,
                'error': 'Ya existe una configuración para este procedimiento y paso'
            }), 400
        
        config = MediaConfig(
            procedure_key=data.get('procedure_key'),
            step_number=data.get('step_number'),
            video_url=data.get('video_url', ''),
            audio_url=data.get('audio_url', ''),
            step_title=data.get('step_title', ''),
            description=data.get('description', ''),
            is_active=True
        )
        
        try:
            db.session.add(config)
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Configuración creada exitosamente',
                'config': config.to_dict()
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    elif request.method == 'PUT':
        # Actualizar configuración existente
        data = request.get_json()
        config_id = data.get('id')
        
        if not config_id:
            return jsonify({
                'success': False,
                'error': 'ID de configuración requerido'
            }), 400
        
        config = MediaConfig.query.get(config_id)
        if not config:
            return jsonify({
                'success': False,
                'error': 'Configuración no encontrada'
            }), 404
        
        # Actualizar campos
        if 'video_url' in data:
            config.video_url = data.get('video_url', '')
        if 'audio_url' in data:
            config.audio_url = data.get('audio_url', '')
        if 'step_title' in data:
            config.step_title = data.get('step_title', '')
        if 'description' in data:
            config.description = data.get('description', '')
        if 'is_active' in data:
            config.is_active = bool(data.get('is_active', True))
        
        config.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Configuración actualizada exitosamente',
                'config': config.to_dict()
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    elif request.method == 'DELETE':
        # Eliminar configuración
        config_id = request.args.get('id')
        
        if not config_id:
            return jsonify({
                'success': False,
                'error': 'ID de configuración requerido'
            }), 400
        
        config = MediaConfig.query.get(config_id)
        if not config:
            return jsonify({
                'success': False,
                'error': 'Configuración no encontrada'
            }), 404
        
        try:
            db.session.delete(config)
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Configuración eliminada exitosamente'
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

@app.route('/api/media/config/<procedure_key>')
def get_media_config(procedure_key):
    """API pública para obtener configuraciones de multimedia (para el frontend)"""
    configs = MediaConfig.get_procedure_configs(procedure_key)
    return jsonify({
        'success': True,
        'procedure_key': procedure_key,
        'configs': [c.to_dict() for c in configs]
    })

# Rutas de administración para configuración de pagos
@app.route('/admin/payments/review/<int:payment_id>')
@admin_required
def admin_payment_review(payment_id):
    """Revisar y aprobar/rechazar pago con OCR"""
    payment = Payment.query.get_or_404(payment_id)
    user = User.query.get(payment.user_id)
    
    # Parsear datos OCR
    ocr_data = None
    if payment.ocr_data:
        try:
            import json
            ocr_data = json.loads(payment.ocr_data)
        except:
            pass
    
    return render_template('admin/payment_review.html',
                         payment=payment,
                         user=user,
                         ocr_data=ocr_data)

@app.route('/api/admin/payments/<int:payment_id>/approve', methods=['POST'])
@admin_required
def api_approve_payment(payment_id):
    """Aprobar pago y otorgar membresía"""
    try:
        payment = Payment.query.get_or_404(payment_id)
        
        if payment.status == 'succeeded':
            return jsonify({'success': False, 'error': 'El pago ya está aprobado'}), 400
        
        # Aprobar pago
        payment.status = 'succeeded'
        payment.ocr_status = 'verified'
        payment.ocr_verified_at = datetime.utcnow()
        payment.paid_at = datetime.utcnow()
        
        admin_notes = request.json.get('notes', '')
        if admin_notes:
            payment.admin_notes = admin_notes
        
        db.session.commit()
        
        # Procesar carrito si existe
        cart = get_or_create_cart(payment.user_id)
        if cart.get_items_count() > 0:
            process_cart_after_payment(cart, payment)
            cart.clear()
            db.session.commit()
        
        # Enviar notificación al usuario
        user = User.query.get(payment.user_id)
        if user:
            try:
                subscription = Subscription.query.filter_by(payment_id=payment.id).first()
                if subscription:
                    NotificationEngine.notify_membership_payment(user, payment, subscription)
            except:
                pass
            
            # Enviar webhook a Odoo (no bloquea si falla)
            try:
                send_payment_to_odoo(payment, user, cart)
            except Exception as e:
                print(f"⚠️ Error enviando pago a Odoo (no crítico): {e}")
        
        return jsonify({'success': True, 'message': 'Pago aprobado exitosamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/payments/<int:payment_id>/reject', methods=['POST'])
@admin_required
def api_reject_payment(payment_id):
    """Rechazar pago"""
    try:
        payment = Payment.query.get_or_404(payment_id)
        
        payment.status = 'failed'
        payment.ocr_status = 'rejected'
        payment.ocr_verified_at = datetime.utcnow()
        
        admin_notes = request.json.get('notes', '')
        if admin_notes:
            payment.admin_notes = admin_notes
        
        db.session.commit()
        
        # Enviar notificación al usuario
        user = User.query.get(payment.user_id)
        if user and EMAIL_TEMPLATES_AVAILABLE and email_service:
            try:
                html_content = f"""
                <h2>Pago Rechazado</h2>
                <p>Hola {user.first_name},</p>
                <p>Lamentamos informarte que tu pago #{payment.id} ha sido rechazado.</p>
                <p><strong>Razón:</strong> {admin_notes or 'No se pudo verificar el comprobante de pago'}</p>
                <p>Por favor, verifica los datos de tu comprobante y vuelve a intentar.</p>
                <p>Saludos,<br>Equipo RelaticPanama</p>
                """
                email_service.send_email(
                    subject='Pago Rechazado - RelaticPanama',
                    recipients=[user.email],
                    html_content=html_content,
                    email_type='payment_rejected',
                    related_entity_type='payment',
                    related_entity_id=payment.id,
                    recipient_id=user.id,
                    recipient_name=f"{user.first_name} {user.last_name}"
                )
            except:
                pass
        
        return jsonify({'success': True, 'message': 'Pago rechazado'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/payments')
@admin_required
def admin_payments():
    """Panel de configuración de métodos de pago y revisión de pagos pendientes"""
    try:
        # Obtener configuración directamente con query explícito
        payment_config = db.session.query(PaymentConfig).filter_by(is_active=True).first()
        
        # Verificar que sea realmente un PaymentConfig y tenga el método to_dict
        if payment_config:
            if not isinstance(payment_config, PaymentConfig):
                print(f"⚠️ Error: Se obtuvo un objeto de tipo {type(payment_config).__name__} en lugar de PaymentConfig")
                config_dict = None
            elif not hasattr(payment_config, 'to_dict'):
                print(f"⚠️ Error: PaymentConfig no tiene método to_dict")
                config_dict = None
            else:
                config_dict = payment_config.to_dict()
        else:
            config_dict = None
    except Exception as e:
        print(f"❌ Error obteniendo PaymentConfig: {e}")
        import traceback
        traceback.print_exc()
        config_dict = None
    
    # Obtener pagos pendientes de revisión
    pending_payments = Payment.query.filter(
        Payment.ocr_status.in_(['pending', 'needs_review']),
        Payment.status == 'pending'
    ).order_by(Payment.created_at.desc()).limit(20).all()
    
    # Obtener transacciones del historial relacionadas con pagos
    # Filtrar por transacciones de tipo 'payment' o 'purchase'
    payment_transactions = HistoryTransaction.query.filter(
        HistoryTransaction.transaction_type.in_(['payment', 'purchase'])
    ).order_by(HistoryTransaction.timestamp.desc()).limit(100).all()
    
    # Enriquecer transacciones con información del usuario y pago
    enriched_transactions = []
    for trans in payment_transactions:
        trans_dict = trans.to_dict(include_sensitive=True)
        
        # Agregar información del usuario
        if trans.actor_id:
            actor = User.query.get(trans.actor_id)
            if actor:
                trans_dict['actor'] = {
                    'id': actor.id,
                    'email': actor.email,
                    'first_name': actor.first_name,
                    'last_name': actor.last_name
                }
        
        # Intentar extraer payment_id del payload o result
        payment_id = None
        try:
            import json
            if trans.payload:
                payload_data = json.loads(trans.payload)
                payment_id = payload_data.get('payment_id') or payload_data.get('payment', {}).get('id')
            if not payment_id and trans.result:
                result_data = json.loads(trans.result)
                payment_id = result_data.get('payment_id') or result_data.get('payment', {}).get('id')
        except:
            pass
        
        # Agregar información del pago si existe
        if payment_id:
            payment = Payment.query.get(payment_id)
            if payment:
                trans_dict['payment'] = {
                    'id': payment.id,
                    'amount': float(payment.amount) / 100 if payment.amount else 0,  # Convertir de centavos a dólares
                    'currency': payment.currency.upper() if payment.currency else 'USD',
                    'status': payment.status,
                    'method': payment.payment_method
                }
        
        enriched_transactions.append(trans_dict)
    
    # Debug: Log para verificar que se están pasando las transacciones
    print(f"📊 admin_payments(): Pasando {len(enriched_transactions)} transacciones al template")
    if enriched_transactions:
        print(f"   - Primera transacción: ID {enriched_transactions[0].get('id')}, Tipo: {enriched_transactions[0].get('transaction_type')}")
    
    return render_template('admin/payments.html',
                         payment_config=config_dict,
                         pending_payments=pending_payments,
                         payment_transactions=enriched_transactions)

@app.route('/admin/backup')
@admin_required
def admin_backup():
    """Panel de respaldo de base de datos"""
    # Obtener lista de backups existentes
    backups_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')
    backups = []
    
    if os.path.exists(backups_dir):
        for filename in sorted(os.listdir(backups_dir), reverse=True):
            if filename.startswith('relaticpanama_backup_') and filename.endswith('.db'):
                filepath = os.path.join(backups_dir, filename)
                file_stat = os.stat(filepath)
                backups.append({
                    'filename': filename,
                    'size': file_stat.st_size,
                    'size_mb': round(file_stat.st_size / (1024 * 1024), 2),
                    'created_at': datetime.fromtimestamp(file_stat.st_mtime),
                    'path': filepath
                })
    
    return render_template('admin/backup.html', backups=backups)

@app.route('/admin/backup/create', methods=['POST'])
@admin_required
def create_backup():
    """Crear respaldo de base de datos y devolverlo para descarga"""
    try:
        # Crear respaldo
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(project_root, 'instance', 'relaticpanama.db')
        backups_dir = os.path.join(project_root, 'backups')
        
        os.makedirs(backups_dir, exist_ok=True)
        
        if not os.path.exists(db_path):
            return jsonify({'success': False, 'error': 'Base de datos no encontrada'}), 404
        
        # Generar nombre de respaldo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'relaticpanama_backup_{timestamp}.db'
        backup_path = os.path.join(backups_dir, backup_filename)
        
        # Copiar base de datos
        import shutil
        shutil.copy2(db_path, backup_path)
        
        # Registrar en logs
        print(f"✅ Respaldo creado por admin: {backup_filename}")
        
        # Devolver archivo para descarga
        return send_file(
            backup_path,
            as_attachment=True,
            download_name=backup_filename,
            mimetype='application/x-sqlite3'
        )
        
    except Exception as e:
        print(f"❌ Error al crear respaldo: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/backup/download/<filename>')
@admin_required
def download_backup(filename):
    """Descargar un respaldo existente"""
    try:
        # Validar nombre de archivo (seguridad)
        if not filename.startswith('relaticpanama_backup_') or not filename.endswith('.db'):
            return jsonify({'success': False, 'error': 'Nombre de archivo inválido'}), 400
        
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        backup_path = os.path.join(project_root, 'backups', filename)
        
        if not os.path.exists(backup_path):
            return jsonify({'success': False, 'error': 'Respaldo no encontrado'}), 404
        
        return send_file(
            backup_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/x-sqlite3'
        )
        
    except Exception as e:
        print(f"❌ Error al descargar respaldo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/backup/delete/<filename>', methods=['POST'])
@admin_required
def delete_backup(filename):
    """Eliminar un respaldo"""
    try:
        # Validar nombre de archivo (seguridad)
        if not filename.startswith('relaticpanama_backup_') or not filename.endswith('.db'):
            return jsonify({'success': False, 'error': 'Nombre de archivo inválido'}), 400
        
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        backup_path = os.path.join(project_root, 'backups', filename)
        
        if not os.path.exists(backup_path):
            return jsonify({'success': False, 'error': 'Respaldo no encontrado'}), 404
        
        os.remove(backup_path)
        
        return jsonify({'success': True, 'message': 'Respaldo eliminado exitosamente'})
        
    except Exception as e:
        print(f"❌ Error al eliminar respaldo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/backup/restore/<filename>', methods=['POST'])
@admin_required
def restore_backup(filename):
    """Restaurar base de datos desde un respaldo"""
    try:
        # Validar nombre de archivo (seguridad)
        if not filename.startswith('relaticpanama_backup_') or not filename.endswith('.db'):
            return jsonify({'success': False, 'error': 'Nombre de archivo inválido'}), 400
        
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        backup_path = os.path.join(project_root, 'backups', filename)
        db_path = os.path.join(project_root, 'instance', 'relaticpanama.db')
        
        if not os.path.exists(backup_path):
            return jsonify({'success': False, 'error': 'Respaldo no encontrado'}), 404
        
        # Crear respaldo de seguridad antes de restaurar
        import shutil
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safety_backup = os.path.join(project_root, 'backups', f'safety_backup_before_restore_{timestamp}.db')
        
        if os.path.exists(db_path):
            shutil.copy2(db_path, safety_backup)
            print(f"✅ Respaldo de seguridad creado: {safety_backup}")
        
        # Restaurar base de datos
        shutil.copy2(backup_path, db_path)
        
        print(f"✅ Base de datos restaurada desde: {filename}")
        
        return jsonify({
            'success': True, 
            'message': f'Base de datos restaurada exitosamente desde {filename}. Se creó un respaldo de seguridad antes de la restauración.'
        })
        
    except Exception as e:
        print(f"❌ Error al restaurar respaldo: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/payments/config', methods=['GET', 'POST', 'PUT'])
@admin_required
def api_payment_config():
    """API para obtener y actualizar configuración de pagos"""
    if request.method == 'GET':
        config = PaymentConfig.get_active_config()
        if config:
            return jsonify({'success': True, 'config': config.to_dict()})
        else:
            return jsonify({'success': False, 'message': 'No hay configuración activa'})
    
    elif request.method in ['POST', 'PUT']:
        data = request.get_json()
        
        # Desactivar todas las configuraciones anteriores
        PaymentConfig.query.update({'is_active': False})
        
        # Buscar si existe una configuración
        config = PaymentConfig.query.first()
        
        if not config:
            # Crear nueva configuración
            config = PaymentConfig(
                stripe_secret_key=data.get('stripe_secret_key', ''),
                stripe_publishable_key=data.get('stripe_publishable_key', ''),
                stripe_webhook_secret=data.get('stripe_webhook_secret', ''),
                paypal_client_id=data.get('paypal_client_id', ''),
                paypal_client_secret=data.get('paypal_client_secret', ''),
                paypal_mode=data.get('paypal_mode', 'sandbox'),
                paypal_return_url=data.get('paypal_return_url', ''),
                paypal_cancel_url=data.get('paypal_cancel_url', ''),
                banco_general_merchant_id=data.get('banco_general_merchant_id', ''),
                banco_general_api_key=data.get('banco_general_api_key', ''),
                banco_general_shared_secret=data.get('banco_general_shared_secret', ''),
                banco_general_api_url=data.get('banco_general_api_url', 'https://api.cybersource.com'),
                yappy_api_key=data.get('yappy_api_key', ''),
                yappy_merchant_id=data.get('yappy_merchant_id', ''),
                yappy_api_url=data.get('yappy_api_url', 'https://api.yappy.im'),
                use_environment_variables=bool(data.get('use_environment_variables', True)),
                is_active=True
            )
            db.session.add(config)
        else:
            # Actualizar configuración existente
            if 'stripe_secret_key' in data:
                config.stripe_secret_key = data.get('stripe_secret_key', config.stripe_secret_key)
            if 'stripe_publishable_key' in data:
                config.stripe_publishable_key = data.get('stripe_publishable_key', config.stripe_publishable_key)
            if 'stripe_webhook_secret' in data:
                config.stripe_webhook_secret = data.get('stripe_webhook_secret', config.stripe_webhook_secret)
            if 'paypal_client_id' in data:
                config.paypal_client_id = data.get('paypal_client_id', config.paypal_client_id)
            if 'paypal_client_secret' in data:
                config.paypal_client_secret = data.get('paypal_client_secret', config.paypal_client_secret)
            if 'paypal_mode' in data:
                config.paypal_mode = data.get('paypal_mode', config.paypal_mode)
            if 'paypal_return_url' in data:
                config.paypal_return_url = data.get('paypal_return_url', config.paypal_return_url)
            if 'paypal_cancel_url' in data:
                config.paypal_cancel_url = data.get('paypal_cancel_url', config.paypal_cancel_url)
            if 'banco_general_merchant_id' in data:
                config.banco_general_merchant_id = data.get('banco_general_merchant_id', config.banco_general_merchant_id)
            if 'banco_general_api_key' in data:
                config.banco_general_api_key = data.get('banco_general_api_key', config.banco_general_api_key)
            if 'banco_general_shared_secret' in data:
                config.banco_general_shared_secret = data.get('banco_general_shared_secret', config.banco_general_shared_secret)
            if 'banco_general_api_url' in data:
                config.banco_general_api_url = data.get('banco_general_api_url', config.banco_general_api_url)
            if 'yappy_api_key' in data:
                config.yappy_api_key = data.get('yappy_api_key', config.yappy_api_key)
            if 'yappy_merchant_id' in data:
                config.yappy_merchant_id = data.get('yappy_merchant_id', config.yappy_merchant_id)
            if 'yappy_api_url' in data:
                config.yappy_api_url = data.get('yappy_api_url', config.yappy_api_url)
            config.use_environment_variables = bool(data.get('use_environment_variables', config.use_environment_variables))
            config.is_active = True
            config.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Configuración de pagos actualizada exitosamente',
                'config': config.to_dict()
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

@app.route('/api/admin/email/templates/<int:template_id>/reset', methods=['POST'])
@admin_required
def api_email_template_reset(template_id):
    """API para resetear un template a su versión por defecto"""
    template = EmailTemplate.query.get_or_404(template_id)
    
    # Cargar template por defecto desde email_templates.py
    try:
        if EMAIL_TEMPLATES_AVAILABLE:
            # Importar función de template
            template_func_map = {
                'welcome': get_welcome_email,
                'membership_payment': get_membership_payment_confirmation_email,
                'membership_expiring': get_membership_expiring_email,
                'membership_expired': get_membership_expired_email,
                'membership_renewed': get_membership_renewed_email,
                'event_registration': get_event_registration_email,
                'event_cancellation': get_event_cancellation_email,
                'event_update': get_event_update_email,
                'appointment_confirmation': get_appointment_confirmation_email,
                'appointment_reminder': get_appointment_reminder_email,
            }
            
            if template.template_key in template_func_map:
                # Nota: Esto requiere pasar objetos mock, por ahora solo marcamos como no custom
                template.is_custom = False
                template.updated_at = datetime.utcnow()
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': f'Template "{template.name}" reseteado a versión por defecto'
                })
        
        return jsonify({
            'success': False,
            'error': 'No se pudo resetear el template'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# RUTAS ADMINISTRATIVAS - CÓDIGOS DE DESCUENTO
# ============================================================================

@app.route('/admin/discount-codes')
@admin_required
def admin_discount_codes():
    """Panel de gestión de códigos de descuento"""
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)

    query = DiscountCode.query
    
    # Filtro de búsqueda
    if search:
        query = query.filter(
            db.or_(
                DiscountCode.code.ilike(f'%{search}%'),
                DiscountCode.name.ilike(f'%{search}%')
            )
        )
    
    # Filtro de estado
    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'inactive':
        query = query.filter_by(is_active=False)
    
    # Ordenar y paginar
    query = query.order_by(DiscountCode.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    codes = pagination.items
    
    # Obtener descuento maestro activo
    master_discount = Discount.query.filter_by(is_master=True, is_active=True).first()
    
    # Obtener eventos para el selector (eventos publicados)
    events = Event.query.filter_by(publish_status='published').order_by(Event.title).all()
    
    return render_template('admin/discount_codes.html',
                         codes=codes,
                         pagination=pagination,
                         search=search,
                         status_filter=status_filter,
                         master_discount=master_discount,
                         events=events)


@app.route('/admin/discount-codes/create', methods=['POST'])
@admin_required
def admin_discount_code_create():
    """Crear nuevo código de descuento"""
    try:
        data = request.get_json() if request.is_json else request.form
        
        # Obtener datos del formulario
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        code_input = data.get('code', '').strip().upper()
        generate_auto = data.get('generate_auto', 'false') == 'true'
        prefix = data.get('prefix', 'DSC').strip().upper()
        discount_type = data.get('discount_type', 'percentage')
        value = float(data.get('value', 0))
        applies_to = data.get('applies_to', 'all')
        event_ids = data.get('event_ids', [])
        
        # Generar o validar código
        if generate_auto:
            code = generate_discount_code(prefix=prefix)
        else:
            if not code_input:
                return jsonify({'success': False, 'error': 'El código es requerido'}), 400
            
            # Verificar que no exista
            if DiscountCode.query.filter_by(code=code_input).first():
                return jsonify({'success': False, 'error': 'Este código ya existe'}), 400
            
            code = code_input
        
        # Validar valor
        if value <= 0:
            return jsonify({'success': False, 'error': 'El valor del descuento debe ser mayor a 0'}), 400
        
        if discount_type == 'percentage' and value > 100:
            return jsonify({'success': False, 'error': 'El porcentaje no puede ser mayor a 100%'}), 400
        
        # Fechas
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
        
        if start_date and end_date and start_date > end_date:
            return jsonify({'success': False, 'error': 'La fecha de inicio debe ser anterior a la fecha de fin'}), 400
        
        # Límites
        max_uses_total = int(data.get('max_uses_total', 0)) if data.get('max_uses_total') else None
        max_uses_per_user = int(data.get('max_uses_per_user', 1))
        
        # Event IDs (JSON)
        event_ids_json = None
        if event_ids and isinstance(event_ids, list):
            import json
            event_ids_json = json.dumps(event_ids)
        
        # Crear código
        discount_code = DiscountCode(
            code=code,
            name=name,
            description=description,
            discount_type=discount_type,
            value=value,
            applies_to=applies_to,
            event_ids=event_ids_json,
            start_date=start_date,
            end_date=end_date,
            max_uses_total=max_uses_total,
            max_uses_per_user=max_uses_per_user,
            created_by=current_user.id,
            is_active=True
        )
        
        db.session.add(discount_code)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Código de descuento creado exitosamente',
            'code_id': discount_code.id,
            'code': discount_code.code
        })
    
    except ValueError as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Error en los datos: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/discount-codes/<int:code_id>', methods=['GET'])
@admin_required
def admin_discount_code_get(code_id):
    """Obtener información de un código de descuento"""
    try:
        code = DiscountCode.query.get_or_404(code_id)
        
        # Parsear event_ids si existe
        event_ids = []
        if code.event_ids:
            import json
            try:
                event_ids = json.loads(code.event_ids)
            except:
                pass
        
        return jsonify({
            'success': True,
            'code': {
                'id': code.id,
                'code': code.code,
                'name': code.name,
                'description': code.description,
                'discount_type': code.discount_type,
                'value': code.value,
                'applies_to': code.applies_to,
                'event_ids': event_ids,
                'start_date': code.start_date.isoformat() if code.start_date else None,
                'end_date': code.end_date.isoformat() if code.end_date else None,
                'max_uses_total': code.max_uses_total,
                'max_uses_per_user': code.max_uses_per_user,
                'is_active': code.is_active,
                'current_uses': code.current_uses
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/discount-codes/<int:code_id>/update', methods=['POST'])
@admin_required
def admin_discount_code_update(code_id):
    """Actualizar código de descuento"""
    try:
        code = DiscountCode.query.get_or_404(code_id)
        data = request.get_json() if request.is_json else request.form
        
        # Actualizar campos
        if 'name' in data:
            code.name = data.get('name', '').strip()
        if 'description' in data:
            code.description = data.get('description', '').strip()
        if 'discount_type' in data:
            code.discount_type = data.get('discount_type')
        if 'value' in data:
            value = float(data.get('value', 0))
            if value <= 0:
                return jsonify({'success': False, 'error': 'El valor debe ser mayor a 0'}), 400
            if code.discount_type == 'percentage' and value > 100:
                return jsonify({'success': False, 'error': 'El porcentaje no puede ser mayor a 100%'}), 400
            code.value = value
        if 'applies_to' in data:
            code.applies_to = data.get('applies_to')
        if 'event_ids' in data:
            event_ids = data.get('event_ids', [])
            import json
            code.event_ids = json.dumps(event_ids) if event_ids else None
        
        # Fechas
        if 'start_date' in data:
            start_date_str = data.get('start_date')
            code.start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
        if 'end_date' in data:
            end_date_str = data.get('end_date')
            code.end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
        
        if code.start_date and code.end_date and code.start_date > code.end_date:
            return jsonify({'success': False, 'error': 'La fecha de inicio debe ser anterior a la fecha de fin'}), 400
        
        # Límites
        if 'max_uses_total' in data:
            max_uses = data.get('max_uses_total')
            code.max_uses_total = int(max_uses) if max_uses else None
        if 'max_uses_per_user' in data:
            code.max_uses_per_user = int(data.get('max_uses_per_user', 1))
        
        # Estado
        if 'is_active' in data:
            code.is_active = bool(data.get('is_active'))
        
        code.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Código de descuento actualizado exitosamente'
        })
    
    except ValueError as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Error en los datos: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/discount-codes/<int:code_id>/delete', methods=['POST'])
@admin_required
def admin_discount_code_delete(code_id):
    """Eliminar código de descuento"""
    try:
        code = DiscountCode.query.get_or_404(code_id)
        
        # Verificar si tiene aplicaciones
        if code.applications:
            return jsonify({
                'success': False,
                'error': 'No se puede eliminar un código que ya ha sido usado'
            }), 400
        
        db.session.delete(code)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Código de descuento eliminado exitosamente'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/discount-codes/generate', methods=['POST'])
@admin_required
def api_generate_discount_code():
    """API para generar código automáticamente"""
    try:
        data = request.get_json()
        prefix = data.get('prefix', 'DSC').strip().upper()
        length = int(data.get('length', 8))
        custom_part = data.get('custom_part', '').strip().upper()
        
        code = generate_discount_code(prefix=prefix, length=length, custom_part=custom_part if custom_part else None)
        
        return jsonify({
            'success': True,
            'code': code
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/services')
@admin_required
def admin_services():
    """Panel de administración de servicios"""
    status = request.args.get('status', 'all')
    search = request.args.get('search', '').strip()
    q = Service.query
    if status == 'active':
        q = q.filter_by(is_active=True)
    elif status == 'inactive':
        q = q.filter_by(is_active=False)
    if search:
        q = q.filter(Service.name.ilike(f'%{search}%'))
    services = q.order_by(Service.display_order, Service.name).all()
    return render_template('admin/services.html', services=services, current_status=status, search=search)

@app.route('/api/admin/services/create', methods=['POST'])
@admin_required
def admin_services_create():
    """Crear nuevo servicio"""
    try:
        data = request.get_json()
        
        # Manejar appointment_type_id
        appointment_type_id = data.get('appointment_type_id')
        if appointment_type_id == '' or appointment_type_id is None:
            appointment_type_id = None
        else:
            appointment_type_id = int(appointment_type_id) if appointment_type_id else None
            # Validar que el tipo de cita existe
            if appointment_type_id:
                appointment_type = AppointmentType.query.get(appointment_type_id)
                if not appointment_type:
                    return jsonify({'success': False, 'error': 'Tipo de cita no encontrado'}), 400
        
        service = Service(
            name=data.get('name'),
            description=data.get('description', ''),
            icon=data.get('icon', 'fas fa-cog'),
            membership_type=data.get('membership_type', 'basic'),
            external_link=data.get('external_link', ''),
            base_price=float(data.get('base_price', 50.0)),
            is_active=data.get('is_active', True),
            display_order=int(data.get('display_order', 0)),
            appointment_type_id=appointment_type_id
        )
        
        db.session.add(service)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Servicio creado exitosamente', 'service': service.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/admin/services/update/<int:service_id>', methods=['PUT'])
@admin_required
def admin_services_update(service_id):
    """Actualizar servicio"""
    try:
        service = Service.query.get_or_404(service_id)
        data = request.get_json()
        
        # Obtener planes seleccionados
        membership_plans = data.get('membership_plans', [])
        if isinstance(membership_plans, str):
            membership_plans = [membership_plans]
        elif not isinstance(membership_plans, list):
            # Fallback al método antiguo si viene membership_type
            membership_plans = [data.get('membership_type', service.membership_type)]
        
        if not membership_plans:
            return jsonify({'success': False, 'error': 'Debe seleccionar al menos un plan de membresía'}), 400
        
        # Jerarquía para determinar el plan base
        membership_hierarchy = {
            'basic': 0, 'pro': 1, 'premium': 2, 'deluxe': 3, 'corporativo': 4
        }
        
        # El plan base será el más bajo en jerarquía
        base_plan = min(membership_plans, key=lambda p: membership_hierarchy.get(p, 999))
        
        category_id = data.get('category_id')
        if category_id:
            # Verificar que la categoría existe
            category = ServiceCategory.query.get(category_id)
            if not category:
                return jsonify({'success': False, 'error': 'Categoría no encontrada'}), 400
        
        service.name = data.get('name', service.name)
        service.description = data.get('description', service.description)
        service.icon = data.get('icon', service.icon)
        service.membership_type = base_plan  # Actualizar plan base
        service.category_id = category_id if category_id else None
        service.external_link = data.get('external_link', service.external_link)
        service.base_price = float(data.get('base_price', service.base_price))
        service.is_active = data.get('is_active', service.is_active)
        service.display_order = int(data.get('display_order', service.display_order))
        
        # Manejar appointment_type_id
        appointment_type_id = data.get('appointment_type_id')
        if appointment_type_id == '' or appointment_type_id is None:
            service.appointment_type_id = None
        else:
            appointment_type_id = int(appointment_type_id) if appointment_type_id else None
            # Validar que el tipo de cita existe
            if appointment_type_id:
                appointment_type = AppointmentType.query.get(appointment_type_id)
                if not appointment_type:
                    return jsonify({'success': False, 'error': 'Tipo de cita no encontrado'}), 400
            service.appointment_type_id = appointment_type_id
        
        service.updated_at = datetime.utcnow()
        
        # Obtener todas las reglas de precio existentes
        existing_rules = {rule.membership_type: rule for rule in service.pricing_rules}
        
        # Actualizar o crear reglas para los planes seleccionados
        for plan in membership_plans:
            if plan != base_plan:  # El plan base no necesita regla
                if plan in existing_rules:
                    # Actualizar regla existente
                    existing_rules[plan].is_included = True
                    existing_rules[plan].is_active = True
                else:
                    # Crear nueva regla
                    rule = ServicePricingRule(
                        service_id=service.id,
                        membership_type=plan,
                        is_included=True,
                        is_active=True
                    )
                    db.session.add(rule)
        
        # Desactivar reglas para planes que ya no están seleccionados
        for plan, rule in existing_rules.items():
            if plan not in membership_plans:
                rule.is_active = False
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Servicio actualizado exitosamente', 'service': service.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/admin/services/<int:service_id>', methods=['GET'])
@admin_required
def admin_services_get(service_id):
    """Obtener un servicio por ID con sus reglas de precio"""
    try:
        service = Service.query.get_or_404(service_id)
        
        # Construir diccionario manualmente para evitar problemas de serialización
        service_dict = {
            'id': service.id,
            'name': service.name,
            'description': service.description or '',
            'icon': service.icon or 'fas fa-cog',
            'membership_type': service.membership_type,
            'category_id': service.category_id,
            'external_link': service.external_link or '',
            'base_price': float(service.base_price) if service.base_price else 0.0,
            'is_active': service.is_active,
            'display_order': service.display_order or 0,
            'appointment_type_id': service.appointment_type_id,
            'requires_appointment': service.requires_appointment()
        }
        
        # Incluir reglas de precio
        pricing_rules = ServicePricingRule.query.filter_by(service_id=service_id).all()
        service_dict['pricing_rules'] = [{
            'id': rule.id,
            'membership_type': rule.membership_type,
            'price': float(rule.price) if rule.price else None,
            'discount_percentage': float(rule.discount_percentage) if rule.discount_percentage else 0.0,
            'is_included': rule.is_included,
            'is_active': rule.is_active
        } for rule in pricing_rules]
        
        return jsonify({'success': True, 'service': service_dict})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 404

@app.route('/api/admin/appointment-types', methods=['GET'])
@admin_required
def admin_appointment_types_list():
    """Obtener lista de tipos de cita disponibles"""
    try:
        appointment_types = AppointmentType.query.order_by(AppointmentType.display_order, AppointmentType.name).all()
        types_list = [{
            'id': at.id,
            'name': at.name,
            'description': at.description or '',
            'duration_minutes': at.duration_minutes or 60
        } for at in appointment_types]
        return jsonify({'success': True, 'appointment_types': types_list})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

def generate_slots_from_availability(advisor_id, appointment_type_id, days_ahead=30, slot_interval_minutes=None):
    """
    Genera slots automáticamente desde AdvisorAvailability.
    Similar a cómo Odoo genera slots desde el Schedule tab.
    
    Args:
        advisor_id: ID del asesor
        appointment_type_id: ID del tipo de cita
        days_ahead: Días hacia adelante para generar slots (default: 30)
        slot_interval_minutes: Intervalo entre slots (None = usar duración del appointment_type)
    
    Returns:
        Lista de slots creados
    """
    from datetime import time as dt_time
    
    advisor = Advisor.query.get(advisor_id)
    appointment_type = AppointmentType.query.get(appointment_type_id)
    
    if not advisor or not appointment_type:
        return []
    
    # Verificar que el asesor está asignado a este tipo de cita
    assignment = AppointmentAdvisor.query.filter_by(
        appointment_type_id=appointment_type_id,
        advisor_id=advisor_id,
        is_active=True
    ).first()
    
    if not assignment:
        return []
    
    # Obtener disponibilidad específica del asesor para este servicio
    availabilities = AdvisorServiceAvailability.query.filter_by(
        advisor_id=advisor_id,
        appointment_type_id=appointment_type_id,
        is_active=True
    ).all()
    
    # Si no hay disponibilidad específica, usar la disponibilidad general del asesor
    if not availabilities:
        availabilities_general = AdvisorAvailability.query.filter_by(
            advisor_id=advisor_id,
            is_active=True
        ).all()
        
        if not availabilities_general:
            return []
        
        # Convertir AdvisorAvailability a formato compatible
        class AvailabilityWrapper:
            def __init__(self, av):
                self.day_of_week = av.day_of_week
                self.start_time = av.start_time
                self.end_time = av.end_time
                self.timezone = av.timezone
        
        availabilities = [AvailabilityWrapper(av) for av in availabilities_general]
    
    # Duración del slot
    slot_duration = appointment_type.duration()
    slot_interval = timedelta(minutes=slot_interval_minutes) if slot_interval_minutes else slot_duration
    
    # Rango de fechas
    start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=days_ahead)
    
    slots_created = []
    current_date = start_date
    
    while current_date < end_date:
        day_of_week = current_date.weekday()  # 0 = lunes, 6 = domingo
        
        # Buscar disponibilidades para este día de la semana
        day_availabilities = [av for av in availabilities if av.day_of_week == day_of_week]
        
        for availability in day_availabilities:
            # Combinar fecha con hora de inicio
            slot_start = datetime.combine(current_date.date(), availability.start_time)
            slot_end_time = availability.end_time
            
            # Generar slots dentro de este bloque de disponibilidad
            current_slot_start = slot_start
            
            while current_slot_start.time() < slot_end_time:
                current_slot_end = current_slot_start + slot_duration
                
                # Verificar que el slot no exceda el bloque de disponibilidad
                if current_slot_end.time() > slot_end_time:
                    break
                
                # Verificar que no esté en el pasado
                if current_slot_start < datetime.utcnow():
                    current_slot_start += slot_interval
                    continue
                
                # Verificar que no exista ya un slot en este horario
                existing_slot = AppointmentSlot.query.filter(
                    AppointmentSlot.advisor_id == advisor_id,
                    AppointmentSlot.appointment_type_id == appointment_type_id,
                    AppointmentSlot.start_datetime == current_slot_start,
                    AppointmentSlot.is_available == True
                ).first()
                
                if not existing_slot:
                    # Verificar conflictos con otros slots del mismo asesor
                    conflicting = AppointmentSlot.query.filter(
                        AppointmentSlot.advisor_id == advisor_id,
                        AppointmentSlot.start_datetime < current_slot_end,
                        AppointmentSlot.end_datetime > current_slot_start,
                        AppointmentSlot.is_available == True
                    ).first()
                    
                    if not conflicting:
                        # Crear nuevo slot
                        new_slot = AppointmentSlot(
                            appointment_type_id=appointment_type_id,
                            advisor_id=advisor_id,
                            start_datetime=current_slot_start,
                            end_datetime=current_slot_end,
                            capacity=1,
                            is_available=True,
                            is_auto_generated=True
                        )
                        db.session.add(new_slot)
                        slots_created.append(new_slot)
                
                current_slot_start += slot_interval
        
        current_date += timedelta(days=1)
    
    if slots_created:
        db.session.commit()
    
    return slots_created

@app.route('/api/appointments/calendar/<int:advisor_id>', methods=['GET'])
@login_required
def get_advisor_calendar(advisor_id):
    """
    Obtener disponibilidad del asesor en formato calendario.
    Similar a cómo Odoo muestra disponibilidad en calendario.
    """
    try:
        appointment_type_id = request.args.get('appointment_type_id', type=int)
        service_id = request.args.get('service_id', type=int)
        start_date = request.args.get('start')  # YYYY-MM-DD
        end_date = request.args.get('end')  # YYYY-MM-DD
        
        # Si viene service_id, obtener appointment_type_id del servicio
        if service_id and not appointment_type_id:
            service = Service.query.get(service_id)
            if service and service.appointment_type_id:
                appointment_type_id = service.appointment_type_id
        
        if not appointment_type_id:
            return jsonify({'success': False, 'error': 'appointment_type_id o service_id requerido'}), 400
        
        advisor = Advisor.query.get_or_404(advisor_id)
        
        # Verificar que el asesor está asignado a este tipo de cita
        assignment = AppointmentAdvisor.query.filter_by(
            appointment_type_id=appointment_type_id,
            advisor_id=advisor_id,
            is_active=True
        ).first()
        
        if not assignment:
            return jsonify({'success': False, 'error': 'Asesor no asignado a este tipo de cita'}), 400
        
        # Generar slots si no existen (solo para próximos 30 días)
        appointment_type = AppointmentType.query.get(appointment_type_id)
        if appointment_type:
            # Generar slots automáticamente si no hay suficientes
            existing_slots_count = AppointmentSlot.query.filter(
                AppointmentSlot.advisor_id == advisor_id,
                AppointmentSlot.appointment_type_id == appointment_type_id,
                AppointmentSlot.start_datetime >= datetime.utcnow(),
                AppointmentSlot.start_datetime <= datetime.utcnow() + timedelta(days=30)
            ).count()
            
            if existing_slots_count < 10:  # Si hay menos de 10 slots, generar más
                generate_slots_from_availability(advisor_id, appointment_type_id, days_ahead=30)
        
        # Parsear fechas si vienen
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            except:
                start_dt = datetime.utcnow()
        else:
            start_dt = datetime.utcnow()
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            except:
                end_dt = start_dt + timedelta(days=30)
        else:
            end_dt = start_dt + timedelta(days=30)
        
        # Obtener slots disponibles
        slots = AppointmentSlot.query.filter(
            AppointmentSlot.advisor_id == advisor_id,
            AppointmentSlot.appointment_type_id == appointment_type_id,
            AppointmentSlot.start_datetime >= start_dt,
            AppointmentSlot.start_datetime < end_dt,
            AppointmentSlot.is_available == True
        ).order_by(AppointmentSlot.start_datetime.asc()).all()
        
        # Obtener disponibilidad base del asesor
        availabilities = AdvisorAvailability.query.filter_by(
            advisor_id=advisor_id,
            is_active=True
        ).all()
        
        # Formatear para calendario (formato FullCalendar)
        calendar_events = []
        
        # Agregar slots disponibles
        for slot in slots:
            calendar_events.append({
                'id': f'slot_{slot.id}',
                'title': f'Disponible ({slot.remaining_seats()} cupos)',
                'start': slot.start_datetime.isoformat(),
                'end': slot.end_datetime.isoformat(),
                'backgroundColor': '#28a745',  # Verde para disponible
                'borderColor': '#28a745',
                'textColor': '#fff',
                'extendedProps': {
                    'type': 'slot',
                    'slot_id': slot.id,
                    'available': True,
                    'remaining_seats': slot.remaining_seats(),
                    'capacity': slot.capacity
                }
            })
        
        # Agregar disponibilidad base (horarios regulares)
        availability_info = []
        for av in availabilities:
            day_names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            availability_info.append({
                'day_of_week': av.day_of_week,
                'day_name': day_names[av.day_of_week],
                'start_time': av.start_time.strftime('%H:%M'),
                'end_time': av.end_time.strftime('%H:%M'),
                'timezone': av.timezone
            })
        
        return jsonify({
            'success': True,
            'advisor': {
                'id': advisor.id,
                'name': f"{advisor.user.first_name} {advisor.user.last_name}" if advisor.user else 'Asesor',
                'bio': advisor.bio,
                'specializations': advisor.specializations
            },
            'appointment_type': {
                'id': appointment_type.id,
                'name': appointment_type.name,
                'duration_minutes': appointment_type.duration_minutes
            },
            'events': calendar_events,
            'availability': availability_info,
            'timezone': availabilities[0].timezone if availabilities else 'America/Panama'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/services/<int:service_id>/calendar', methods=['GET'])
@login_required
def get_service_calendar(service_id):
    """
    Obtener calendario unificado de un servicio.
    Muestra todos los espacios disponibles de todos los asesores que atienden ese servicio.
    Formato compatible con FullCalendar.
    """
    try:
        start_date = request.args.get('start')  # YYYY-MM-DD
        end_date = request.args.get('end')  # YYYY-MM-DD
        advisor_id_filter = request.args.get('advisor_id', type=int)  # Filtro opcional por asesor
        
        # 1. Obtener servicio y verificar que requiere cita
        service = Service.query.get_or_404(service_id)
        if not service.is_active:
            return jsonify({'success': False, 'error': 'Este servicio no está disponible'}), 400
        
        if not service.requires_appointment():
            return jsonify({'success': False, 'error': 'Este servicio no requiere cita'}), 400
        
        # 2. Obtener appointment_type_id del servicio
        appointment_type_id = service.appointment_type_id
        if not appointment_type_id:
            return jsonify({'success': False, 'error': 'Este servicio no tiene tipo de cita configurado'}), 400
        
        appointment_type = AppointmentType.query.get(appointment_type_id)
        if not appointment_type or not appointment_type.is_active:
            return jsonify({'success': False, 'error': 'El tipo de cita asociado no está disponible'}), 400
        
        # 3. Obtener TODOS los asesores asignados a este servicio
        advisor_assignments = AppointmentAdvisor.query.filter_by(
            appointment_type_id=appointment_type_id,
            is_active=True
        ).join(Advisor).filter(Advisor.is_active == True).all()
        
        if not advisor_assignments:
            return jsonify({
                'success': True,
                'service': {'id': service.id, 'name': service.name},
                'advisors': [],
                'events': [],
                'total_slots': 0,
                'message': 'No hay asesores asignados a este servicio'
            })
        
        advisor_ids = [aa.advisor_id for aa in advisor_assignments]
        
        # Aplicar filtro de asesor si viene
        if advisor_id_filter:
            if advisor_id_filter not in advisor_ids:
                return jsonify({'success': False, 'error': 'Asesor no asignado a este servicio'}), 400
            advisor_ids = [advisor_id_filter]
        
        # 4. Generar slots para todos los asesores si no hay suficientes
        for advisor_id in advisor_ids:
            existing_slots_count = AppointmentSlot.query.filter(
                AppointmentSlot.advisor_id == advisor_id,
                AppointmentSlot.appointment_type_id == appointment_type_id,
                AppointmentSlot.start_datetime >= datetime.utcnow(),
                AppointmentSlot.start_datetime <= datetime.utcnow() + timedelta(days=30)
            ).count()
            
            if existing_slots_count < 10:
                generate_slots_from_availability(advisor_id, appointment_type_id, days_ahead=30)
        
        # 5. Parsear fechas
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            except:
                start_dt = datetime.utcnow()
        else:
            start_dt = datetime.utcnow()
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            except:
                end_dt = start_dt + timedelta(days=30)
        else:
            end_dt = start_dt + timedelta(days=30)
        
        # 6. Obtener TODOS los slots disponibles de TODOS los asesores
        from sqlalchemy.orm import joinedload
        slots = AppointmentSlot.query.options(
            joinedload(AppointmentSlot.advisor).joinedload(Advisor.user)
        ).filter(
            AppointmentSlot.appointment_type_id == appointment_type_id,
            AppointmentSlot.advisor_id.in_(advisor_ids),
            AppointmentSlot.start_datetime >= start_dt,
            AppointmentSlot.start_datetime < end_dt,
            AppointmentSlot.is_available == True
        ).order_by(AppointmentSlot.start_datetime.asc()).all()
        
        print(f"Servicio {service_id}: Encontrados {len(slots)} slots disponibles entre {start_dt} y {end_dt}")
        
        # 7. Formatear para calendario (FullCalendar)
        calendar_events = []
        for slot in slots:
            try:
                advisor_name = 'Asesor'
                if slot.advisor:
                    if slot.advisor.user:
                        advisor_name = f"{slot.advisor.user.first_name} {slot.advisor.user.last_name}"
                    else:
                        advisor_name = f"Asesor #{slot.advisor.id}"
                
                # Validar que start_datetime y end_datetime existan
                if not slot.start_datetime or not slot.end_datetime:
                    continue
                
                remaining_seats = 1
                if hasattr(slot, 'remaining_seats'):
                    try:
                        remaining_seats = slot.remaining_seats()
                    except:
                        remaining_seats = slot.capacity if slot.capacity else 1
                
                calendar_events.append({
                    'id': f'slot_{slot.id}',
                    'title': f'Disponible - {advisor_name}',
                    'start': slot.start_datetime.isoformat(),
                    'end': slot.end_datetime.isoformat(),
                    'backgroundColor': '#28a745',  # Verde para disponible
                    'borderColor': '#28a745',
                    'textColor': '#fff',
                    'extendedProps': {
                        'type': 'slot',
                        'slot_id': slot.id,
                        'advisor_id': slot.advisor_id,
                        'advisor_name': advisor_name,
                        'service_id': service_id,
                        'service_name': service.name,
                        'remaining_seats': remaining_seats,
                        'capacity': slot.capacity if slot.capacity else 1,
                        'available': True
                    }
                })
            except Exception as e:
                print(f"Error procesando slot {slot.id}: {e}")
                continue
        
        # 8. Información de asesores
        advisors_info = []
        for assignment in advisor_assignments:
            try:
                advisor = assignment.advisor
                if advisor_id_filter and advisor.id != advisor_id_filter:
                    continue
                
                advisor_name = 'Asesor'
                if advisor.user:
                    advisor_name = f"{advisor.user.first_name} {advisor.user.last_name}"
                else:
                    advisor_name = f"Asesor #{advisor.id}"
                
                advisors_info.append({
                    'id': advisor.id,
                    'name': advisor_name,
                    'bio': advisor.bio if advisor.bio else '',
                    'specializations': advisor.specializations if advisor.specializations else '',
                    'photo_url': advisor.photo_url if advisor.photo_url else ''
                })
            except Exception as e:
                print(f"Error procesando asesor {assignment.advisor_id}: {e}")
                continue
        
        return jsonify({
            'success': True,
            'service': {
                'id': service.id,
                'name': service.name,
                'appointment_type_id': appointment_type_id,
                'appointment_type_name': appointment_type.name,
                'duration_minutes': appointment_type.duration_minutes
            },
            'advisors': advisors_info,
            'events': calendar_events,
            'total_slots': len(calendar_events),
            'date_range': {
                'start': start_dt.isoformat(),
                'end': end_dt.isoformat()
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/admin/services/delete/<int:service_id>', methods=['DELETE'])
@admin_required
def admin_services_delete(service_id):
    """Eliminar servicio"""
    try:
        service = Service.query.get_or_404(service_id)
        db.session.delete(service)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Servicio eliminado exitosamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

# ==================== RUTAS ADMIN PARA CATEGORÍAS DE SERVICIOS ====================

@app.route('/admin/service-categories')
@admin_required
def admin_service_categories():
    """Panel de administración de categorías de servicios"""
    categories = ServiceCategory.query.order_by(ServiceCategory.display_order, ServiceCategory.name).all()
    return render_template('admin/service_categories.html', categories=categories)

@app.route('/api/admin/service-categories/create', methods=['POST'])
@admin_required
def admin_service_categories_create():
    """Crear nueva categoría"""
    try:
        data = request.get_json()
        
        # Generar slug si no se proporciona
        slug = data.get('slug', '').strip()
        if not slug:
            from flask import url_for
            import re
            name = data.get('name', '').strip()
            slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        
        # Verificar que el slug sea único
        existing = ServiceCategory.query.filter_by(slug=slug).first()
        if existing:
            counter = 1
            original_slug = slug
            while existing:
                slug = f"{original_slug}-{counter}"
                existing = ServiceCategory.query.filter_by(slug=slug).first()
                counter += 1
        
        category = ServiceCategory(
            name=data.get('name'),
            slug=slug,
            description=data.get('description', ''),
            icon=data.get('icon', 'fas fa-folder'),
            color=data.get('color', 'primary'),
            display_order=int(data.get('display_order', 0)),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(category)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Categoría creada exitosamente', 'category': category.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/admin/service-categories/update/<int:category_id>', methods=['PUT'])
@admin_required
def admin_service_categories_update(category_id):
    """Actualizar categoría"""
    try:
        category = ServiceCategory.query.get_or_404(category_id)
        data = request.get_json()
        
        # Verificar slug único si se cambia
        new_slug = data.get('slug', category.slug).strip()
        if new_slug != category.slug:
            existing = ServiceCategory.query.filter_by(slug=new_slug).first()
            if existing and existing.id != category_id:
                return jsonify({'success': False, 'error': 'El slug ya está en uso'}), 400
        
        category.name = data.get('name', category.name)
        category.slug = new_slug
        category.description = data.get('description', category.description)
        category.icon = data.get('icon', category.icon)
        category.color = data.get('color', category.color)
        category.display_order = int(data.get('display_order', category.display_order))
        category.is_active = data.get('is_active', category.is_active)
        category.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Categoría actualizada exitosamente', 'category': category.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/admin/service-categories/<int:category_id>', methods=['GET'])
@admin_required
def admin_service_categories_get(category_id):
    """Obtener una categoría por ID"""
    try:
        category = ServiceCategory.query.get_or_404(category_id)
        return jsonify({'success': True, 'category': category.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 404

@app.route('/api/admin/service-categories/delete/<int:category_id>', methods=['DELETE'])
@admin_required
def admin_service_categories_delete(category_id):
    """Eliminar categoría"""
    try:
        category = ServiceCategory.query.get_or_404(category_id)
        
        # Verificar si tiene servicios asociados
        if category.services:
            return jsonify({
                'success': False, 
                'error': f'No se puede eliminar la categoría porque tiene {len(category.services)} servicio(s) asociado(s)'
            }), 400
        
        db.session.delete(category)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Categoría eliminada exitosamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/admin/service-categories', methods=['GET'])
@admin_required
def admin_service_categories_list():
    """Listar todas las categorías activas (para selects)"""
    try:
        categories = ServiceCategory.query.filter_by(is_active=True).order_by(ServiceCategory.display_order, ServiceCategory.name).all()
        return jsonify({
            'success': True, 
            'categories': [cat.to_dict() for cat in categories]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== RUTAS ADMIN PARA DESCUENTOS DE MEMBRESÍA ====================

@app.route('/admin/membership-discounts')
@admin_required
def admin_membership_discounts():
    """Panel de administración de descuentos por membresía"""
    discounts = MembershipDiscount.query.order_by(
        MembershipDiscount.product_type,
        MembershipDiscount.membership_type
    ).all()
    return render_template('admin/membership_discounts.html', discounts=discounts)

@app.route('/api/admin/membership-discounts/create', methods=['POST'])
@admin_required
def admin_membership_discounts_create():
    """Crear nuevo descuento de membresía"""
    try:
        data = request.get_json()
        
        # Validar que no exista ya un descuento para esta combinación
        existing = MembershipDiscount.query.filter_by(
            membership_type=data.get('membership_type'),
            product_type=data.get('product_type')
        ).first()
        
        if existing:
            return jsonify({
                'success': False,
                'error': f'Ya existe un descuento para {data.get("membership_type")} - {data.get("product_type")}'
            }), 400
        
        discount = MembershipDiscount(
            membership_type=data.get('membership_type'),
            product_type=data.get('product_type'),
            discount_percentage=float(data.get('discount_percentage', 0)),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(discount)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Descuento creado exitosamente',
            'discount': discount.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/admin/membership-discounts/update/<int:discount_id>', methods=['PUT'])
@admin_required
def admin_membership_discounts_update(discount_id):
    """Actualizar descuento de membresía"""
    try:
        discount = MembershipDiscount.query.get_or_404(discount_id)
        data = request.get_json()
        
        # Si cambia membership_type o product_type, verificar que no exista otro
        new_membership_type = data.get('membership_type', discount.membership_type)
        new_product_type = data.get('product_type', discount.product_type)
        
        if (new_membership_type != discount.membership_type or 
            new_product_type != discount.product_type):
            existing = MembershipDiscount.query.filter_by(
                membership_type=new_membership_type,
                product_type=new_product_type
            ).first()
            
            if existing and existing.id != discount_id:
                return jsonify({
                    'success': False,
                    'error': f'Ya existe un descuento para {new_membership_type} - {new_product_type}'
                }), 400
        
        discount.membership_type = new_membership_type
        discount.product_type = new_product_type
        discount.discount_percentage = float(data.get('discount_percentage', discount.discount_percentage))
        discount.is_active = data.get('is_active', discount.is_active)
        discount.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Descuento actualizado exitosamente',
            'discount': discount.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/admin/membership-discounts/<int:discount_id>', methods=['GET'])
@admin_required
def admin_membership_discounts_get(discount_id):
    """Obtener un descuento por ID"""
    try:
        discount = MembershipDiscount.query.get_or_404(discount_id)
        return jsonify({'success': True, 'discount': discount.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 404

@app.route('/api/admin/membership-discounts/delete/<int:discount_id>', methods=['DELETE'])
@admin_required
def admin_membership_discounts_delete(discount_id):
    """Eliminar descuento de membresía"""
    try:
        discount = MembershipDiscount.query.get_or_404(discount_id)
        db.session.delete(discount)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Descuento eliminado exitosamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/admin/master-discount', methods=['GET', 'POST'])
@admin_required
def admin_master_discount():
    """Gestionar descuento maestro"""
    if request.method == 'GET':
        master_discount = Discount.query.filter_by(is_master=True, is_active=True).first()
        return render_template('admin/master_discount.html', master_discount=master_discount)
    
    # POST - Crear o actualizar descuento maestro
    try:
        data = request.get_json() if request.is_json else request.form
        
        # Desactivar todos los descuentos maestros anteriores
        Discount.query.filter_by(is_master=True).update({'is_master': False})
        
        # Verificar si se está activando o desactivando
        is_active = data.get('is_active', 'false') == 'true'
        
        if not is_active:
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Descuento maestro desactivado'
            })
        
        # Crear o actualizar descuento maestro
        discount_id = data.get('discount_id')
        
        if discount_id:
            # Usar descuento existente
            discount = Discount.query.get_or_404(discount_id)
            discount.is_master = True
            discount.is_active = True
        else:
            # Crear nuevo descuento maestro
            name = data.get('name', 'Descuento Maestro').strip()
            discount_type = data.get('discount_type', 'percentage')
            value = float(data.get('value', 0))
            
            if value <= 0:
                return jsonify({'success': False, 'error': 'El valor debe ser mayor a 0'}), 400
            
            discount = Discount(
                name=name,
                code=f'MASTER-{int(datetime.utcnow().timestamp())}',
                discount_type=discount_type,
                value=value,
                is_master=True,
                is_active=True,
                applies_automatically=True
            )
            db.session.add(discount)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Descuento maestro configurado exitosamente',
            'discount_id': discount.id
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Registrar blueprints de eventos
try:
    from event_routes import events_bp, admin_events_bp, events_api_bp
    app.register_blueprint(events_bp)
    app.register_blueprint(admin_events_bp)
    app.register_blueprint(events_api_bp)
except ImportError as e:
    print(f"Warning: No se pudieron registrar los blueprints de eventos: {e}")

# Registrar blueprints de citas/appointments
try:
    from appointment_routes import appointments_bp, admin_appointments_bp, appointments_api_bp
    app.register_blueprint(appointments_bp)
    app.register_blueprint(admin_appointments_bp)
    app.register_blueprint(appointments_api_bp)
    
    # Registrar API de slots para asesores
    try:
        from api_advisor_slots import advisor_slots_api_bp
        app.register_blueprint(advisor_slots_api_bp)
    except ImportError:
        pass  # Opcional
except ImportError as e:
    print(f"Warning: No se pudieron registrar los blueprints de citas: {e}")

# Funciones de utilidad
def create_sample_data():
    """Crear datos de ejemplo"""
    # Crear beneficios de ejemplo
    benefits = [
        Benefit(name='Acceso a Revistas', description='Acceso completo a la biblioteca de revistas especializadas', membership_type='basic'),
        Benefit(name='Base de Datos', description='Acceso a bases de datos de investigación', membership_type='basic'),
        Benefit(name='Asesoría de Publicación', description='Sesiones de asesoría para publicaciones académicas', membership_type='premium'),
        Benefit(name='Soporte Prioritario', description='Soporte técnico prioritario', membership_type='premium'),
    ]
    
    for benefit in benefits:
        if not Benefit.query.filter_by(name=benefit.name).first():
            db.session.add(benefit)
    
    db.session.commit()

# Ruta para obtener notificaciones del usuario
@app.route('/api/notifications')
@login_required
def api_notifications():
    """API para obtener notificaciones del usuario"""
    # Obtener filtros de query params
    notification_type = request.args.get('type', 'all')
    status = request.args.get('status', 'all')  # all, read, unread
    limit = int(request.args.get('limit', 50))
    
    # Construir query
    query = Notification.query.filter_by(user_id=current_user.id)
    
    # Filtrar por tipo
    if notification_type != 'all':
        query = query.filter_by(notification_type=notification_type)
    
    # Filtrar por estado
    if status == 'read':
        query = query.filter_by(is_read=True)
    elif status == 'unread':
        query = query.filter_by(is_read=False)
    
    # Obtener conteos
    unread_count = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).count()
    
    # Obtener notificaciones
    notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
    
    return jsonify({
        'unread_count': unread_count,
        'total': len(notifications),
        'notifications': [{
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'type': n.notification_type,
            'is_read': n.is_read,
            'event_id': n.event_id,
            'created_at': n.created_at.isoformat() if n.created_at else None,
            'email_sent': n.email_sent,
            'email_sent_at': n.email_sent_at.isoformat() if n.email_sent_at else None
        } for n in notifications]
    })

@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Marcar notificación como leída"""
    try:
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=current_user.id
        ).first()
        
        if not notification:
            return jsonify({
                'success': False,
                'error': 'Notificación no encontrada'
            }), 404
        
        if notification.is_read:
            return jsonify({
                'success': True,
                'message': 'Notificación ya estaba marcada como leída'
            })
        
        notification.mark_as_read()
        db.session.commit()
        
        print(f"✅ Notificación {notification_id} marcada como leída por usuario {current_user.id}")
        return jsonify({
            'success': True,
            'message': 'Notificación marcada como leída',
            'notification': {
                'id': notification.id,
                'is_read': notification.is_read
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error marcando notificación {notification_id} como leída: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Marcar todas las notificaciones como leídas"""
    try:
        Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).update({'is_read': True})
        db.session.commit()
        return jsonify({'success': True, 'message': 'Todas las notificaciones han sido marcadas como leídas'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/notifications/<int:notification_id>', methods=['DELETE'])
@login_required
def delete_notification(notification_id):
    """Eliminar notificación"""
    try:
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=current_user.id
        ).first()
        
        if not notification:
            return jsonify({
                'success': False, 
                'error': 'Notificación no encontrada o no tienes permisos para eliminarla'
            }), 404
        
        db.session.delete(notification)
        db.session.commit()
        
        print(f"✅ Notificación {notification_id} eliminada por usuario {current_user.id}")
        return jsonify({
            'success': True, 
            'message': 'Notificación eliminada exitosamente'
        })
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error eliminando notificación {notification_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': f'Error al eliminar notificación: {str(e)}'
        }), 500

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        ensure_email_log_columns()  # Asegurar columnas antes de crear datos de muestra
        create_sample_data()
        # Aplicar configuración de email desde BD después de crear tablas
        apply_email_config_from_db()
    
    app.run(host='0.0.0.0', port=9000, debug=True)
