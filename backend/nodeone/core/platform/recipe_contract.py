"""Contrato de dominio recetas/BOM (fase siguiente — no operacional).

Cuando un producto vendido explote a ingredientes:

    Cuba Libre vendido → Ron -45 ml, Coca-Cola -X

eso requiere un BOM por producto vendible + UOM de consumo. No se aplica en
SALE hoy: el SALE Connected descuenta el ``product_ref`` de la línea del pedido.

No improvisar recetas con ajustes. Esta fase cubre movimientos + toma física.
"""

from __future__ import annotations

from typing import Any, TypedDict


class RecipeComponent(TypedDict):
    product_ref: str
    quantity: float
    uom: str


class RecipeContractError(ValueError):
    pass


def explode_sale_components(
    organization_id: int,
    sold_product_ref: str,
    quantity: float,
) -> list[RecipeComponent]:
    """Reservado. No hay tabla de recetas en el ledger ADR-039."""
    raise RecipeContractError('recipe_bom_not_implemented')


def recipe_contract_status() -> dict[str, Any]:
    return {
        'status': 'deferred',
        'operational': False,
        'sale_today': 'deducts_order_line_product_ref',
        'next_phase': 'product_recipe_components + explode_on_SALE',
    }
