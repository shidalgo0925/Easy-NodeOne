"""Modelos ORM (NodeOne)."""
from datetime import datetime, timedelta
import json
import os
import re
import secrets
from flask import has_request_context, url_for
from flask_login import UserMixin, current_user
from sqlalchemy import text as sql_text
from werkzeug.security import generate_password_hash, check_password_hash

from nodeone.core.db import db

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
        if self.end_date is None:
            return self.status == 'active'
        return self.status == 'active' and datetime.utcnow() <= self.end_date
    
    @property
    def is_active(self):
        """Propiedad para compatibilidad con Membership"""
        return self.is_currently_active()

class PaymentConfig(db.Model):
    """Configuración de métodos de pago"""
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )

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
            'organization_id': self.organization_id,
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
    def get_active_config(organization_id=None, allow_fallback_to_default_org=True):
        """
        Configuración de pagos activa (multi-tenant, alineada a EmailConfig).
        - organization_id=None: primera fila activa (arranque / legado).
        - Con organization_id: fila activa del tenant; fallback a org por defecto y filas legacy (NULL).
        """
        q_active = PaymentConfig.query.filter_by(is_active=True)
        if organization_id is None:
            return q_active.order_by(PaymentConfig.id.asc()).first()
        oid = int(organization_id)
        row = q_active.filter_by(organization_id=oid).order_by(PaymentConfig.id.asc()).first()
        if row is not None:
            return row
        if not allow_fallback_to_default_org:
            return None
        try:
            from utils.organization import default_organization_id

            def_oid = int(default_organization_id())
        except Exception:
            def_oid = None
        if def_oid is not None:
            row = q_active.filter_by(organization_id=def_oid).order_by(PaymentConfig.id.asc()).first()
            if row is not None:
                return row
        return (
            q_active.filter(PaymentConfig.organization_id.is_(None)).order_by(PaymentConfig.id.asc()).first()
        )

    @staticmethod
    def get_active_config_for_user_id(user_id, memo=None):
        """Config activa del tenant del usuario; memo opcional dict oid -> PaymentConfig (cron)."""
        from utils.organization import payment_organization_id_for_user_id

        oid = payment_organization_id_for_user_id(user_id)
        if memo is not None and oid in memo:
            return memo[oid]
        cfg = PaymentConfig.get_active_config(organization_id=oid)
        if memo is not None:
            memo[oid] = cfg
        return cfg

    @staticmethod
    def processor_for_payment_user(payment, method, config_memo=None, processor_memo=None):
        """Procesador y config para un Payment; caches opcionales para el bucle del scheduler."""
        from payment_processors import get_payment_processor

        cfg = PaymentConfig.get_active_config_for_user_id(
            getattr(payment, 'user_id', None), config_memo
        )
        if not cfg:
            return None, None
        if processor_memo is not None:
            key = (cfg.id, method)
            if key not in processor_memo:
                processor_memo[key] = get_payment_processor(method, cfg)
            return processor_memo[key], cfg
        return get_payment_processor(method, cfg), cfg
    
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

    def get_stripe_webhook_secret(self):
        """Signing secret del webhook (BD o STRIPE_WEBHOOK_SECRET)."""
        if self.use_environment_variables:
            return os.getenv('STRIPE_WEBHOOK_SECRET', '')
        return self.stripe_webhook_secret or ''

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

