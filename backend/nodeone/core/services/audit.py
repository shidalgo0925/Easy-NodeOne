"""AuditService — auditoría y eventos de dominio (Etapa 11)."""

from __future__ import annotations

from typing import Any

from nodeone.core.platform.events import publish_domain_event


class AuditService:
    @staticmethod
    def publish_domain_event(
        organization_id: int,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        source_app_id: str = 'core',
    ):
        return publish_domain_event(
            int(organization_id),
            event_type,
            payload,
            source_app_id=source_app_id,
        )

    @staticmethod
    def log_system_action(
        action: str,
        *,
        organization_id: int | None = None,
        context: dict[str, Any] | None = None,
        status: str = 'success',
    ) -> None:
        from history_module import HistoryLogger

        ctx = dict(context or {})
        if organization_id is not None:
            ctx['organization_id'] = int(organization_id)
        HistoryLogger.log_system_action(action, status=status, context=ctx)
