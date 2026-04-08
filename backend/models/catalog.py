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

from .payments import MembershipDiscount

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
        # Import lazy para evitar NameError al separar modelos por archivos.
        from .events import Discount

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
        # Import lazy para evitar NameError al separar modelos por archivos.
        from .events import DiscountCode

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
        from .events import DiscountCode

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
    # CONSULTIVO = primera reunión → propuesta → pago. AGENDABLE = calendario → pago → confirmado.
    service_type = db.Column(db.String(20), nullable=False, default='AGENDABLE')  # CONSULTIVO | AGENDABLE
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
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, default=1
    )
    default_tax_id = db.Column(db.Integer, db.ForeignKey('taxes.id', ondelete='SET NULL'), nullable=True, index=True)

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
            'deposit_percentage': float(self.deposit_percentage) if self.deposit_percentage else None,
            'service_type': getattr(self, 'service_type', 'AGENDABLE') or 'AGENDABLE',
            'organization_id': int(getattr(self, 'organization_id', None) or 1),
            'default_tax_id': int(getattr(self, 'default_tax_id', None) or 0) or None,
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
