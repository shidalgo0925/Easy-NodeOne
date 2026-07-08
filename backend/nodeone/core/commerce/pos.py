"""PosTerminalService — terminales POS (Etapa 12 stub)."""

from __future__ import annotations

from nodeone.core.commerce.dtos import PosTerminalDTO
from nodeone.core.commerce.events import COMMERCE_POS_TERMINAL_REGISTERED
from nodeone.core.commerce.order import CommerceNotReadyError
from nodeone.core.services.audit import AuditService


class PosTerminalService:
    @staticmethod
    def register(
        organization_id: int,
        *,
        terminal_ref: str,
        device_label: str | None = None,
        register_ref: str | None = None,
    ) -> PosTerminalDTO:
        raise CommerceNotReadyError(
            'PosTerminalService.register pendiente de core_pos_terminal (Etapa 14).'
        )

    @staticmethod
    def publish_registered(
        organization_id: int,
        *,
        terminal_ref: str,
        register_ref: str | None = None,
        source_app_id: str = 'eposone',
    ):
        payload: dict = {'terminal_ref': terminal_ref}
        if register_ref:
            payload['register_ref'] = register_ref
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_POS_TERMINAL_REGISTERED,
            payload,
            source_app_id=source_app_id,
        )
