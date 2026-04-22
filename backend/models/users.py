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

from .associations import user_role_table, role_permission_table

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
    is_salesperson = db.Column(db.Boolean, default=False, nullable=False)  # Vendedor en cotizaciones (miembros de la org)

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
    
    # Obligar cambio de contraseña en primer login (seed admin)
    must_change_password = db.Column(db.Boolean, default=False, nullable=False)
    
    # Email marketing: subscribed, unsubscribed, bounced
    email_marketing_status = db.Column(db.String(20), default='subscribed', nullable=False)

    # Multi-tenant (tabla saas_organization en BD)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id'), nullable=False, default=1
    )
    # Última empresa elegida en selector post-login (admin multi-tenant)
    last_selected_organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='SET NULL'), nullable=True
    )
    
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
        # Import lazy para evitar NameError/ciclos al cargar modelos separados.
        from .benefits import Membership
        from .payments import Subscription

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

    def has_permission(self, perm_code):
        """
        Comprueba si el usuario tiene el permiso (por RBAC o compat is_admin).
        Regla: backend valida por permiso, nunca por rol.
        """
        if not perm_code:
            return False
        # Compatibilidad: si tiene is_admin y aún no tiene roles RBAC, se considera con acceso admin (como AD)
        if getattr(self, 'is_admin', False):
            ur = db.session.execute(
                sql_text('SELECT 1 FROM user_role WHERE user_id = :uid LIMIT 1'),
                {'uid': self.id}
            ).fetchone()
            if not ur:
                return True  # is_admin sin roles RBAC → tratar como todo permitido
        # RBAC: permisos vía roles del usuario
        r = db.session.execute(
            sql_text('''
                SELECT 1 FROM user_role ur
                JOIN role_permission rp ON rp.role_id = ur.role_id
                JOIN permission p ON p.id = rp.permission_id
                WHERE ur.user_id = :uid AND p.code = :code LIMIT 1
            '''),
            {'uid': self.id, 'code': perm_code}
        ).fetchone()
        return r is not None

    # RBAC: roles asignados (véase asignación después de class Role)


class Role(db.Model):
    """Rol del sistema (SA, AD, ST, TE, MI, IN)."""
    __tablename__ = 'role'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    permissions = db.relationship(
        'Permission', secondary=role_permission_table,
        backref=db.backref('roles', lazy='dynamic'), lazy='dynamic'
    )


class Permission(db.Model):
    """Permiso granular (ej. users.create, payments.manage)."""
    __tablename__ = 'permission'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# RBAC: relación User.roles (definida aquí para evitar ambigüedad por assigned_by_id en user_role)
User.roles = db.relationship(
    Role, secondary=user_role_table, backref='users', lazy='dynamic',
    primaryjoin=(User.id == user_role_table.c.user_id),
    secondaryjoin=(user_role_table.c.role_id == Role.id),
)


class SocialAuth(db.Model):
    """Vinculación de usuario con proveedor OAuth (Google, Facebook, LinkedIn)."""
    __tablename__ = 'social_auth'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    provider = db.Column(db.String(50), nullable=False)  # google, facebook, linkedin
    provider_user_id = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('provider', 'provider_user_id', name='uq_social_provider_user'),)


class UserOrganization(db.Model):
    """Miembro de una empresa (varias organizaciones por usuario; email único global en User)."""
    __tablename__ = 'user_organization'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')
    status = db.Column(db.String(20), nullable=False, default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship(
        'User',
        backref=db.backref('user_org_links', lazy='dynamic', cascade='all, delete-orphan'),
    )
    __table_args__ = (
        db.UniqueConstraint('user_id', 'organization_id', name='uq_user_organization_membership'),
    )


class UserSettings(db.Model):
    """Preferencias de configuración por usuario (notificaciones, privacidad, idioma, apariencia)."""
    __tablename__ = 'user_settings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, unique=True)
    preferences = db.Column(db.Text)  # JSON
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('user_settings', uselist=False))

