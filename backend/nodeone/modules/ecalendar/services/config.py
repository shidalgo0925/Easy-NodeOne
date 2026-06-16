"""Configuración ECalendar (desde BD admin EN1)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ECalendarConfig:
    enabled: bool
    timezone: str
    slot_minutes: int
    lead_hours: int
    horizon_days: int
    business_start: str
    business_end: str
    title_prefix: str
    allowed_origins: tuple[str, ...]
    products_json: str
    google_client_id: str
    google_client_secret: str
    google_refresh_token: str
    google_calendar_id: str

    @property
    def google_configured(self) -> bool:
        return bool(
            self.google_client_id
            and self.google_client_secret
            and self.google_refresh_token
            and self.google_calendar_id
        )


def _split_origins(raw: str) -> tuple[str, ...]:
    return tuple(x.strip() for x in (raw or '').split(',') if x.strip())


def load_ecalendar_config(organization_id: int | None = None) -> ECalendarConfig:
    from nodeone.modules.ecalendar.services.settings_store import load_ecalendar_config_for_org

    return load_ecalendar_config_for_org(organization_id)
