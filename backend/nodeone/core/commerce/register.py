"""Registro de handlers del bus comercial (Etapa 8)."""

from __future__ import annotations


def register_commerce_bus_handlers() -> None:
    from nodeone.core.commerce.fiscal_handlers import register_commerce_fiscal_handlers
    from nodeone.core.commerce.inventory_handlers import register_commerce_inventory_handlers
    from nodeone.core.commerce.report_handlers import register_commerce_report_handlers

    register_commerce_fiscal_handlers()
    register_commerce_inventory_handlers()
    register_commerce_report_handlers()
