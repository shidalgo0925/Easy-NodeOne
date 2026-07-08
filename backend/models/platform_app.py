"""Runtime de aplicaciones de plataforma por organización (Etapa 5)."""

from datetime import datetime

from nodeone.core.db import db

APP_RUNTIME_LEGACY = 'legacy'
APP_RUNTIME_MIGRATING = 'en_migracion'
APP_RUNTIME_PLATFORM = 'plataforma'

APP_RUNTIME_VALUES = frozenset(
    {APP_RUNTIME_LEGACY, APP_RUNTIME_MIGRATING, APP_RUNTIME_PLATFORM}
)


class PlatformOrgAppRuntime(db.Model):
    """Estado de integración org × app (no sustituye saas_org_module)."""

    __tablename__ = 'platform_org_app_runtime'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey('saas_organization.id', ondelete='CASCADE'), nullable=False
    )
    app_id = db.Column(db.String(64), nullable=False)
    runtime = db.Column(db.String(32), nullable=False, default=APP_RUNTIME_LEGACY)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('organization_id', 'app_id', name='uq_platform_org_app_runtime'),
    )
