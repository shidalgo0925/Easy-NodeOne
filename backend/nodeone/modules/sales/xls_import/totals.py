"""Recálculo de importes EN1 vs totales declarados en el XLS."""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from nodeone.modules.sales.xls_import.types import SalesImportData, SalesImportLine
from nodeone.services.tax_calculation import compute_line_amounts

MONEY = Decimal('0.01')


def money_tolerance() -> Decimal:
    raw = (os.environ.get('NODEONE_SALES_XLS_MONEY_TOLERANCE') or '').strip()
    try:
        n = Decimal(raw) if raw else Decimal('0.02')
    except Exception:
        n = Decimal('0.02')
    if n < Decimal('0'):
        n = Decimal('0.02')
    return n.quantize(MONEY)


def as_money(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0)).quantize(MONEY, rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal('0.00')


@dataclass
class LineCompute:
    description: str
    quantity: float
    unit_price: float
    discount: float
    tax_rate: float | None
    tax_id: int | None
    product_id: int | None
    subtotal: float
    tax_amount: float
    total: float
    declared_total: float | None


@dataclass
class TotalsResult:
    lines: list[LineCompute]
    subtotal: float
    tax_total: float
    grand_total: float
    declared_subtotal: float | None
    declared_tax: float | None
    declared_total: float | None
    difference: float
    within_tolerance: bool
    errors: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            'lines': [
                {
                    'description': ln.description,
                    'quantity': ln.quantity,
                    'unit_price': ln.unit_price,
                    'discount': ln.discount,
                    'tax_rate': ln.tax_rate,
                    'tax_id': ln.tax_id,
                    'product_id': ln.product_id,
                    'subtotal': ln.subtotal,
                    'tax_amount': ln.tax_amount,
                    'total': ln.total,
                    'declared_total': ln.declared_total,
                }
                for ln in self.lines
            ],
            'subtotal': self.subtotal,
            'tax_total': self.tax_total,
            'grand_total': self.grand_total,
            'declared_subtotal': self.declared_subtotal,
            'declared_tax': self.declared_tax,
            'declared_total': self.declared_total,
            'difference': self.difference,
            'within_tolerance': self.within_tolerance,
            'errors': list(self.errors),
            'warnings': list(self.warnings),
        }


class _TaxLike:
    def __init__(self, rate: float):
        self.percentage = float(rate or 0)
        self.price_included = False
        self.type = 'excluded'
        self.computation = 'percent'
        self.amount_fixed = 0.0


def recompute(data: SalesImportData, *, tax_resolver=None) -> TotalsResult:
    errors: list[str] = []
    warnings: list[str] = []
    computed: list[LineCompute] = []
    subtotal = Decimal('0.00')
    tax_total = Decimal('0.00')
    grand = Decimal('0.00')

    if not data.lines:
        errors.append('No se reconocieron líneas de venta en el archivo.')

    for raw in data.lines:
        ln = raw if isinstance(raw, SalesImportLine) else SalesImportLine.from_dict(raw)
        qty = float(ln.quantity or 0)
        price = max(0.0, float(ln.unit_price or 0) - float(ln.discount or 0))
        if qty <= 0:
            errors.append(f'La línea «{ln.description}» no tiene cantidad válida.')
            continue
        tax_obj = None
        tax_id = ln.tax_id
        rate = ln.tax_rate
        if tax_resolver is not None:
            tax_id, tax_obj = tax_resolver(rate)
        elif rate is not None:
            tax_obj = _TaxLike(rate)
        s, t, tx = compute_line_amounts(qty, price, tax_obj)
        s_m, t_m, tx_m = as_money(s), as_money(t), as_money(tx)
        subtotal += s_m
        tax_total += tx_m
        grand += t_m
        computed.append(
            LineCompute(
                description=ln.description,
                quantity=qty,
                unit_price=float(ln.unit_price or 0),
                discount=float(ln.discount or 0),
                tax_rate=rate,
                tax_id=tax_id,
                product_id=ln.product_id,
                subtotal=float(s_m),
                tax_amount=float(tx_m),
                total=float(t_m),
                declared_total=ln.declared_total,
            )
        )

    declared_total = data.declared_total
    difference = 0.0
    within = True
    if declared_total is not None and computed:
        difference = float(as_money(grand) - as_money(declared_total))
        within = abs(as_money(difference)) <= money_tolerance()
        if not within:
            errors.append(
                'El total calculado por EN1 no coincide con el total declarado en el archivo.'
            )

    if data.declared_subtotal is not None and computed:
        dsub = abs(as_money(subtotal) - as_money(data.declared_subtotal))
        if dsub > money_tolerance():
            warnings.append('El subtotal declarado en el XLS no coincide con el recálculo EN1.')
    if data.declared_tax is not None and computed:
        dtax = abs(as_money(tax_total) - as_money(data.declared_tax))
        if dtax > money_tolerance():
            warnings.append('El ITBMS declarado en el XLS no coincide con el recálculo EN1.')

    return TotalsResult(
        lines=computed,
        subtotal=float(as_money(subtotal)),
        tax_total=float(as_money(tax_total)),
        grand_total=float(as_money(grand)),
        declared_subtotal=data.declared_subtotal,
        declared_tax=data.declared_tax,
        declared_total=data.declared_total,
        difference=difference,
        within_tolerance=within,
        errors=errors,
        warnings=warnings,
    )
