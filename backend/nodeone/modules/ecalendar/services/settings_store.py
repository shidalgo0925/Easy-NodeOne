"""Persistencia y resolución de configuración ECalendar desde BD."""

from __future__ import annotations

from nodeone.core.db import db
from nodeone.modules.ecalendar.services.config import ECalendarConfig, _split_origins


def ensure_ecalendar_settings_table() -> None:
    from models.ecalendar import ECalendarSettings

    try:
        ECalendarSettings.__table__.create(db.engine, checkfirst=True)
    except Exception:
        pass


def row_to_config(row) -> ECalendarConfig:
    return ECalendarConfig(
        enabled=bool(getattr(row, 'enabled', False)),
        timezone=(row.timezone or 'America/Panama').strip() or 'America/Panama',
        slot_minutes=max(15, int(row.slot_minutes or 30)),
        lead_hours=max(0, int(row.lead_hours or 4)),
        horizon_days=max(1, int(row.horizon_days or 30)),
        business_start=(row.business_start or '09:00').strip() or '09:00',
        business_end=(row.business_end or '17:00').strip() or '17:00',
        title_prefix=(row.title_prefix or '').strip(),
        allowed_origins=_split_origins(row.allowed_origins or ''),
        products_json=(row.products_json or '').strip(),
        google_client_id=(row.google_client_id or '').strip(),
        google_client_secret=(row.google_client_secret or '').strip(),
        google_refresh_token=(row.google_refresh_token or '').strip(),
        google_calendar_id=(row.google_calendar_id or 'primary').strip() or 'primary',
    )


def empty_config() -> ECalendarConfig:
    return ECalendarConfig(
        enabled=False,
        timezone='America/Panama',
        slot_minutes=30,
        lead_hours=4,
        horizon_days=30,
        business_start='09:00',
        business_end='17:00',
        title_prefix='',
        allowed_origins=(),
        products_json='',
        google_client_id='',
        google_client_secret='',
        google_refresh_token='',
        google_calendar_id='primary',
    )


def load_ecalendar_config_for_org(organization_id: int | None = None) -> ECalendarConfig:
    ensure_ecalendar_settings_table()
    from models.ecalendar import ECalendarSettings

    if organization_id is not None:
        row = ECalendarSettings.get_for_organization(int(organization_id))
        return row_to_config(row) if row is not None else empty_config()

    row = ECalendarSettings.get_public_settings()
    return row_to_config(row) if row is not None else empty_config()
