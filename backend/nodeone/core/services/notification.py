"""NotificationService — envío unificado (Etapa 11)."""

from __future__ import annotations

from typing import Any


class NotificationService:
    """Punto de entrada para comunicaciones; delega en CommunicationEngine."""

    @staticmethod
    def trigger(
        event_code: str,
        user_id: int,
        *,
        organization_id: int | None = None,
        context: dict[str, Any] | None = None,
    ):
        from nodeone.modules.communications.services.engine import CommunicationEngine

        return CommunicationEngine.trigger(
            event_code,
            int(user_id),
            organization_id=organization_id,
            context=context or {},
        )
