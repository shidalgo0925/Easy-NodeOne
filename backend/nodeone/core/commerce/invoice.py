"""InvoiceService — facturas comerciales (Etapa 12)."""

from __future__ import annotations

from nodeone.core.commerce.constants import INVOICE_KIND_FISCAL, INVOICE_KIND_NON_FISCAL
from nodeone.core.commerce.dtos import InvoiceDTO, InvoiceLineDTO
from nodeone.core.commerce.events import COMMERCE_INVOICE_CANCELLED, COMMERCE_INVOICE_ISSUED
from nodeone.core.services.audit import AuditService


def _invoice_kind(row) -> str:
    """Heurística v1: factura contable posted/paid → fiscal; draft sin FE → non_fiscal."""
    status = (getattr(row, 'status', None) or '').strip().lower()
    if status in ('posted', 'partial', 'paid'):
        return INVOICE_KIND_FISCAL
    return INVOICE_KIND_NON_FISCAL


def _to_dto(row, lines: list) -> InvoiceDTO:
    return InvoiceDTO(
        id=int(row.id),
        organization_id=int(row.organization_id),
        number=str(row.number or ''),
        status=str(row.status or 'draft'),
        kind=_invoice_kind(row),
        contact_id=int(row.contact_id) if getattr(row, 'contact_id', None) else None,
        currency=str(row.currency or 'USD'),
        grand_total=float(row.grand_total or 0.0),
        amount_paid=float(row.amount_paid or 0.0),
        lines=tuple(
            InvoiceLineDTO(
                description=str(line.description or ''),
                quantity=float(line.quantity or 0.0),
                unit_price=float(line.price_unit or 0.0),
                line_total=float(line.total or 0.0),
                product_id=int(line.product_id) if getattr(line, 'product_id', None) else None,
            )
            for line in lines
        ),
        date=getattr(row, 'date', None),
    )


class InvoiceService:
    """Lectura sobre facturas contables legacy; emisión unificada en Etapa 14."""

    @staticmethod
    def get(organization_id: int, invoice_id: int) -> InvoiceDTO | None:
        from nodeone.modules.accounting.models import Invoice, InvoiceLine

        row = Invoice.query.filter_by(
            organization_id=int(organization_id),
            id=int(invoice_id),
        ).first()
        if row is None:
            return None
        lines = (
            InvoiceLine.query.filter_by(invoice_id=int(row.id))
            .order_by(InvoiceLine.id.asc())
            .all()
        )
        return _to_dto(row, lines)

    @staticmethod
    def publish_issued(
        organization_id: int,
        *,
        invoice_number: str,
        order_ref: str | None = None,
        grand_total: float | None = None,
        source_app_id: str = 'eposone',
    ):
        payload: dict = {'invoice_number': invoice_number}
        if order_ref:
            payload['order_ref'] = order_ref
        if grand_total is not None:
            payload['grand_total'] = grand_total
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_INVOICE_ISSUED,
            payload,
            source_app_id=source_app_id,
        )

    @staticmethod
    def publish_cancelled(
        organization_id: int,
        *,
        invoice_number: str,
        reason: str | None = None,
        source_app_id: str = 'eposone',
    ):
        payload: dict = {'invoice_number': invoice_number}
        if reason:
            payload['reason'] = reason
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_INVOICE_CANCELLED,
            payload,
            source_app_id=source_app_id,
        )
