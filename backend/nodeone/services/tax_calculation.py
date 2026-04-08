"""Cálculo de subtotal / impuesto / total por línea (cotización, factura)."""
from __future__ import annotations

from typing import Any, Optional, Tuple


def price_included(tax: Any) -> bool:
    if tax is None:
        return False
    pi = getattr(tax, 'price_included', None)
    if pi is not None:
        return bool(pi)
    return getattr(tax, 'type', 'excluded') == 'included'


def computation_mode(tax: Any) -> str:
    c = getattr(tax, 'computation', None) or 'percent'
    return c if c in ('percent', 'fixed') else 'percent'


def compute_line_amounts(qty: float, price_unit: float, tax: Optional[Any]) -> Tuple[float, float, float]:
    """
    Retorna (subtotal_sin_impuesto_en_base, total_con_impuesto, monto_impuesto).
    price_unit es el precio unitario tal como lo ingresa el usuario (con o sin impuesto según price_included).
    """
    q = float(qty or 0)
    pu = float(price_unit or 0)
    amount = q * pu
    if tax is None:
        return amount, amount, 0.0

    inc = price_included(tax)
    comp = computation_mode(tax)
    rate = float(getattr(tax, 'percentage', 0) or 0)
    fixed = float(getattr(tax, 'amount_fixed', 0) or 0)

    if comp == 'fixed':
        tax_amt = fixed * q
        if inc:
            subtotal = max(0.0, amount - tax_amt)
            total = amount
            return float(subtotal), float(total), float(tax_amt)
        subtotal = amount
        total = amount + tax_amt
        return float(subtotal), float(total), float(tax_amt)

    if inc:
        if rate > 0:
            subtotal = amount / (1.0 + rate / 100.0)
        else:
            subtotal = amount
        total = amount
        tax_amt = total - subtotal
        return float(subtotal), float(total), float(tax_amt)

    tax_amt = amount * (rate / 100.0)
    subtotal = amount
    total = amount + tax_amt
    return float(subtotal), float(total), float(tax_amt)
