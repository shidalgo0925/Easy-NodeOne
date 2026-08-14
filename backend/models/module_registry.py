"""ADR-038 F1 — Module Registry (aditivo; no reemplaza saas_module / saas_org_module)."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class ModuleDefinition(db.Model):
    """Catálogo formal de módulos EN1 (toggle/domain gate). module_key ≠ product_code ≠ app_id."""

    __tablename__ = 'module_definition'

    id = db.Column(db.Integer, primary_key=True)
    module_key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    version = db.Column(db.String(32), nullable=False, default='1')
    # active | draft | deprecated
    status = db.Column(db.String(32), nullable=False, default='active', index=True)
    # JSON list of module_key dependencies, e.g. '["communications"]'
    dependencies_json = db.Column(db.Text, nullable=True)
    configurable_per_org = db.Column(db.Boolean, nullable=False, default=True)
    is_core = db.Column(db.Boolean, nullable=False, default=False)
    # F1: identity map to legacy saas_module.code (usually == module_key)
    saas_code = db.Column(db.String(64), nullable=True, index=True)
    nav_metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class OrganizationModule(db.Model):
    """Estado enable/disable por organización. Deshabilitar ≠ DELETE."""

    __tablename__ = 'organization_module'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    module_key = db.Column(db.String(64), nullable=False, index=True)
    enabled = db.Column(db.Boolean, nullable=False, default=False)
    enabled_at = db.Column(db.DateTime, nullable=True)
    disabled_at = db.Column(db.DateTime, nullable=True)
    config_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'module_key', name='uq_organization_module_org_key'),
    )
