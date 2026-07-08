"""PosTerminalService — terminales POS (Etapa 14)."""

from __future__ import annotations

from models.commercial_core import CorePosTerminal
from nodeone.core.commerce.constants import POS_TERMINAL_ACTIVE
from nodeone.core.commerce.dtos import PosTerminalDTO
from nodeone.core.commerce.order import OrderValidationError
from nodeone.core.commerce.persistence import pos_terminal_to_dto
from nodeone.core.commerce.events import COMMERCE_POS_TERMINAL_REGISTERED
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
        from app import db

        ref = (terminal_ref or '').strip()
        if not ref:
            raise OrderValidationError('terminal_ref_required')
        existing = CorePosTerminal.query.filter_by(
            organization_id=int(organization_id),
            terminal_ref=ref,
        ).first()
        if existing is not None:
            return pos_terminal_to_dto(existing)

        row = CorePosTerminal(
            organization_id=int(organization_id),
            terminal_ref=ref,
            register_ref=(register_ref or None),
            status=POS_TERMINAL_ACTIVE,
            device_label=(device_label or None),
        )
        db.session.add(row)
        db.session.commit()
        PosTerminalService.publish_registered(
            int(organization_id),
            terminal_ref=ref,
            register_ref=register_ref,
        )
        return pos_terminal_to_dto(row)

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
