"""Handlers bus de eventos — emisión fiscal comercial (Etapa 7)."""

from __future__ import annotations

from nodeone.core.commerce.events import COMMERCE_INVOICE_REQUESTED
from nodeone.core.commerce.fiscal import CommerceFiscalService
from nodeone.core.platform.events import DomainEventMessage, subscribe

_REGISTERED = False


def _on_invoice_requested(message: DomainEventMessage) -> None:
    try:
        CommerceFiscalService.process_from_event(message)
    except Exception:
        # Dejar fiscal_status=pending; no romper despacho del bus.
        pass


def register_commerce_fiscal_handlers() -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    subscribe(COMMERCE_INVOICE_REQUESTED, _on_invoice_requested)
    _REGISTERED = True
