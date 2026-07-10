"""Sprint 6 — Dispositivos POS (registro, perfil, vínculo empresa/caja).

Capa de casos de uso sobre ``DeviceRepository``. No cablea sync (Sprint 7).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Literal

from nodeone.core.eposone_domain.models import Device

DeviceProfile = Literal['fixed', 'handheld']

PROFILES: frozenset[str] = frozenset({'fixed', 'handheld'})


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def new_device_id() -> str:
    """UUID estable del dispositivo (ADR / contrato Sprint 2)."""
    return str(uuid.uuid4())


@dataclass(frozen=True)
class RegisterDeviceInput:
    """Alta o re-registro de un terminal."""

    device_id: str | None = None  # None → genera UUID
    profile: DeviceProfile = 'fixed'
    name: str | None = None
    business_id: str | None = None
    branch_id: str | None = None
    register_id: str | None = None
    app_version: str | None = None
    platform: str | None = None
    device_model: str | None = None
    sync_enabled: bool = True


class DeviceRegistryError(ValueError):
    pass


class DeviceRegistry:
    """Registro lógico de dispositivos POS."""

    def __init__(self, devices: Any) -> None:
        self._devices = devices

    def register(self, data: RegisterDeviceInput) -> Device:
        profile = (data.profile or 'fixed').strip().lower()
        if profile not in PROFILES:
            raise DeviceRegistryError(f'invalid_profile:{profile}')

        device_id = (data.device_id or '').strip() or new_device_id()
        existing = self._devices.get(device_id)
        now = _utcnow()

        if existing is not None:
            saved = replace(
                existing,
                profile=profile,  # type: ignore[arg-type]
                name=(data.name if data.name is not None else existing.name),
                business_id=(
                    data.business_id if data.business_id is not None else existing.business_id
                ),
                branch_id=data.branch_id if data.branch_id is not None else existing.branch_id,
                register_id=(
                    data.register_id if data.register_id is not None else existing.register_id
                ),
                app_version=(
                    data.app_version if data.app_version is not None else existing.app_version
                ),
                platform=data.platform if data.platform is not None else existing.platform,
                device_model=(
                    data.device_model if data.device_model is not None else existing.device_model
                ),
                sync_enabled=bool(data.sync_enabled),
                status='active',
                last_seen_at=now,
            )
            return self._devices.upsert(saved)

        device = Device(
            id=device_id,
            profile=profile,  # type: ignore[arg-type]
            name=(data.name or '').strip() or None,
            business_id=(data.business_id or '').strip() or None,
            branch_id=(data.branch_id or '').strip() or None,
            register_id=(data.register_id or '').strip() or None,
            app_version=(data.app_version or '').strip() or None,
            platform=(data.platform or '').strip() or None,
            device_model=(data.device_model or '').strip() or None,
            status='active',
            sync_enabled=bool(data.sync_enabled),
            last_seen_at=now,
            created_at=now,
        )
        return self._devices.upsert(device)

    def assign(
        self,
        device_id: str,
        *,
        business_id: str | None = None,
        branch_id: str | None = None,
        register_id: str | None = None,
    ) -> Device:
        d = self._devices.get(device_id)
        if d is None:
            raise DeviceRegistryError('device_not_found')
        saved = replace(
            d,
            business_id=business_id if business_id is not None else d.business_id,
            branch_id=branch_id if branch_id is not None else d.branch_id,
            register_id=register_id if register_id is not None else d.register_id,
        )
        return self._devices.upsert(saved)

    def set_sync_enabled(self, device_id: str, enabled: bool) -> Device:
        d = self._devices.get(device_id)
        if d is None:
            raise DeviceRegistryError('device_not_found')
        return self._devices.upsert(replace(d, sync_enabled=bool(enabled)))

    def deactivate(self, device_id: str) -> Device:
        d = self._devices.get(device_id)
        if d is None:
            raise DeviceRegistryError('device_not_found')
        return self._devices.upsert(replace(d, status='inactive', sync_enabled=False))

    def heartbeat(
        self, device_id: str, *, app_version: str | None = None
    ) -> Device:
        updated = self._devices.heartbeat(
            device_id, last_seen_at=_utcnow(), app_version=app_version
        )
        if updated is None:
            raise DeviceRegistryError('device_not_found')
        return updated

    def list_active(self, *, limit: int = 100) -> list[Device]:
        return self._devices.list(active_only=True, limit=limit)

    def get(self, device_id: str) -> Device | None:
        return self._devices.get(device_id)


def registry_from_bundle(bundle: Any) -> DeviceRegistry:
    return DeviceRegistry(bundle.devices)
