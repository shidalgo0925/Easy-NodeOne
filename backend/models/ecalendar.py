"""Configuración ECalendar (agenda pública Google Calendar) por tenant."""

from __future__ import annotations

from datetime import datetime

from nodeone.core.db import db


class ECalendarSettings(db.Model):
    __tablename__ = 'ecalendar_settings'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('saas_organization.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        index=True,
    )
    enabled = db.Column(db.Boolean, nullable=False, default=False)
    use_for_public_agenda = db.Column(db.Boolean, nullable=False, default=True)

    google_client_id = db.Column(db.String(256), nullable=False, default='')
    google_client_secret = db.Column(db.String(512), nullable=False, default='')
    google_refresh_token = db.Column(db.String(512), nullable=False, default='')
    google_calendar_id = db.Column(db.String(256), nullable=False, default='primary')
    google_account_email = db.Column(db.String(256), nullable=False, default='')

    timezone = db.Column(db.String(64), nullable=False, default='America/Panama')
    slot_minutes = db.Column(db.Integer, nullable=False, default=30)
    lead_hours = db.Column(db.Integer, nullable=False, default=4)
    horizon_days = db.Column(db.Integer, nullable=False, default=30)
    business_start = db.Column(db.String(8), nullable=False, default='09:00')
    business_end = db.Column(db.String(8), nullable=False, default='17:00')
    title_prefix = db.Column(db.String(64), nullable=False, default='')
    allowed_origins = db.Column(db.Text, nullable=False, default='')
    products_json = db.Column(db.Text, nullable=False, default='')

    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get_for_organization(organization_id: int) -> ECalendarSettings | None:
        oid = int(organization_id)
        return (
            ECalendarSettings.query.filter_by(organization_id=oid, is_active=True)
            .order_by(ECalendarSettings.id.asc())
            .first()
        )

    @staticmethod
    def get_or_create_for_organization(organization_id: int) -> ECalendarSettings:
        row = ECalendarSettings.get_for_organization(organization_id)
        if row is not None:
            return row
        row = ECalendarSettings(organization_id=int(organization_id))
        db.session.add(row)
        return row

    @staticmethod
    def get_public_settings() -> ECalendarSettings | None:
        flagged = (
            ECalendarSettings.query.filter_by(
                enabled=True,
                is_active=True,
                use_for_public_agenda=True,
            )
            .order_by(ECalendarSettings.id.asc())
            .first()
        )
        if flagged is not None:
            return flagged
        return (
            ECalendarSettings.query.filter_by(enabled=True, is_active=True)
            .order_by(ECalendarSettings.id.asc())
            .first()
        )

    def to_dict(self, *, include_secret_flags: bool = True) -> dict:
        out = {
            'organization_id': self.organization_id,
            'enabled': bool(self.enabled),
            'use_for_public_agenda': bool(self.use_for_public_agenda),
            'google_client_id': (self.google_client_id or '').strip(),
            'google_calendar_id': (self.google_calendar_id or 'primary').strip() or 'primary',
            'google_account_email': (self.google_account_email or '').strip(),
            'timezone': (self.timezone or 'America/Panama').strip() or 'America/Panama',
            'slot_minutes': int(self.slot_minutes or 30),
            'lead_hours': int(self.lead_hours or 4),
            'horizon_days': int(self.horizon_days or 30),
            'business_start': (self.business_start or '09:00').strip() or '09:00',
            'business_end': (self.business_end or '17:00').strip() or '17:00',
            'title_prefix': (self.title_prefix or '').strip(),
            'allowed_origins': (self.allowed_origins or '').strip(),
            'products_json': (self.products_json or '').strip(),
            'configured': self.google_configured,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_secret_flags:
            out['has_google_client_secret'] = bool((self.google_client_secret or '').strip())
            out['has_google_refresh_token'] = bool((self.google_refresh_token or '').strip())
        return out

    @property
    def google_configured(self) -> bool:
        return bool(
            (self.google_client_id or '').strip()
            and (self.google_client_secret or '').strip()
            and (self.google_refresh_token or '').strip()
            and (self.google_calendar_id or '').strip()
        )
