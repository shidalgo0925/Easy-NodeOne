"""OrderService — pedidos comerciales (Etapa 14)."""

from __future__ import annotations

from typing import Any

from models.commercial_core import CoreCommercialOrder, CoreCommercialOrderLine
from nodeone.core.commerce.constants import (
    ORDER_FISCAL_STATUS_NOT_REQUIRED,
    ORDER_PAYMENT_STATUS_UNPAID,
    ORDER_STATUS_CONFIRMED,
    ORDER_STATUS_DRAFT,
    can_transition_order_status,
)
from nodeone.core.commerce.dtos import OrderDTO
from nodeone.core.commerce.events import (
    COMMERCE_ORDER_CANCELLED,
    COMMERCE_ORDER_CONFIRMED,
    COMMERCE_ORDER_CREATED,
    COMMERCE_ORDER_PAYMENT_STATUS_CHANGED,
    COMMERCE_ORDER_STATUS_CHANGED,
)
from nodeone.core.commerce.persistence import order_to_dto
from nodeone.core.services.audit import AuditService

class CommerceNotReadyError(NotImplementedError):
    """Reservado — tablas comerciales no disponibles."""


class OrderValidationError(ValueError):
    pass


class OrderService:
    """API Core de pedidos — persistencia en core_commercial_order."""

    @staticmethod
    def can_transition(current_status: str, target_status: str) -> bool:
        return can_transition_order_status(current_status, target_status)

    @staticmethod
    def get(organization_id: int, order_id: int) -> OrderDTO | None:
        row = CoreCommercialOrder.query.filter_by(
            organization_id=int(organization_id),
            id=int(order_id),
        ).first()
        return order_to_dto(row) if row is not None else None

    @staticmethod
    def get_by_ref(organization_id: int, order_ref: str) -> OrderDTO | None:
        row = CoreCommercialOrder.query.filter_by(
            organization_id=int(organization_id),
            order_ref=(order_ref or '').strip(),
        ).first()
        return order_to_dto(row) if row is not None else None

    @staticmethod
    def search(
        organization_id: int,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[OrderDTO], int]:
        q = CoreCommercialOrder.query.filter_by(organization_id=int(organization_id))
        if status:
            q = q.filter_by(status=(status or '').strip().lower())
        total = q.count()
        rows = (
            q.order_by(CoreCommercialOrder.id.desc())
            .offset(max(0, int(offset)))
            .limit(max(1, min(int(limit), 200)))
            .all()
        )
        return [order_to_dto(r) for r in rows], int(total)

    @staticmethod
    def create(organization_id: int, data: dict[str, Any], *, source_app_id: str = 'eposone') -> OrderDTO:
        from app import db

        oid = int(organization_id)
        lines_in = data.get('lines') if isinstance(data.get('lines'), list) else []
        if not lines_in:
            raise OrderValidationError('lines_required')

        order_ref = (data.get('order_ref') or '').strip() or OrderService._next_order_ref(oid)

        subtotal = 0.0
        tax_total = float(data.get('tax_total') or 0)
        line_rows: list[CoreCommercialOrderLine] = []
        for raw in lines_in:
            if not isinstance(raw, dict):
                continue
            qty = float(raw.get('quantity') or 1)
            unit = float(raw.get('unit_price') or 0)
            line_total = round(qty * unit, 2)
            subtotal += line_total
            line_rows.append(
                CoreCommercialOrderLine(
                    description=str(raw.get('description') or 'Ítem')[:500],
                    quantity=qty,
                    unit_price=unit,
                    line_total=line_total,
                    product_ref=(str(raw.get('product_ref')).strip()[:128] if raw.get('product_ref') else None),
                )
            )
        if not line_rows:
            raise OrderValidationError('lines_required')

        grand_total = round(subtotal + tax_total, 2)
        row = CoreCommercialOrder(
            organization_id=oid,
            order_ref=order_ref,
            status=str(data.get('status') or ORDER_STATUS_DRAFT).strip().lower() or ORDER_STATUS_DRAFT,
            payment_status=ORDER_PAYMENT_STATUS_UNPAID,
            fiscal_status=ORDER_FISCAL_STATUS_NOT_REQUIRED,
            contact_id=int(data['contact_id']) if data.get('contact_id') else None,
            currency=str(data.get('currency') or 'USD')[:8],
            subtotal=subtotal,
            tax_total=tax_total,
            grand_total=grand_total,
            source_app_id=(source_app_id or 'eposone').strip().lower() or 'eposone',
            notes=(str(data.get('notes')).strip()[:5000] if data.get('notes') else None),
        )
        row.lines = line_rows
        db.session.add(row)
        db.session.commit()

        dto = order_to_dto(row)
        OrderService.publish_created(
            oid,
            order_ref=dto.order_ref,
            status=dto.status,
            payment_status=dto.payment_status,
            grand_total=dto.grand_total,
            source_app_id=source_app_id,
            extra={'order_id': dto.id},
        )
        return dto

    @staticmethod
    def _next_order_ref(organization_id: int) -> str:
        import re

        prefix = 'POS'
        rx = re.compile(rf'^{re.escape(prefix)}-(\d{{1,12}})\Z')
        max_seq = 0
        for (ref,) in (
            CoreCommercialOrder.query.filter_by(organization_id=int(organization_id))
            .with_entities(CoreCommercialOrder.order_ref)
            .all()
        ):
            m = rx.match(str(ref or '').strip())
            if m:
                max_seq = max(max_seq, int(m.group(1)))
        return f'{prefix}-{max_seq + 1:04d}'

    @staticmethod
    def transition_status(
        organization_id: int,
        order_id: int,
        target_status: str,
        *,
        source_app_id: str = 'eposone',
        reason: str | None = None,
    ) -> OrderDTO:
        from app import db

        row = CoreCommercialOrder.query.filter_by(
            organization_id=int(organization_id),
            id=int(order_id),
        ).first()
        if row is None:
            raise OrderValidationError('order_not_found')
        tgt = (target_status or '').strip().lower()
        cur = str(row.status or '')
        if not OrderService.can_transition(cur, tgt):
            raise OrderValidationError(f'invalid_transition:{cur}->{tgt}')

        OrderService.publish_status_changed(
            int(organization_id),
            order_ref=str(row.order_ref),
            from_status=cur,
            to_status=tgt,
            source_app_id=source_app_id,
        )
        if tgt == ORDER_STATUS_CONFIRMED:
            OrderService.publish_confirmed(
                int(organization_id), order_ref=str(row.order_ref), source_app_id=source_app_id
            )
        if tgt == 'cancelled':
            OrderService.publish_cancelled(
                int(organization_id),
                order_ref=str(row.order_ref),
                reason=reason,
                source_app_id=source_app_id,
            )

        row.status = tgt
        row.version = int(row.version or 1) + 1
        db.session.commit()

        from nodeone.modules.eposone.kds_service import KdsService

        try:
            KdsService.maybe_enqueue_for_order_status(int(organization_id), int(order_id), tgt)
        except Exception:
            pass

        try:
            from nodeone.modules.eposone.delivery_service import EposoneDeliveryService

            EposoneDeliveryService.maybe_create_for_order_status(int(organization_id), int(order_id), tgt)
        except Exception:
            pass

        return order_to_dto(row)

    @staticmethod
    def publish_created(
        organization_id: int,
        *,
        order_ref: str,
        status: str,
        payment_status: str | None = None,
        grand_total: float | None = None,
        source_app_id: str = 'eposone',
        extra: dict[str, Any] | None = None,
    ):
        payload: dict[str, Any] = {'order_ref': order_ref, 'status': status}
        if payment_status is not None:
            payload['payment_status'] = payment_status
        if grand_total is not None:
            payload['grand_total'] = grand_total
        if extra:
            payload.update(extra)
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_ORDER_CREATED,
            payload,
            source_app_id=source_app_id,
        )

    @staticmethod
    def publish_payment_status_changed(
        organization_id: int,
        *,
        order_ref: str,
        from_status: str,
        to_status: str,
        source_app_id: str = 'eposone',
    ):
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_ORDER_PAYMENT_STATUS_CHANGED,
            {
                'order_ref': order_ref,
                'from_payment_status': from_status,
                'to_payment_status': to_status,
            },
            source_app_id=source_app_id,
        )

    @staticmethod
    def publish_status_changed(
        organization_id: int,
        *,
        order_ref: str,
        from_status: str,
        to_status: str,
        source_app_id: str = 'eposone',
    ):
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_ORDER_STATUS_CHANGED,
            {
                'order_ref': order_ref,
                'from_status': from_status,
                'to_status': to_status,
            },
            source_app_id=source_app_id,
        )

    @staticmethod
    def publish_confirmed(organization_id: int, *, order_ref: str, source_app_id: str = 'eposone'):
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_ORDER_CONFIRMED,
            {'order_ref': order_ref},
            source_app_id=source_app_id,
        )

    @staticmethod
    def publish_cancelled(
        organization_id: int,
        *,
        order_ref: str,
        reason: str | None = None,
        source_app_id: str = 'eposone',
    ):
        payload: dict[str, Any] = {'order_ref': order_ref}
        if reason:
            payload['reason'] = reason
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_ORDER_CANCELLED,
            payload,
            source_app_id=source_app_id,
        )
