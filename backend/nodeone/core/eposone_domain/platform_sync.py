"""Sprint 7 — Sync Modo Plataforma (política sobre motor existente).

No reescribe ``nodeone/core/sync/``. Solo:
- permite cola/pull en ``operating_mode=platform``;
- rechaza en Modo Local;
- usa ``device_id`` como ``client_id`` cuando hay dispositivo;
- respeta ``Device.sync_enabled``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from nodeone.core.eposone_domain.first_start import MODE_LOCAL, MODE_PLATFORM, MODE_UNINITIALIZED
from nodeone.core.eposone_domain.models import Device

OperatingMode = Literal['uninitialized', 'local', 'platform']


class PlatformSyncError(ValueError):
    """Rechazo de sync por política de modo / dispositivo."""


@dataclass(frozen=True)
class SyncClientContext:
    """Contexto del cliente POS que intenta sincronizar."""

    operating_mode: OperatingMode
    organization_id: str | None = None
    device_id: str | None = None
    device: Device | None = None

    @property
    def client_id(self) -> str:
        did = (self.device_id or '').strip()
        if did:
            return did
        if self.device is not None:
            return self.device.id
        return 'default'


def assert_platform_sync_allowed(ctx: SyncClientContext) -> None:
    """§ 6.9 / ADR-003: sync EN1 solo en Modo Plataforma."""
    mode = (ctx.operating_mode or MODE_UNINITIALIZED).strip().lower()
    if mode == MODE_LOCAL:
        raise PlatformSyncError('sync_disabled_local_mode')
    if mode == MODE_UNINITIALIZED:
        raise PlatformSyncError('sync_requires_platform_mode')
    if mode != MODE_PLATFORM:
        raise PlatformSyncError(f'sync_invalid_mode:{mode}')
    if ctx.device is not None and not ctx.device.sync_enabled:
        raise PlatformSyncError('sync_disabled_for_device')
    if ctx.device is not None and ctx.device.status != 'active':
        raise PlatformSyncError('device_inactive')


def resolve_sync_context(
    *,
    operating_mode: str | None,
    organization_id: str | int | None = None,
    device_id: str | None = None,
    devices: Any | None = None,
    default_mode: OperatingMode = MODE_PLATFORM,
) -> SyncClientContext:
    """Resuelve contexto desde headers/body del cliente o defaults EN1 web.

    EN1 web (sesión tenant) es intrínsecamente Plataforma → ``default_mode=platform``.
    """
    raw = (operating_mode or '').strip().lower()
    if not raw:
        mode: OperatingMode = default_mode
    elif raw in (MODE_LOCAL, MODE_PLATFORM, MODE_UNINITIALIZED):
        mode = raw  # type: ignore[assignment]
    else:
        raise PlatformSyncError(f'sync_invalid_mode:{raw}')

    did = (device_id or '').strip() or None
    device = None
    if did and devices is not None:
        device = devices.get(did)

    oid = str(organization_id).strip() if organization_id is not None else None
    return SyncClientContext(
        operating_mode=mode,
        organization_id=oid,
        device_id=did,
        device=device,
    )


class PlatformSyncBridge:
    """Puente: política V4 + ``SyncOperationService`` / pull de eventos.

    El motor de cola e handlers EPosOne permanecen; este bridge solo enmascara.
    """

    def __init__(
        self,
        *,
        devices: Any | None = None,
        default_mode: OperatingMode = MODE_PLATFORM,
    ) -> None:
        self._devices = devices
        self._default_mode = default_mode

    def context_from_request(
        self,
        *,
        operating_mode: str | None = None,
        organization_id: str | int | None = None,
        device_id: str | None = None,
        client_id: str | None = None,
    ) -> SyncClientContext:
        # client_id legacy = device_id cuando el APK aún no manda device_id
        did = (device_id or client_id or '').strip() or None
        return resolve_sync_context(
            operating_mode=operating_mode,
            organization_id=organization_id,
            device_id=did,
            devices=self._devices,
            default_mode=self._default_mode,
        )

    def enqueue(
        self,
        organization_id: int,
        *,
        idempotency_key: str,
        operation_type: str,
        payload: dict[str, Any] | None = None,
        operating_mode: str | None = None,
        device_id: str | None = None,
        client_id: str | None = None,
        entity_type: str | None = None,
        entity_ref: str | None = None,
        base_version: int | None = None,
    ):
        from nodeone.core.sync.queue import SyncOperationService

        ctx = self.context_from_request(
            operating_mode=operating_mode,
            organization_id=organization_id,
            device_id=device_id,
            client_id=client_id,
        )
        assert_platform_sync_allowed(ctx)
        return SyncOperationService.enqueue(
            int(organization_id),
            idempotency_key=idempotency_key,
            operation_type=operation_type,
            payload=payload or {},
            client_id=ctx.client_id,
            entity_type=entity_type,
            entity_ref=entity_ref,
            base_version=base_version,
        )

    def process_pending(
        self, *, organization_id: int | None = None, limit: int = 50
    ) -> int:
        """Procesa cola — solo tiene sentido en servidores/plataformas EN1."""
        from nodeone.modules.eposone.sync_handlers import process_eposone_sync_queue

        return process_eposone_sync_queue(organization_id=organization_id, limit=limit)

    def pull_events(
        self,
        organization_id: int,
        *,
        since_id: int = 0,
        limit: int = 100,
        event_type_prefix: str | None = None,
        operating_mode: str | None = None,
        device_id: str | None = None,
        client_id: str | None = None,
    ):
        from nodeone.core.sync.incremental import IncrementalSyncService

        ctx = self.context_from_request(
            operating_mode=operating_mode,
            organization_id=organization_id,
            device_id=device_id,
            client_id=client_id,
        )
        assert_platform_sync_allowed(ctx)
        return IncrementalSyncService.fetch_events(
            int(organization_id),
            since_id=since_id,
            limit=limit,
            event_type_prefix=event_type_prefix,
        )

    def touch_device_seen(self, device_id: str, *, app_version: str | None = None) -> Device | None:
        """Opcional: heartbeat al sincronizar."""
        if self._devices is None or not device_id:
            return None
        from nodeone.core.eposone_domain.devices import DeviceRegistry

        try:
            return DeviceRegistry(self._devices).heartbeat(device_id, app_version=app_version)
        except Exception:
            return None


def bridge_for_api_org(organization_id: int) -> PlatformSyncBridge:
    """Bridge EN1 Plataforma con dispositivos de la org."""
    from nodeone.core.eposone_domain.api import ApiDeviceRepository

    return PlatformSyncBridge(
        devices=ApiDeviceRepository(int(organization_id)),
        default_mode=MODE_PLATFORM,
    )
