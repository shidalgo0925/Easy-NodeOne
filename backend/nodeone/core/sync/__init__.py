"""Sincronización offline — Etapa 13."""

from nodeone.core.sync.conflicts import SyncConflictError, detect_version_conflict, resolve_conflict
from nodeone.core.sync.constants import (
    CONFLICT_STRATEGY_MANUAL,
    CONFLICT_STRATEGY_SERVER_WINS,
    SYNC_DOMAIN_EVENTS,
)
from nodeone.core.sync.cursor import SyncCursorDTO, SyncCursorService
from nodeone.core.sync.incremental import IncrementalSyncService, SyncEventDTO
from nodeone.core.sync.queue import SyncOperationDTO, SyncOperationService
from nodeone.core.sync.retry import compute_next_retry_at, is_ready_for_retry, max_event_retries

__all__ = [
    'CONFLICT_STRATEGY_MANUAL',
    'CONFLICT_STRATEGY_SERVER_WINS',
    'IncrementalSyncService',
    'SyncConflictError',
    'SyncCursorDTO',
    'SyncCursorService',
    'SyncEventDTO',
    'SyncOperationDTO',
    'SyncOperationService',
    'SYNC_DOMAIN_EVENTS',
    'compute_next_retry_at',
    'detect_version_conflict',
    'is_ready_for_retry',
    'max_event_retries',
    'resolve_conflict',
]
