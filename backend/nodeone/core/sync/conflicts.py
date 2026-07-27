"""Detección y resolución de conflictos — Etapa 13."""

from __future__ import annotations

from nodeone.core.sync.constants import (
    CONFLICT_STRATEGY_CLIENT_WINS,
    CONFLICT_STRATEGY_MANUAL,
    CONFLICT_STRATEGY_SERVER_WINS,
)


class SyncConflictError(Exception):
    def __init__(self, reason: str, *, server_version: int | None = None):
        super().__init__(reason)
        self.reason = reason
        self.server_version = server_version


def detect_version_conflict(
    *,
    base_version: int | None,
    server_version: int | None,
) -> str | None:
    if base_version is None or server_version is None:
        return None
    if int(base_version) != int(server_version):
        return f'version_mismatch: client={base_version} server={server_version}'
    return None


def resolve_conflict(strategy: str, *, server_payload: dict, client_payload: dict) -> dict:
    key = (strategy or CONFLICT_STRATEGY_MANUAL).strip().lower()
    if key == CONFLICT_STRATEGY_SERVER_WINS:
        return dict(server_payload)
    if key == CONFLICT_STRATEGY_CLIENT_WINS:
        return dict(client_payload)
    raise SyncConflictError('conflict_requires_manual_resolution')
