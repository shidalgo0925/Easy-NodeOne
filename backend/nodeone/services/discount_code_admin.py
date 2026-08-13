"""Helpers compartidos — admin de DiscountCode (promos producto ETS y legacy)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func

from nodeone.core.platform.product_registry import ProductRegistry, STATUS_ACTIVE
from nodeone.services.discount_codes import generate_discount_code


def list_commercial_products() -> list[dict[str, str]]:
    """Productos ETS activos elegibles para promos (excluye shell en1)."""
    items = ProductRegistry.list(status=STATUS_ACTIVE)
    out: list[dict[str, str]] = []
    for p in items:
        code = (p.code or '').strip().lower()
        if not code or code == 'en1':
            continue
        out.append({'code': code, 'name': p.name or code})
    return sorted(out, key=lambda x: x['name'].lower())


def product_codes_query(M):
    """Códigos de descuento con alcance producto (plataforma)."""
    q = M.DiscountCode.query
    if hasattr(M.DiscountCode, 'product_codes'):
        return q.filter(
            M.db.or_(
                M.DiscountCode.applies_to == 'products',
                M.DiscountCode.product_codes.isnot(None),
            )
        )
    return q.filter(M.DiscountCode.applies_to == 'products')


def normalize_product_codes(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = [x.strip() for x in raw.split(',') if x.strip()]
    if not isinstance(raw, (list, tuple)):
        return []
    known = {p['code'] for p in list_commercial_products()}
    out: list[str] = []
    for item in raw:
        code = str(item).strip().lower()
        if code and code in known and code not in out:
            out.append(code)
    return out


def parse_optional_dates(start_date_str: str | None, end_date_str: str | None) -> tuple[datetime | None, datetime | None]:
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
    if start_date and end_date and start_date > end_date:
        raise ValueError('La fecha de inicio debe ser anterior a la de fin')
    return start_date, end_date


def validate_discount_value(discount_type: str, value: float) -> str | None:
    if value <= 0:
        return 'El valor del descuento debe ser mayor a 0'
    if discount_type == 'percentage' and value > 100:
        return 'El porcentaje no puede ser mayor a 100%'
    return None


def resolve_discount_code(
    M,
    *,
    code_input: str,
    generate_auto: bool,
    prefix: str,
    length: int = 8,
) -> tuple[str | None, str | None]:
    """Resuelve código manual o autogenerado. Retorna (code, error)."""
    if generate_auto:
        return generate_discount_code(prefix=prefix, length=length), None
    code = (code_input or '').strip().upper()
    if not code:
        return None, 'El código es requerido'
    if M.DiscountCode.query.filter(func.lower(M.DiscountCode.code) == code.lower()).first():
        return None, 'Este código ya existe'
    return code, None


def serialize_product_discount_row(row) -> dict[str, Any]:
    return {
        'id': row.id,
        'code': row.code,
        'name': row.name,
        'description': row.description,
        'discount_type': row.discount_type,
        'value': row.value,
        'product_codes': row.get_product_codes_list(),
        'start_date': row.start_date.isoformat() if row.start_date else None,
        'end_date': row.end_date.isoformat() if row.end_date else None,
        'max_uses_total': row.max_uses_total,
        'max_uses_per_user': row.max_uses_per_user,
        'is_active': row.is_active,
        'current_uses': row.current_uses,
    }
