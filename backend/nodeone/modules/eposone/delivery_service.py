"""DeliveryService EPosOne — Etapa 16."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from models.commercial_core import CoreCommercialOrder
from models.eposone_delivery import (
    DELIVERY_STATUS_ASSIGNED,
    DELIVERY_STATUS_DELIVERED,
    DELIVERY_STATUS_IN_TRANSIT,
    DELIVERY_STATUS_PENDING,
    DELIVERY_TRANSITIONS,
    EposoneDelivery,
)
from nodeone.core.commerce.constants import ORDER_STATUS_READY
from nodeone.core.commerce.dtos import DeliveryDTO
from nodeone.core.commerce.events import COMMERCE_DELIVERY_COMPLETED, COMMERCE_DELIVERY_STARTED
from nodeone.core.commerce.order import OrderValidationError
from nodeone.core.services.audit import AuditService

EPOSONE_DELIVERY_ASSIGNED = 'eposone.delivery.assigned'


def _to_dto(row: EposoneDelivery) -> DeliveryDTO:
    return DeliveryDTO(
        id=int(row.id),
        organization_id=int(row.organization_id),
        order_ref=str(row.order_ref),
        status=str(row.status),
        delivered_qty=float(row.delivered_qty or 0),
        total_qty=float(row.total_qty or 0),
    )


class EposoneDeliveryService:
    @staticmethod
    def get(organization_id: int, delivery_id: int) -> DeliveryDTO | None:
        row = EposoneDelivery.query.filter_by(
            organization_id=int(organization_id),
            id=int(delivery_id),
        ).first()
        return _to_dto(row) if row is not None else None

    @staticmethod
    def list_deliveries(
        organization_id: int,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> list[DeliveryDTO]:
        q = EposoneDelivery.query.filter_by(organization_id=int(organization_id))
        if status:
            q = q.filter_by(status=(status or '').strip().lower())
        rows = q.order_by(EposoneDelivery.id.desc()).limit(max(1, min(int(limit), 200))).all()
        return [_to_dto(r) for r in rows]

    @staticmethod
    def create_for_order(
        organization_id: int,
        order_id: int,
        *,
        destination_address: str | None = None,
        notes: str | None = None,
    ) -> DeliveryDTO:
        from app import db

        order = CoreCommercialOrder.query.filter_by(
            organization_id=int(organization_id),
            id=int(order_id),
        ).first()
        if order is None:
            raise OrderValidationError('order_not_found')
        existing = EposoneDelivery.query.filter_by(
            organization_id=int(organization_id),
            order_id=int(order_id),
        ).first()
        if existing is not None:
            return _to_dto(existing)

        total_qty = sum(float(line.quantity or 0) for line in (order.lines or []))
        row = EposoneDelivery(
            organization_id=int(organization_id),
            order_id=int(order.id),
            order_ref=str(order.order_ref),
            status=DELIVERY_STATUS_PENDING,
            destination_address=(destination_address or None),
            notes=(notes or None),
            total_qty=total_qty,
            delivered_qty=0.0,
        )
        db.session.add(row)
        db.session.commit()
        return _to_dto(row)

    @staticmethod
    def maybe_create_for_order_status(organization_id: int, order_id: int, order_status: str) -> None:
        if (order_status or '').strip().lower() == ORDER_STATUS_READY:
            try:
                EposoneDeliveryService.create_for_order(int(organization_id), int(order_id))
            except OrderValidationError:
                pass

    @staticmethod
    def assign_driver(
        organization_id: int,
        delivery_id: int,
        *,
        driver_name: str,
        driver_contact_id: int | None = None,
    ) -> DeliveryDTO:
        from app import db

        row = EposoneDelivery.query.filter_by(
            organization_id=int(organization_id),
            id=int(delivery_id),
        ).first()
        if row is None:
            raise OrderValidationError('delivery_not_found')
        row.driver_name = (driver_name or '').strip()[:200] or None
        row.driver_contact_id = int(driver_contact_id) if driver_contact_id else None
        row.status = DELIVERY_STATUS_ASSIGNED
        row.assigned_at = datetime.utcnow()
        db.session.commit()
        AuditService.publish_domain_event(
            int(organization_id),
            EPOSONE_DELIVERY_ASSIGNED,
            {
                'delivery_id': int(row.id),
                'order_ref': str(row.order_ref),
                'driver_name': row.driver_name,
            },
            source_app_id='eposone',
        )
        return _to_dto(row)

    @staticmethod
    def transition_status(organization_id: int, delivery_id: int, target_status: str) -> DeliveryDTO:
        from app import db

        row = EposoneDelivery.query.filter_by(
            organization_id=int(organization_id),
            id=int(delivery_id),
        ).first()
        if row is None:
            raise OrderValidationError('delivery_not_found')
        tgt = (target_status or '').strip().lower()
        cur = str(row.status or '')
        if tgt not in DELIVERY_TRANSITIONS.get(cur, frozenset()) and tgt != cur:
            raise OrderValidationError(f'invalid_delivery_transition:{cur}->{tgt}')

        if tgt == DELIVERY_STATUS_IN_TRANSIT:
            AuditService.publish_domain_event(
                int(organization_id),
                COMMERCE_DELIVERY_STARTED,
                {'order_ref': str(row.order_ref), 'delivery_id': int(row.id)},
                source_app_id='eposone',
            )
        if tgt == DELIVERY_STATUS_DELIVERED:
            row.delivered_qty = float(row.total_qty or 0)
            row.delivered_at = datetime.utcnow()
            AuditService.publish_domain_event(
                int(organization_id),
                COMMERCE_DELIVERY_COMPLETED,
                {'order_ref': str(row.order_ref), 'delivery_id': int(row.id)},
                source_app_id='eposone',
            )

        row.status = tgt
        db.session.commit()
        return _to_dto(row)

    @staticmethod
    def to_detail_dict(row: EposoneDelivery) -> dict[str, Any]:
        dto = _to_dto(row)
        data = dto.to_dict()
        data.update(
            {
                'driver_name': row.driver_name,
                'driver_contact_id': row.driver_contact_id,
                'destination_address': row.destination_address,
                'notes': row.notes,
                'assigned_at': row.assigned_at.isoformat() if row.assigned_at else None,
                'delivered_at': row.delivered_at.isoformat() if row.delivered_at else None,
            }
        )
        return data
