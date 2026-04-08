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

class OrganizationSettings(db.Model):
    """Identidad visual por cliente (design tokens). Preferir una fila por organization_id (sesión)."""
    __tablename__ = 'organization_settings'
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=True, unique=True
    )
    primary_color = db.Column(db.String(7), nullable=False, default='#2563EB')
    primary_color_dark = db.Column(db.String(7), nullable=False, default='#1E3A8A')
    accent_color = db.Column(db.String(7), nullable=False, default='#06B6D4')
    logo_url = db.Column(db.String(500))   # ruta relativa o vacío = usar get_system_logo()
    favicon_url = db.Column(db.String(500))  # ruta relativa o vacío = usar logo
    preset = db.Column(db.String(50), default='azul')  # azul | verde | rojo | custom
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get_settings():
        """Compatibilidad: primera fila (legado sin organization_id o id 1)."""
        s = OrganizationSettings.query.first()
        if s is None:
            s = OrganizationSettings()
            db.session.add(s)
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
        return s

    @staticmethod
    def get_settings_for_session():
        """
        Identidad para la organización activa (sesión). Usar en inject_theme, branding /admin, navbar.
        """
        from utils.organization import default_organization_id, get_current_organization_id

        oid = default_organization_id()
        try:
            if has_request_context() and getattr(current_user, 'is_authenticated', False):
                gco = get_current_organization_id()
                if gco is not None:
                    oid = int(gco)
        except Exception:
            pass
        row = OrganizationSettings.query.filter_by(organization_id=oid).first()
        if row is not None:
            return row
        legacy = OrganizationSettings.query.filter(OrganizationSettings.organization_id.is_(None)).first()
        if legacy is not None and int(oid) == int(default_organization_id()):
            return legacy
        base = legacy or OrganizationSettings.query.first()
        src = base.to_dict() if base else {}
        n = OrganizationSettings(
            organization_id=oid,
            primary_color=src.get('primary_color') or '#2563EB',
            primary_color_dark=src.get('primary_color_dark') or '#1E3A8A',
            accent_color=src.get('accent_color') or '#06B6D4',
            logo_url=src.get('logo_url') or '',
            favicon_url=src.get('favicon_url') or '',
            preset=src.get('preset') or 'azul',
        )
        db.session.add(n)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            return OrganizationSettings.get_settings()
        return n

    def to_dict(self):
        return {
            'primary_color': self.primary_color or '#2563EB',
            'primary_color_dark': self.primary_color_dark or '#1E3A8A',
            'accent_color': self.accent_color or '#06B6D4',
            'logo_url': self.logo_url or '',
            'favicon_url': self.favicon_url or '',
            'preset': self.preset or 'azul',
            'organization_id': getattr(self, 'organization_id', None),
        }


class SaasOrganization(db.Model):
    __tablename__ = 'saas_organization'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    subdomain = db.Column(db.String(128), unique=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class SaasModule(db.Model):
    __tablename__ = 'saas_module'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    is_core = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SaasOrgModule(db.Model):
    __tablename__ = 'saas_org_module'
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False
    )
    module_id = db.Column(db.Integer, db.ForeignKey('saas_module.id', ondelete='CASCADE'), nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('organization_id', 'module_id', name='uq_saas_org_module'),)


class TenantCrmContact(db.Model):
    """Contactos CRM por organización (sidebar Clientes → Contactos)."""
    __tablename__ = 'tenant_crm_contact'
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, default=1
    )
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    company = db.Column(db.String(200))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SaasModuleDependency(db.Model):
    __tablename__ = 'saas_module_dependency'
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('saas_module.id', ondelete='CASCADE'), nullable=False)
    depends_on_module_id = db.Column(db.Integer, db.ForeignKey('saas_module.id', ondelete='CASCADE'), nullable=False)
    __table_args__ = (
        db.UniqueConstraint('module_id', 'depends_on_module_id', name='uq_saas_mod_dep'),
    )

