"""Emisión fiscal comercial — Etapa 7 (dominio 6.8)."""

from __future__ import annotations

from typing import Any

from models.commercial_core import CoreCommercialOrder
from nodeone.core.commerce.constants import ORDER_FISCAL_STATUS_PENDING
from nodeone.core.commerce.events import COMMERCE_INVOICE_REQUESTED
from nodeone.core.commerce.order import OrderValidationError
from nodeone.core.services.audit import AuditService


class CommerceFiscalService:
    """Encola emisión fiscal para pedidos con fiscal_status=pending."""

    @staticmethod
    def request_for_order(
        organization_id: int,
        order_id: int,
        *,
        source_app_id: str = 'eposone',
    ) -> dict[str, Any]:
        oid = int(organization_id)
        order = CoreCommercialOrder.query.filter_by(organization_id=oid, id=int(order_id)).first()
        if order is None:
            raise OrderValidationError('order_not_found')
        if str(order.fiscal_status or '') != ORDER_FISCAL_STATUS_PENDING:
            return {'status': 'skipped', 'reason': 'fiscal_not_pending'}

        AuditService.publish_domain_event(
            oid,
            COMMERCE_INVOICE_REQUESTED,
            {
                'order_id': int(order.id),
                'order_ref': str(order.order_ref),
                'grand_total': float(order.grand_total or 0),
                'contact_id': int(order.contact_id) if order.contact_id else None,
                'payment_status': str(order.payment_status or ''),
            },
            source_app_id=source_app_id,
        )
        return {'status': 'queued', 'order_ref': str(order.order_ref)}
