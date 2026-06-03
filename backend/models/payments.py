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
    # pending, succeeded, …; yappy_manual: pending_receipt|pending_payment, pending_admin_review|pending_validation, …
    status = db.Column(db.String(32), default='pending')
    
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

    # Yappy manual (QR sin API): validación administrativa
    amount_received_cents = db.Column(db.Integer, nullable=True)  # monto que reportó/validó el admin (centavos)
    validated_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    validated_at = db.Column(db.DateTime, nullable=True)
    validation_observations = db.Column(db.Text)  # observaciones al aprobar/rechazar/marcar parcial
    yappy_manual_audit_json = db.Column(db.Text)  # lista JSON de eventos de auditoría

    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    payment_user_reference = db.Column(db.String(500))  # nota / referencia del cliente (Yappy manual)
    receipt_uploaded_at = db.Column(db.DateTime, nullable=True)
    receipt_disk_path = db.Column(db.String(500))  # ruta relativa bajo uploads/payments/yappy/{org_id}/
    rejection_reason = db.Column(db.Text)

    # Metadata adicional (JSON) - usando payment_metadata porque metadata es reservado en SQLAlchemy
    payment_metadata = db.Column(db.Text)  # JSON con información adicional del pago
    
    # Fechas
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    paid_at = db.Column(db.DateTime)  # Fecha cuando se confirmó el pago
    
    user = db.relationship('User', backref=db.backref('payments', lazy=True), foreign_keys=[user_id])
    validated_by = db.relationship(
        'User', foreign_keys=[validated_by_user_id], viewonly=True, overlaps='payments'
    )
    
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
            'amount_received_cents': self.amount_received_cents,
            'validated_by_user_id': self.validated_by_user_id,
            'validated_at': self.validated_at.isoformat() if self.validated_at else None,
            'validation_observations': self.validation_observations,
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
    banco_general_beneficiary_name = db.Column(db.String(400))
    banco_general_bank_name = db.Column(db.String(200))
    banco_general_account_number = db.Column(db.String(80))
    banco_general_account_type = db.Column(db.String(80))

    # Yappy
    yappy_api_key = db.Column(db.String(500))
    yappy_merchant_id = db.Column(db.String(200))
    yappy_api_url = db.Column(db.String(500), default='https://api.yappy.im')
    # Yappy en checkout (QR / directorio; usado también por yappy_manual)
    yappy_directory_name = db.Column(db.String(100))
    yappy_qr_image_path = db.Column(db.String(500))
    yappy_business_name = db.Column(db.String(200))
    # Teléfono en tarjeta «visualización checkout»; si no hay yappy_phone_or_identifier, cuenta para Yappy manual
    yappy_merchant_phone = db.Column(db.String(64))
    # Yappy solo QR + validación admin (sin API bancaria)
    yappy_manual_enabled = db.Column(db.Boolean, default=False)
    yappy_manual_instructions = db.Column(db.Text)  # HTML o texto visible al cliente
    yappy_manual_admin_emails = db.Column(db.Text)  # correos separados por coma para alertas
    yappy_display_name = db.Column(db.String(200))  # nombre visible en checkout (si vacío → yappy_business_name)
    yappy_phone_or_identifier = db.Column(db.String(120))
    yappy_instructions = db.Column(db.Text)  # si vacío → yappy_manual_instructions
    yappy_requires_receipt = db.Column(db.Boolean, default=True, nullable=False)
    yappy_admin_validation_required = db.Column(db.Boolean, default=True, nullable=False)

    # Transferencia internacional (SWIFT / cuenta Panamá)
    intl_wire_enabled = db.Column(db.Boolean, default=True)
    intl_wire_beneficiary_name = db.Column(db.String(400))
    intl_wire_bank_name = db.Column(db.String(200))
    intl_wire_swift = db.Column(db.String(32))
    intl_wire_account = db.Column(db.String(80))
    intl_wire_account_type = db.Column(db.String(80))
    intl_wire_country = db.Column(db.String(120))
    intl_wire_instructions = db.Column(db.Text)

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
            'paypal_client_id': self.paypal_client_id if not self.use_environment_variables else '[Desde variables de entorno]',
            'paypal_mode': self.paypal_mode,
            'paypal_return_url': self.paypal_return_url,
            'paypal_cancel_url': self.paypal_cancel_url,
            'banco_general_merchant_id': self.banco_general_merchant_id if not self.use_environment_variables else '[Desde variables de entorno]',
            'banco_general_api_url': self.banco_general_api_url,
            'banco_general_beneficiary_name': self.banco_general_beneficiary_name or '',
            'banco_general_bank_name': self.banco_general_bank_name or '',
            'banco_general_account_number': self.banco_general_account_number or '',
            'banco_general_account_type': self.banco_general_account_type or '',
            'yappy_merchant_id': self.yappy_merchant_id if not self.use_environment_variables else '[Desde variables de entorno]',
            'yappy_api_url': self.yappy_api_url,
            'yappy_directory_name': self.yappy_directory_name or '',
            'yappy_qr_image_path': self.yappy_qr_image_path or '',
            'yappy_business_name': self.yappy_business_name or '',
            'yappy_merchant_phone': (self.yappy_merchant_phone or '')
            if getattr(self, 'yappy_merchant_phone', None) is not None
            else '',
            'yappy_manual_enabled': bool(self.yappy_manual_enabled),
            'yappy_manual_instructions': self.yappy_manual_instructions or '',
            'yappy_manual_admin_emails': self.yappy_manual_admin_emails or '',
            'yappy_display_name': (self.yappy_display_name or '') if getattr(self, 'yappy_display_name', None) is not None else '',
            'yappy_phone_or_identifier': (self.yappy_phone_or_identifier or '')
            if getattr(self, 'yappy_phone_or_identifier', None) is not None
            else '',
            'yappy_instructions': (self.yappy_instructions or '') if getattr(self, 'yappy_instructions', None) is not None else '',
            'yappy_requires_receipt': bool(getattr(self, 'yappy_requires_receipt', True)),
            'yappy_admin_validation_required': bool(getattr(self, 'yappy_admin_validation_required', True)),
            'intl_wire_enabled': bool(getattr(self, 'intl_wire_enabled', True)),
            'intl_wire_beneficiary_name': self.intl_wire_beneficiary_name or '',
            'intl_wire_bank_name': self.intl_wire_bank_name or '',
            'intl_wire_swift': self.intl_wire_swift or '',
            'intl_wire_account': self.intl_wire_account or '',
            'intl_wire_account_type': self.intl_wire_account_type or '',
            'intl_wire_country': self.intl_wire_country or '',
            'intl_wire_instructions': self.intl_wire_instructions or '',
            'use_environment_variables': self.use_environment_variables,
            'is_active': self.is_active,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @staticmethod
    def empty_config_api_dict(organization_id=None):
        """Diccionario para GET /api/admin/payments/config cuando aún no hay fila activa (formulario vacío)."""
        oid = None
        if organization_id is not None:
            try:
                oid = int(organization_id)
            except (TypeError, ValueError):
                oid = None
        return {
            'id': None,
            'organization_id': oid,
            'stripe_publishable_key': '',
            'stripe_secret_key': '',
            'stripe_webhook_secret': '',
            'paypal_client_id': '',
            'paypal_client_secret': '',
            'paypal_mode': 'sandbox',
            'paypal_return_url': '',
            'paypal_cancel_url': '',
            'banco_general_merchant_id': '',
            'banco_general_api_url': 'https://api.cybersource.com',
            'banco_general_beneficiary_name': '',
            'banco_general_bank_name': '',
            'banco_general_account_number': '',
            'banco_general_account_type': '',
            'yappy_merchant_id': '',
            'yappy_api_url': 'https://api.yappy.im',
            'yappy_directory_name': '',
            'yappy_qr_image_path': '',
            'yappy_business_name': '',
            'yappy_merchant_phone': '',
            'yappy_manual_enabled': False,
            'yappy_manual_instructions': '',
            'yappy_manual_admin_emails': '',
            'yappy_display_name': '',
            'yappy_phone_or_identifier': '',
            'yappy_instructions': '',
            'yappy_requires_receipt': True,
            'yappy_admin_validation_required': True,
            'intl_wire_enabled': True,
            'intl_wire_beneficiary_name': '',
            'intl_wire_bank_name': '',
            'intl_wire_swift': '',
            'intl_wire_account': '',
            'intl_wire_account_type': '',
            'intl_wire_country': '',
            'intl_wire_instructions': '',
            'use_environment_variables': True,
            'is_active': False,
            'updated_at': None,
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

    def get_paypal_mode(self):
        """sandbox | live: si ``use_environment_variables``, prioriza ``PAYPAL_MODE`` del entorno."""
        raw = None
        if self.use_environment_variables:
            raw = os.getenv('PAYPAL_MODE')
        if not raw:
            raw = self.paypal_mode or 'sandbox'
        raw = (raw or 'sandbox').strip().lower()
        return 'live' if raw == 'live' else 'sandbox'

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


class OrganizationPaymentMethod(db.Model):
    """Métodos de pago habilitados y su UX por organización (checkout dinámico)."""

    __tablename__ = 'organization_payment_methods'
    __table_args__ = (
        db.UniqueConstraint('organization_id', 'method_key', name='uq_org_payment_method'),
    )

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    method_key = db.Column(db.String(40), nullable=False)
    label = db.Column(db.String(120), nullable=False, default='')
    enabled = db.Column(db.Boolean, nullable=False, default=False)
    display_order = db.Column(db.Integer, nullable=False, default=100)
    requires_receipt = db.Column(db.Boolean, nullable=False, default=False)
    requires_admin_approval = db.Column(db.Boolean, nullable=False, default=False)
    auto_confirm = db.Column(db.Boolean, nullable=False, default=False)
    instructions_html = db.Column(db.Text, nullable=True)
    is_international = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'method_key': self.method_key,
            'label': self.label,
            'enabled': bool(self.enabled),
            'display_order': int(self.display_order or 0),
            'requires_receipt': bool(self.requires_receipt),
            'requires_admin_approval': bool(self.requires_admin_approval),
            'auto_confirm': bool(self.auto_confirm),
            'instructions_html': self.instructions_html or '',
            'is_international': bool(self.is_international),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

