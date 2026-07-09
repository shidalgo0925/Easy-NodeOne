"""Emisión fiscal comercial — Etapa 7 (dominio 6.8)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from models.commercial_core import CoreCommercialOrder
from nodeone.core.commerce.constants import (
    ORDER_FISCAL_STATUS_CANCELLED,
    ORDER_FISCAL_STATUS_INVOICED,
    ORDER_FISCAL_STATUS_NOT_REQUIRED,
    ORDER_FISCAL_STATUS_PENDING,
)
from nodeone.core.commerce.events import (
    COMMERCE_CREDIT_NOTE_REQUESTED,
    COMMERCE_INVOICE_REQUESTED,
)
from nodeone.core.commerce.invoice import InvoiceService
from nodeone.core.commerce.order import OrderService, OrderValidationError
from nodeone.core.platform.events import DomainEventMessage
from nodeone.core.services.audit import AuditService


class CommerceFiscalService:
    """Encola y procesa emisión fiscal para pedidos con fiscal_status=pending."""

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

    @staticmethod
    def find_invoice_id_for_order(organization_id: int, order_id: int) -> int | None:
        """Localiza factura contable vinculada al pedido comercial."""
        from nodeone.modules.accounting.models import Invoice

        oid = int(organization_id)
        marker = f'commercial_order_id={int(order_id)}'
        existing = (
            Invoice.query.filter_by(organization_id=oid)
            .filter(Invoice.notes.like(f'%{marker}%'))
            .first()
        )
        return int(existing.id) if existing is not None else None

    @staticmethod
    def request_credit_note_for_order(
        organization_id: int,
        order_id: int,
        *,
        payment_ref: str | None = None,
        refund_amount: float | None = None,
        source_app_id: str = 'eposone',
    ) -> dict[str, Any]:
        """Reembolso total con factura emitida — encola nota de crédito (§6.8)."""
        oid = int(organization_id)
        order = CoreCommercialOrder.query.filter_by(organization_id=oid, id=int(order_id)).first()
        if order is None:
            raise OrderValidationError('order_not_found')
        if str(order.fiscal_status or '') != ORDER_FISCAL_STATUS_INVOICED:
            return {'status': 'skipped', 'reason': 'fiscal_not_invoiced'}

        invoice_id = CommerceFiscalService.find_invoice_id_for_order(oid, int(order.id))
        invoice_number = f'POS-{order.order_ref}'[:50]
        if invoice_id is not None:
            from nodeone.modules.accounting.models import Invoice

            inv = Invoice.query.filter_by(organization_id=oid, id=int(invoice_id)).first()
            if inv is not None:
                invoice_number = str(inv.number or invoice_number)

        payload: dict[str, Any] = {
            'order_id': int(order.id),
            'order_ref': str(order.order_ref),
            'invoice_number': invoice_number,
            'document_type': 'credit_note',
        }
        if invoice_id is not None:
            payload['invoice_id'] = int(invoice_id)
        if payment_ref:
            payload['payment_ref'] = str(payment_ref)
        if refund_amount is not None:
            payload['refund_amount'] = float(refund_amount)

        AuditService.publish_domain_event(
            oid,
            COMMERCE_CREDIT_NOTE_REQUESTED,
            payload,
            source_app_id=source_app_id,
        )
        InvoiceService.publish_cancelled(
            oid,
            invoice_number=invoice_number,
            reason='full_refund_credit_note',
            source_app_id=source_app_id,
        )
        CommerceFiscalService._try_issue_credit_note_fe(
            oid,
            int(order.id),
            invoice_id,
            order,
            source_app_id=source_app_id,
        )
        return {'status': 'queued', 'order_ref': str(order.order_ref), 'invoice_number': invoice_number}

    @staticmethod
    def _try_issue_credit_note_fe(
        organization_id: int,
        order_id: int,
        invoice_id: int | None,
        order: CoreCommercialOrder,
        *,
        source_app_id: str,
    ) -> bool:
        if invoice_id is None:
            return False
        try:
            from nodeone.modules.efactura.services import config_service as cfg_svc
            from nodeone.services.efactura_module import is_efactura_enabled_for_org

            if not is_efactura_enabled_for_org(int(organization_id)):
                return False
            config = cfg_svc.get_or_create_provider_config(int(organization_id))
            if not cfg_svc.config_ready(config):
                return False
            # Emisión NCR real en efactura — Fase D; aquí solo señal de dominio.
        except Exception:
            return False
        return False

    @staticmethod
    def process_from_event(message: DomainEventMessage) -> dict[str, Any]:
        payload = dict(message.payload or {})
        order_id = payload.get('order_id')
        if not order_id:
            return {'status': 'skipped', 'reason': 'missing_order_id'}
        return CommerceFiscalService.process_pending_order(
            int(message.organization_id),
            int(order_id),
            source_app_id=str(message.source_app_id or 'eposone'),
        )

    @staticmethod
    def process_pending_order(
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

        if not order.contact_id:
            return {'status': 'pending', 'reason': 'no_fiscal_contact'}

        invoice_id = CommerceFiscalService._ensure_accounting_invoice(oid, order)
        if not invoice_id:
            return {'status': 'pending', 'reason': 'invoice_not_created'}

        issued = CommerceFiscalService._try_issue_fe(oid, int(invoice_id), order, source_app_id=source_app_id)
        if issued:
            return {'status': 'issued', 'order_ref': str(order.order_ref), 'invoice_id': invoice_id}
        return {'status': 'pending', 'reason': 'fe_not_issued', 'invoice_id': invoice_id}

    @staticmethod
    def _try_issue_fe(
        organization_id: int,
        invoice_id: int,
        order: CoreCommercialOrder,
        *,
        source_app_id: str,
    ) -> bool:
        try:
            from nodeone.modules.efactura.services import config_service as cfg_svc
            from nodeone.modules.efactura.services.issue import issue_from_commercial_invoice
            from nodeone.services.efactura_module import is_efactura_enabled_for_org

            if not is_efactura_enabled_for_org(int(organization_id)):
                return False
            config = cfg_svc.get_or_create_provider_config(int(organization_id))
            if not cfg_svc.config_ready(config):
                return False
            if (config.emission_mode or 'manual') != 'automatic':
                return False
            if not config.emit_on_payment_confirmed:
                return False
            issue_from_commercial_invoice(int(invoice_id), int(organization_id))
        except Exception:
            return False

        from app import db

        prev = str(order.fiscal_status)
        order.fiscal_status = ORDER_FISCAL_STATUS_INVOICED
        order.version = int(order.version or 1) + 1
        db.session.commit()
        OrderService.publish_fiscal_status_changed(
            int(organization_id),
            order_ref=str(order.order_ref),
            from_status=prev,
            to_status=ORDER_FISCAL_STATUS_INVOICED,
            source_app_id=source_app_id,
        )
        InvoiceService.publish_issued(
            int(organization_id),
            invoice_number=str(order.order_ref),
            order_ref=str(order.order_ref),
            grand_total=float(order.grand_total or 0),
            source_app_id=source_app_id,
        )
        return True

    @staticmethod
    def _ensure_accounting_invoice(organization_id: int, order: CoreCommercialOrder) -> int | None:
        from app import db
        from nodeone.modules.accounting.models import Invoice, InvoiceLine
        from models.users import User

        oid = int(organization_id)
        marker = f'commercial_order_id={int(order.id)}'
        existing = (
            Invoice.query.filter_by(organization_id=oid)
            .filter(Invoice.notes.like(f'%{marker}%'))
            .first()
        )
        if existing is not None:
            return int(existing.id)

        customer_user = User.query.filter_by(organization_id=oid).order_by(User.id.asc()).first()
        if customer_user is None:
            return None

        inv_number = f'POS-{order.order_ref}'[:50]
        suffix = 0
        while Invoice.query.filter_by(organization_id=oid, number=inv_number).first() is not None:
            suffix += 1
            inv_number = f'POS-{order.order_ref}-{suffix}'[:50]

        inv = Invoice(
            organization_id=oid,
            number=inv_number,
            customer_id=int(customer_user.id),
            contact_id=int(order.contact_id) if order.contact_id else None,
            currency=str(order.currency or 'USD'),
            notes=f'eposone {marker} order_ref={order.order_ref}',
            date=datetime.utcnow(),
            status='paid',
            total=float(order.subtotal or 0),
            tax_total=float(order.tax_total or 0),
            grand_total=float(order.grand_total or 0),
            amount_paid=float(order.amount_paid or 0),
        )
        db.session.add(inv)
        db.session.flush()
        for line in order.lines or []:
            qty = float(line.quantity or 1)
            unit = float(line.unit_price or 0)
            db.session.add(
                InvoiceLine(
                    invoice_id=int(inv.id),
                    description=str(line.description or '')[:500],
                    quantity=qty,
                    price_unit=unit,
                    subtotal=float(line.line_total or qty * unit),
                    total=float(line.line_total or qty * unit),
                )
            )
        db.session.commit()
        return int(inv.id)
