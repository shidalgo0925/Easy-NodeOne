"""PosTerminalService — terminales/dispositivos POS (Etapa 14 + V4 + ADR-005)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from models.commercial_core import CorePosTerminal
from nodeone.core.commerce.constants import POS_TERMINAL_ACTIVE
from nodeone.core.commerce.dtos import PosTerminalDTO
from nodeone.core.commerce.events import COMMERCE_POS_TERMINAL_REGISTERED
from nodeone.core.commerce.order import OrderValidationError
from nodeone.core.commerce.persistence import pos_terminal_to_dto
from nodeone.core.license.policy import policy_for_organization
from nodeone.core.services.audit import AuditService

_VALID_PROFILES = frozenset({'fixed', 'handheld'})


class PosTerminalService:
    @staticmethod
    def register(
        organization_id: int,
        *,
        terminal_ref: str,
        device_label: str | None = None,
        register_ref: str | None = None,
        profile: str | None = None,
        platform: str | None = None,
        device_model: str | None = None,
        app_version: str | None = None,
        android_version: str | None = None,
        branch_ref: str | None = None,
        pos_ref: str | None = None,
        sync_enabled: bool | None = None,
    ) -> PosTerminalDTO:
        from app import db

        ref = (terminal_ref or '').strip()
        if not ref:
            raise OrderValidationError('terminal_ref_required')
        prof = (profile or 'fixed').strip().lower() or 'fixed'
        if prof not in _VALID_PROFILES:
            raise OrderValidationError(f'invalid_profile:{prof}')

        # Dispositivos no consumen licencia POS; hook preparado (siempre True hoy)
        policy_for_organization(int(organization_id)).assert_can_create('device')

        existing = CorePosTerminal.query.filter_by(
            organization_id=int(organization_id),
            terminal_ref=ref,
        ).first()
        if existing is not None:
            # Re-registro / actualización de metadatos V4
            if device_label is not None:
                existing.device_label = device_label or None
            if register_ref is not None:
                existing.register_ref = register_ref or None
            existing.profile = prof
            if platform is not None:
                existing.platform = platform or None
            if device_model is not None:
                existing.device_model = device_model or None
            if app_version is not None:
                existing.app_version = app_version or None
            if android_version is not None:
                existing.android_version = android_version or None
            if branch_ref is not None:
                existing.branch_ref = branch_ref or None
            if pos_ref is not None:
                existing.pos_ref = (pos_ref or '').strip() or None
            if sync_enabled is not None:
                existing.sync_enabled = bool(sync_enabled)
            existing.status = POS_TERMINAL_ACTIVE
            existing.last_seen_at = datetime.utcnow()
            db.session.commit()
            return pos_terminal_to_dto(existing)

        row = CorePosTerminal(
            organization_id=int(organization_id),
            terminal_ref=ref,
            register_ref=(register_ref or None),
            status=POS_TERMINAL_ACTIVE,
            device_label=(device_label or None),
            profile=prof,
            platform=(platform or None),
            device_model=(device_model or None),
            app_version=(app_version or None),
            android_version=(android_version or None),
            branch_ref=(branch_ref or None),
            pos_ref=(pos_ref or '').strip() or None,
            sync_enabled=True if sync_enabled is None else bool(sync_enabled),
            last_seen_at=datetime.utcnow(),
        )
        db.session.add(row)
        db.session.commit()
        PosTerminalService.publish_registered(
            int(organization_id),
            terminal_ref=ref,
            register_ref=register_ref,
            pos_ref=pos_ref,
        )
        return pos_terminal_to_dto(row)

    @staticmethod
    def heartbeat(
        organization_id: int,
        terminal_ref: str,
        *,
        last_seen_at: str | None = None,
        app_version: str | None = None,
    ) -> PosTerminalDTO | None:
        from app import db

        ref = (terminal_ref or '').strip()
        if not ref:
            return None
        row = CorePosTerminal.query.filter_by(
            organization_id=int(organization_id),
            terminal_ref=ref,
        ).first()
        if row is None:
            return None
        if last_seen_at:
            try:
                # Accept ISO-ish; fallback utcnow
                ts = last_seen_at.replace('Z', '+00:00')
                row.last_seen_at = datetime.fromisoformat(ts).replace(tzinfo=None)
            except ValueError:
                row.last_seen_at = datetime.utcnow()
        else:
            row.last_seen_at = datetime.utcnow()
        if app_version is not None:
            row.app_version = app_version or None
        db.session.commit()
        return pos_terminal_to_dto(row)

    @staticmethod
    def list_terminals(
        organization_id: int,
        *,
        limit: int = 100,
        pos_ref: str | None = None,
    ) -> list[PosTerminalDTO]:
        q = CorePosTerminal.query.filter_by(organization_id=int(organization_id))
        if pos_ref:
            q = q.filter_by(pos_ref=(pos_ref or '').strip())
        rows = (
            q.order_by(CorePosTerminal.terminal_ref.asc(), CorePosTerminal.id.asc())
            .limit(max(1, int(limit)))
            .all()
        )
        return [pos_terminal_to_dto(row) for row in rows]

    @staticmethod
    def get(organization_id: int, terminal_id: int) -> PosTerminalDTO | None:
        row = CorePosTerminal.query.filter_by(
            organization_id=int(organization_id),
            id=int(terminal_id),
        ).first()
        return pos_terminal_to_dto(row) if row is not None else None

    @staticmethod
    def get_by_ref(organization_id: int, terminal_ref: str) -> PosTerminalDTO | None:
        ref = (terminal_ref or '').strip()
        if not ref:
            return None
        row = CorePosTerminal.query.filter_by(
            organization_id=int(organization_id),
            terminal_ref=ref,
        ).first()
        return pos_terminal_to_dto(row) if row is not None else None

    @staticmethod
    def resolve_id(organization_id: int, data: dict) -> int | None:
        """Resuelve terminal_id desde terminal_id o terminal_ref."""
        oid = int(organization_id)
        if data.get('terminal_id') is not None:
            terminal_id = int(data['terminal_id'])
            row = CorePosTerminal.query.filter_by(organization_id=oid, id=terminal_id).first()
            if row is None:
                raise OrderValidationError('invalid_terminal_id')
            return int(row.id)
        terminal_ref = (str(data.get('terminal_ref') or data.get('device_id') or '')).strip()
        if terminal_ref:
            row = CorePosTerminal.query.filter_by(organization_id=oid, terminal_ref=terminal_ref).first()
            if row is None:
                raise OrderValidationError(f'invalid_terminal_ref:{terminal_ref}')
            return int(row.id)
        if data.get('pos_terminal_id') is not None:
            terminal_id = int(data['pos_terminal_id'])
            row = CorePosTerminal.query.filter_by(organization_id=oid, id=terminal_id).first()
            if row is None:
                raise OrderValidationError('invalid_pos_terminal_id')
            return int(row.id)
        return None

    @staticmethod
    def publish_registered(
        organization_id: int,
        *,
        terminal_ref: str,
        register_ref: str | None = None,
        pos_ref: str | None = None,
        source_app_id: str = 'eposone',
    ):
        payload: dict[str, Any] = {'terminal_ref': terminal_ref}
        if register_ref:
            payload['register_ref'] = register_ref
        if pos_ref:
            payload['pos_ref'] = pos_ref
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_POS_TERMINAL_REGISTERED,
            payload,
            source_app_id=source_app_id,
        )
