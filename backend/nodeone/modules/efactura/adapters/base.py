"""Interfaz base para proveedores PAC."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from models.efactura import ElectronicInvoiceDocument, ElectronicInvoiceProviderConfig


class EInvoiceProviderAdapter(ABC):
    def __init__(self, config: ElectronicInvoiceProviderConfig) -> None:
        self.config = config

    @abstractmethod
    def test_connection(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def emit_invoice(self, document: ElectronicInvoiceDocument, pac_payload: dict) -> dict[str, Any]:
        ...

    def emit_credit_note(self, document: ElectronicInvoiceDocument, pac_payload: dict) -> dict[str, Any]:
        raise NotImplementedError('Nota de crédito: Fase D')

    def emit_debit_note(self, document: ElectronicInvoiceDocument, pac_payload: dict) -> dict[str, Any]:
        raise NotImplementedError('Nota de débito: Fase D')

    def query_status(self, cufe: str) -> dict[str, Any]:
        raise NotImplementedError('Consulta estado: Fase E')

    def download_pdf(self, cufe: str) -> dict[str, Any]:
        raise NotImplementedError('Descarga PDF: Fase E')

    def download_xml(self, cufe: str) -> dict[str, Any]:
        raise NotImplementedError('Descarga XML: Fase E')
