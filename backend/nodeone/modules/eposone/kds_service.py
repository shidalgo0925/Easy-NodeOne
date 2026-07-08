"""KdsService — cocina / bar / runner (Etapa 15)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from models.commercial_core import CoreCommercialOrder
from models.eposone_kds import (
    KDS_STATION_KITCHEN,
    KDS_TICKET_PENDING,
    KDS_TICKET_PREPARING,
    KDS_TICKET_READY,
    KDS_TICKET_SERVED,
    KDS_TICKET_CANCELLED,
    EposoneKdsStation,
    EposoneKdsTicket,
    EposoneKdsTicketLine,
)
from nodeone.core.commerce.constants import ORDER_STATUS_CONFIRMED, ORDER_STATUS_IN_PROGRESS
from nodeone.core.commerce.order import OrderValidationError
from nodeone.core.services.audit import AuditService

EPOSONE_KDS_TICKET_CREATED = 'eposone.kds.ticket.created'
EPOSONE_KDS_TICKET_READY = 'eposone.kds.ticket.ready'
EPOSONE_KDS_TICKET_SERVED = 'eposone.kds.ticket.served'

KDS_TICKET_TRANSITIONS: dict[str, frozenset[str]] = {
    KDS_TICKET_PENDING: frozenset({KDS_TICKET_PREPARING, KDS_TICKET_CANCELLED}),
    KDS_TICKET_PREPARING: frozenset({KDS_TICKET_READY, KDS_TICKET_CANCELLED}),
    KDS_TICKET_READY: frozenset({KDS_TICKET_SERVED, KDS_TICKET_PREPARING}),
    KDS_TICKET_SERVED: frozenset(),
    KDS_TICKET_CANCELLED: frozenset(),
}


@dataclass(frozen=True)
class KdsTicketLineDTO:
    description: str
    quantity: float
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {'description': self.description, 'quantity': self.quantity, 'status': self.status}


@dataclass(frozen=True)
class KdsTicketDTO:
    id: int
    organization_id: int
    order_id: int
    order_ref: str
    station_type: str
    status: str
    priority: int
    lines: tuple[KdsTicketLineDTO, ...]
    created_at: datetime | None = None
    ready_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'order_id': self.order_id,
            'order_ref': self.order_ref,
            'station_type': self.station_type,
            'status': self.status,
            'priority': self.priority,
            'lines': [line.to_dict() for line in self.lines],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'ready_at': self.ready_at.isoformat() if self.ready_at else None,
        }


def _ticket_to_dto(row: EposoneKdsTicket) -> KdsTicketDTO:
    return KdsTicketDTO(
        id=int(row.id),
        organization_id=int(row.organization_id),
        order_id=int(row.order_id),
        order_ref=str(row.order_ref),
        station_type=str(row.station_type),
        status=str(row.status),
        priority=int(row.priority or 0),
        lines=tuple(
            KdsTicketLineDTO(
                description=str(line.description or ''),
                quantity=float(line.quantity or 0),
                status=str(line.status or KDS_TICKET_PENDING),
            )
            for line in (row.lines or [])
        ),
        created_at=row.created_at,
        ready_at=row.ready_at,
    )


class KdsService:
    @staticmethod
    def ensure_default_station(organization_id: int, *, station_type: str = KDS_STATION_KITCHEN) -> EposoneKdsStation:
        from app import db

        ref = f'{station_type}-main'
        row = EposoneKdsStation.query.filter_by(
            organization_id=int(organization_id),
            station_ref=ref,
        ).first()
        if row is not None:
            return row
        names = {
            KDS_STATION_KITCHEN: 'Cocina principal',
            'bar': 'Bar principal',
            'runner': 'Runner principal',
        }
        row = EposoneKdsStation(
            organization_id=int(organization_id),
            station_ref=ref,
            name=names.get(station_type, station_type.title()),
            station_type=station_type,
            active=True,
        )
        db.session.add(row)
        db.session.commit()
        return row

    @staticmethod
    def list_tickets(
        organization_id: int,
        *,
        station_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[KdsTicketDTO]:
        q = EposoneKdsTicket.query.filter_by(organization_id=int(organization_id))
        if station_type:
            q = q.filter_by(station_type=(station_type or '').strip().lower())
        if status:
            q = q.filter_by(status=(status or '').strip().lower())
        rows = q.order_by(EposoneKdsTicket.priority.desc(), EposoneKdsTicket.id.asc()).limit(
            max(1, min(int(limit), 200))
        ).all()
        return [_ticket_to_dto(r) for r in rows]

    @staticmethod
    def create_tickets_for_order(organization_id: int, order_id: int) -> list[KdsTicketDTO]:
        from app import db

        order = CoreCommercialOrder.query.filter_by(
            organization_id=int(organization_id),
            id=int(order_id),
        ).first()
        if order is None:
            raise OrderValidationError('order_not_found')
        existing = EposoneKdsTicket.query.filter_by(
            organization_id=int(organization_id),
            order_id=int(order_id),
        ).first()
        if existing is not None:
            return [_ticket_to_dto(existing)]

        station = KdsService.ensure_default_station(int(organization_id), station_type=KDS_STATION_KITCHEN)
        ticket = EposoneKdsTicket(
            organization_id=int(organization_id),
            order_id=int(order.id),
            order_ref=str(order.order_ref),
            station_id=int(station.id),
            station_type=KDS_STATION_KITCHEN,
            status=KDS_TICKET_PENDING,
        )
        ticket.lines = [
            EposoneKdsTicketLine(
                description=str(line.description or ''),
                quantity=float(line.quantity or 1),
                status=KDS_TICKET_PENDING,
            )
            for line in (order.lines or [])
        ]
        db.session.add(ticket)
        db.session.commit()
        dto = _ticket_to_dto(ticket)
        AuditService.publish_domain_event(
            int(organization_id),
            EPOSONE_KDS_TICKET_CREATED,
            {'ticket_id': dto.id, 'order_ref': dto.order_ref, 'station_type': dto.station_type},
            source_app_id='eposone',
        )
        return [dto]

    @staticmethod
    def maybe_enqueue_for_order_status(organization_id: int, order_id: int, order_status: str) -> None:
        st = (order_status or '').strip().lower()
        if st in (ORDER_STATUS_CONFIRMED, ORDER_STATUS_IN_PROGRESS):
            KdsService.create_tickets_for_order(int(organization_id), int(order_id))

    @staticmethod
    def transition_ticket(
        organization_id: int,
        ticket_id: int,
        target_status: str,
    ) -> KdsTicketDTO:
        from app import db

        row = EposoneKdsTicket.query.filter_by(
            organization_id=int(organization_id),
            id=int(ticket_id),
        ).first()
        if row is None:
            raise OrderValidationError('ticket_not_found')
        tgt = (target_status or '').strip().lower()
        cur = str(row.status or '')
        allowed = KDS_TICKET_TRANSITIONS.get(cur, frozenset())
        if tgt not in allowed and tgt != cur:
            raise OrderValidationError(f'invalid_kds_transition:{cur}->{tgt}')

        row.status = tgt
        if tgt == KDS_TICKET_READY:
            row.ready_at = datetime.utcnow()
            AuditService.publish_domain_event(
                int(organization_id),
                EPOSONE_KDS_TICKET_READY,
                {'ticket_id': int(row.id), 'order_ref': str(row.order_ref)},
                source_app_id='eposone',
            )
        if tgt == KDS_TICKET_SERVED:
            row.served_at = datetime.utcnow()
            AuditService.publish_domain_event(
                int(organization_id),
                EPOSONE_KDS_TICKET_SERVED,
                {'ticket_id': int(row.id), 'order_ref': str(row.order_ref)},
                source_app_id='eposone',
            )
        db.session.commit()
        return _ticket_to_dto(row)
