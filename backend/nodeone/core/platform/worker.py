"""Worker de plataforma — despacho outbox y cola sync offline (Etapa 8)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformWorkerResult:
    events_dispatched: int
    events_retried: int
    sync_processed: int

    def to_dict(self) -> dict[str, int]:
        return {
            'events_dispatched': int(self.events_dispatched),
            'events_retried': int(self.events_retried),
            'sync_processed': int(self.sync_processed),
        }


def run_platform_worker_cycle(
    *,
    event_limit: int = 100,
    sync_limit: int = 50,
    organization_id: int | None = None,
    retry_failed: bool = True,
    process_sync: bool = True,
) -> PlatformWorkerResult:
    """
    Un ciclo del worker: reintenta eventos failed, despacha pendientes y procesa cola offline.

    Pensado para cron/systemd o ``NODEONE_EVENT_BUS_SYNC=0`` en Gunicorn.
    """
    from nodeone.core.platform.events import dispatch_pending_events
    from nodeone.core.platform.events import retry_failed_events as retry_failed_events_fn

    retried = 0
    if retry_failed:
        retried = retry_failed_events_fn(limit=int(event_limit), organization_id=organization_id)

    dispatched = dispatch_pending_events(limit=int(event_limit), organization_id=organization_id)

    sync_processed = 0
    if process_sync:
        from nodeone.modules.eposone.sync_handlers import process_eposone_sync_queue

        sync_processed = process_eposone_sync_queue(
            organization_id=organization_id,
            limit=int(sync_limit),
        )

    return PlatformWorkerResult(
        events_dispatched=int(dispatched),
        events_retried=int(retried),
        sync_processed=int(sync_processed),
    )
