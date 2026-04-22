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
        if self.end_date is None:
            return bool(self.is_active)
        return self.is_active and datetime.utcnow() <= self.end_date

class Benefit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    membership_type = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    icon = db.Column(db.String(80))   # e.g. "fas fa-gift", "fas fa-star"
    color = db.Column(db.String(20))  # Bootstrap: primary, success, info, warning, danger
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, default=1
    )

class MembershipPlan(db.Model):
    """Planes de membresía configurables (sustituye lista fija basic/pro/premium/...)."""
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(50), nullable=False)  # basic, pro, premium, ... (único por org en lógica admin)
    name = db.Column(db.String(100), nullable=False)  # Nombre para mostrar
    description = db.Column(db.Text)
    price_yearly = db.Column(db.Float, default=0.0)
    price_monthly = db.Column(db.Float, default=0.0)
    display_order = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=0)  # Jerarquía: 0=menor, mayor=nivel superior (para herencia de servicios)
    badge = db.Column(db.String(100))  # Ej: "Incluido con la membresía gratuita"
    color = db.Column(db.String(50), default='bg-secondary')  # Clase Bootstrap para badges
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False, default=1
    )

    def to_dict(self):
        return {
            'id': self.id, 'slug': self.slug, 'name': self.name, 'description': self.description,
            'price_yearly': self.price_yearly, 'price_monthly': self.price_monthly,
            'display_order': self.display_order, 'level': self.level, 'badge': self.badge,
            'color': self.color, 'is_active': self.is_active,
            'organization_id': int(getattr(self, 'organization_id', None) or 1),
        }

    @staticmethod
    def get_active_ordered(organization_id=None):
        """Lista de planes activos ordenados por display_order, luego level (por organización)."""
        from app import tenant_data_organization_id  # noqa: WPS433 — evita ciclo import

        oid = int(organization_id) if organization_id is not None else tenant_data_organization_id()
        return MembershipPlan.query.filter_by(is_active=True, organization_id=oid).order_by(
            MembershipPlan.display_order, MembershipPlan.level
        ).all()

    @staticmethod
    def get_hierarchy(organization_id=None):
        """Dict slug -> level para compatibilidad con lógica de jerarquía."""
        from app import tenant_data_organization_id  # noqa: WPS433

        oid = int(organization_id) if organization_id is not None else tenant_data_organization_id()
        out = {
            p.slug: p.level
            for p in MembershipPlan.query.filter_by(is_active=True, organization_id=oid).order_by(MembershipPlan.level).all()
        }
        # ``basic`` no es un plan de catálogo: es “sin membresía paga” / mínimo lógico para servicios y descuentos.
        out.setdefault('basic', 0)
        return out

    @staticmethod
    def get_plans_info(organization_id=None):
        """Dict slug -> {name, price, badge, color} para templates (compat PLANS_INFO)."""
        out = {}
        for p in MembershipPlan.get_active_ordered(organization_id=organization_id):
            price_str = f'${p.price_yearly:.0f}/año' if p.price_yearly else '$0'
            if p.price_monthly and p.price_monthly > 0:
                price_str += f' (${p.price_monthly:.0f}/mes)'
            out[p.slug] = {
                'name': p.name.upper(),
                'price': price_str,
                'badge': p.badge or '',
                'color': p.color or 'bg-secondary',
            }
        return out
