"""Perfil versionado: factura Panameña tipo FACTURA N.xlsx (layout visual + tabla)."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from nodeone.modules.sales.xls_import.types import SalesImportData, SalesImportLine
from nodeone.modules.sales.xls_import.workbook import cell_number, cell_percent, cell_text

PROFILE_CODE = 'panama_factura_layout'
PROFILE_VERSION = 1
PROFILE_LABEL = 'Factura Excel Panamá (layout v1)'

_FACTURA_FILE = re.compile(r'factura[\s._-]*(\d+)', re.I)
_FACTURA_INLINE = re.compile(r'factura\s*(?:n[°ºo]\.?)?\s*[:#]?\s*0*(\d+)', re.I)
_RUC = re.compile(r'(\d{1,20}(?:-\d+){0,4})')
_DV_NEAR = re.compile(r'(?:dv|d\.?v\.?)[:\s-]*(\d{1,2})\b', re.I)
_EMAIL = re.compile(r'[^@\s]+@[^@\s]+\.[^@\s]+')
_DATE_INLINE = re.compile(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})')

_LABEL_FACTURA = re.compile(r'^(factura|n[uú]mero|n[°ºo]\.?|no\.?)$', re.I)
_LABEL_FECHA = re.compile(r'^(fecha|facturado(\s+el)?)$', re.I)
_LABEL_CLIENTE = re.compile(r'^(cliente|nombre|raz[oó]n\s*social)$', re.I)
_LABEL_RUC = re.compile(r'^(ruc|nit|tax[\s-]?id|identificaci[oó]n)$', re.I)
_LABEL_DV = re.compile(r'^(dv|d\.?v\.?)$', re.I)
_LABEL_DIR = re.compile(r'^(direcci[oó]n|address)$', re.I)
_LABEL_TEL = re.compile(r'^(tel[eé]fono|phone|celular|m[oó]vil)$', re.I)
_LABEL_EMAIL = re.compile(r'^(e-?mail|correo)$', re.I)
_LABEL_SUB = re.compile(r'sub[\s-]*total|base imponible', re.I)
_LABEL_TAX = re.compile(r'\bitbms\b|\biva\b|impuesto', re.I)
_LABEL_TOTAL_PAY = re.compile(r'total\s*a\s*pagar|gran\s*total|total\s*factura', re.I)
_LABEL_QTY_TOTAL = re.compile(r'^total(\s*cantidad)?$', re.I)
_STOP_FOOTER = re.compile(r'para realizar pagos|condiciones|cuenta bancaria', re.I)

_HEAD_DESC = re.compile(r'descripci[oó]n|detalle|concepto|item', re.I)
_HEAD_QTY = re.compile(r'^cant|^qty|^quantity', re.I)
_HEAD_PRICE = re.compile(r'precio|p\.?\s*unit|unitario|^price', re.I)
_HEAD_DISC = re.compile(r'descuento|^desc\.?$', re.I)
_HEAD_TAX = re.compile(r'itbms|iva|impuesto', re.I)
_HEAD_TOTAL = re.compile(r'total|importe', re.I)


def filename_external_number(filename: str) -> str | None:
    m = _FACTURA_FILE.search(filename or '')
    return m.group(1) if m else None


def detect_score(filename: str, grid: list[list[Any]]) -> int:
    score = 0
    if filename_external_number(filename):
        score += 25
    blob = ' '.join(cell_text(c) for row in grid[:50] for c in row[:12]).lower()
    if 'itbms' in blob:
        score += 20
    if 'ruc' in blob:
        score += 15
    if 'factura' in blob:
        score += 15
    if 'p. unitario' in blob or 'p.total' in blob or 'p. total' in blob:
        score += 15
    if 'facturado' in blob:
        score += 10
    if any(_HEAD_DESC.search(cell_text(c)) for row in grid for c in row[:10]):
        score += 20
    return score


def parse(filename: str, grid: list[list[Any]]) -> SalesImportData:
    header_idx, mapping = _find_header_row(grid)
    lines: list[SalesImportLine] = []
    if header_idx is not None:
        lines = _parse_lines(grid, header_idx, mapping)
    if not lines:
        lines, inferred_at = _parse_lines_inferred(grid)
        if inferred_at is not None:
            header_idx = inferred_at
    fields = _header_fields(grid, stop_row=header_idx if header_idx is not None else len(grid))
    totals = _footer_totals(grid, start_row=(header_idx + 1) if header_idx is not None else 0)
    _apply_footer_tax_to_lines(lines, totals)
    ext = fields.get('external_number') or filename_external_number(filename)
    tax_id, dv = _split_ruc_dv(fields.get('tax_id'), fields.get('dv'))
    tax_id = _clean_placeholder_ruc(tax_id)
    return SalesImportData(
        external_number=ext,
        date=fields.get('date'),
        customer=fields.get('customer'),
        tax_id=tax_id,
        dv=dv,
        address=fields.get('address'),
        phone=fields.get('phone'),
        email=fields.get('email'),
        currency='USD',
        lines=lines,
        declared_subtotal=totals.get('subtotal'),
        declared_tax=totals.get('tax'),
        declared_total=totals.get('total'),
        profile=PROFILE_CODE,
        profile_version=PROFILE_VERSION,
    )


def _norm_label(value: Any) -> str:
    text = cell_text(value).lower()
    text = re.sub(r'[:\s]+$', '', text)
    return text.strip()


def _split_inline(cell: Any) -> tuple[str, str | None]:
    text = cell_text(cell)
    if ':' in text:
        left, right = text.split(':', 1)
        return _norm_label(left), right.strip() or None
    return _norm_label(text), None


def _find_header_row(grid: list[list[Any]]) -> tuple[int | None, dict[str, int]]:
    best: tuple[int, int, dict[str, int]] | None = None
    for r, row in enumerate(grid):
        own = _mapping_from_rows(row, None)
        if 'desc' not in own:
            continue
        nxt = grid[r + 1] if r + 1 < len(grid) else None
        if nxt is not None and _row_has_amounts(nxt):
            nxt = None
        mapping = _mapping_from_rows(row, nxt)
        hits = len(mapping)
        if hits >= 2 and 'desc' in mapping:
            if best is None or hits > best[0]:
                best = (hits, r, mapping)
    if not best:
        return None, {}
    idx, mapping = best[1], best[2]
    if 'qty' in mapping:
        mapping.setdefault('price', int(mapping['qty']) + 1)
        if 'tax' not in mapping:
            mapping.setdefault('total', int(mapping['price']) + 1)
        else:
            mapping.setdefault('total', int(mapping['tax']) + 1)
    return idx, mapping


def _row_has_amounts(row: list[Any]) -> bool:
    n = 0
    for cell in row:
        if cell_number(cell) is not None:
            n += 1
    return n >= 2


def _mapping_from_rows(row: list[Any], extra: list[Any] | None) -> dict[str, int]:
    mapping: dict[str, int] = {}
    width = max(len(row), len(extra) if extra else 0)
    for c in range(width):
        parts = []
        if c < len(row):
            parts.append(cell_text(row[c]))
        if extra is not None and c < len(extra):
            parts.append(cell_text(extra[c]))
        t = _norm_label(' '.join(p for p in parts if p))
        if not t:
            continue
        if 'desc' not in mapping and _HEAD_DESC.search(t):
            mapping['desc'] = c
        elif 'qty' not in mapping and _HEAD_QTY.search(t):
            mapping['qty'] = c
        elif 'price' not in mapping and _HEAD_PRICE.search(t):
            mapping['price'] = c
        elif 'discount' not in mapping and _HEAD_DISC.search(t):
            mapping['discount'] = c
        elif 'tax' not in mapping and _HEAD_TAX.search(t):
            mapping['tax'] = c
        elif 'total' not in mapping and _HEAD_TOTAL.search(t) and 'sub' not in t:
            mapping['total'] = c
    return mapping


def _parse_lines(grid: list[list[Any]], header_idx: int, mapping: dict[str, int]) -> list[SalesImportLine]:
    out: list[SalesImportLine] = []
    for row in grid[header_idx + 1 :]:
        desc = cell_text(row[mapping['desc']]) if mapping.get('desc', 99) < len(row) else ''
        joined = ' '.join(cell_text(c) for c in row)
        if _STOP_FOOTER.search(joined):
            break
        if not desc:
            if out and all(cell_text(c) == '' for c in row):
                break
            continue
        if _is_totals_label(desc):
            break
        if out and _is_totals_label(joined):
            break
        qty = cell_number(row[mapping['qty']]) if mapping.get('qty', 99) < len(row) else None
        price = cell_number(row[mapping['price']]) if mapping.get('price', 99) < len(row) else None
        disc = cell_number(row[mapping['discount']]) if mapping.get('discount', 99) < len(row) else None
        tax_raw = cell_number(row[mapping['tax']]) if mapping.get('tax', 99) < len(row) else None
        declared = cell_number(row[mapping['total']]) if mapping.get('total', 99) < len(row) else None
        if (qty is None or qty == 0) and not (price or declared):
            continue
        qty, price = _normalize_qty_price(qty, price, declared, tax_raw)
        if qty <= 0 and not declared:
            continue
        rate = _tax_rate_from_cell(tax_raw, qty, price)
        out.append(
            SalesImportLine(
                description=desc[:500],
                quantity=qty,
                unit_price=price,
                discount=float(disc or 0),
                tax_rate=rate,
                declared_total=declared,
            )
        )
    return out


def _parse_lines_inferred(grid: list[list[Any]]) -> tuple[list[SalesImportLine], int | None]:
    """Filas tipo: texto + cantidad + precio + total (factura impresa sin cabecera clara)."""
    start = 0
    for i, row in enumerate(grid):
        blob = ' '.join(cell_text(c) for c in row).lower()
        if 'detalle' in blob or 'cantidad' in blob or 'unitario' in blob:
            start = i + 1
            break
    out: list[SalesImportLine] = []
    data_at: int | None = None
    for r, row in enumerate(grid[start:], start):
        joined = ' '.join(cell_text(c) for c in row)
        if _STOP_FOOTER.search(joined) or _is_totals_label(joined):
            break
        texts = [cell_text(c) for c in row]
        num_vals = [n for n in (cell_number(c) for c in row) if n is not None]
        desc = next((t for t in texts if t and cell_number(t) is None and not _is_totals_label(t)), '')
        if not desc or len(num_vals) < 2:
            if out and all(not t for t in texts):
                break
            continue
        if len(num_vals) >= 3:
            qty, price, declared = num_vals[-3], num_vals[-2], num_vals[-1]
        else:
            qty, price, declared = num_vals[0], num_vals[1], None
        if data_at is None:
            data_at = r - 1 if r > 0 else r
        qty, price = _normalize_qty_price(qty, price, declared, None)
        out.append(
            SalesImportLine(
                description=desc[:500],
                quantity=qty,
                unit_price=price,
                declared_total=declared,
            )
        )
    return out, data_at


def _normalize_qty_price(
    qty: float | None,
    price: float | None,
    declared: float | None,
    tax_raw: float | None = None,
) -> tuple[float, float]:
    q = float(qty or 0)
    p = float(price or 0)
    if q <= 0 and declared and p:
        implied = round(float(declared) / p, 6)
        q = implied if implied > 0 else 1.0
    elif q <= 0 and declared:
        q = 1.0
        p = float(declared)
    elif q <= 0:
        q = 1.0
    # Si hay columna de impuesto, P. Total suele incluir ITBMS: no reescribir el unitario.
    if tax_raw is None and q > 0 and declared is not None and p:
        computed = q * p
        if abs(computed - float(declared)) > 0.05:
            p = round(float(declared) / q, 6)
    return q, p


def _tax_rate_from_cell(raw: float | None, qty: float, price: float) -> float | None:
    if raw is None:
        return None
    if raw in (0, 7, 10, 15) or (0 <= raw <= 15 and float(raw).is_integer()):
        return float(raw)
    base = qty * price
    if base > 0 and raw > 15:
        derived = round((raw / base) * 100.0, 2)
        if abs(derived - 7) < 0.2:
            return 7.0
        if abs(derived - 10) < 0.2:
            return 10.0
        if abs(derived - 0) < 0.2:
            return 0.0
        return derived
    return float(raw)


def _is_totals_label(text: str) -> bool:
    t = text.lower().strip()
    if _LABEL_QTY_TOTAL.match(t) and 'pagar' not in t:
        return True
    return bool(_LABEL_SUB.search(t) or _LABEL_TAX.search(t) or _LABEL_TOTAL_PAY.search(t))


def _neighbor(grid: list[list[Any]], r: int, c: int) -> Any:
    row = grid[r]
    for nc in range(c + 1, min(len(row), c + 8)):
        if cell_text(row[nc]):
            return row[nc]
    if r + 1 < len(grid) and c < len(grid[r + 1]) and cell_text(grid[r + 1][c]):
        if not _looks_like_label(grid[r + 1][c]):
            return grid[r + 1][c]
    return None


def _looks_like_label(value: Any) -> bool:
    t = _norm_label(value)
    return bool(
        _LABEL_FACTURA.search(t)
        or _LABEL_FECHA.search(t)
        or _LABEL_CLIENTE.search(t)
        or _LABEL_RUC.search(t)
        or _LABEL_DV.search(t)
        or _LABEL_DIR.search(t)
        or _LABEL_TEL.search(t)
        or _LABEL_EMAIL.search(t)
    )


def _header_fields(grid: list[list[Any]], stop_row: int) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    limit = min(stop_row, len(grid))
    for r in range(limit):
        row = grid[r]
        for c, cell in enumerate(row):
            inline_label, inline_val = _split_inline(cell)
            t = inline_label
            if not t:
                continue
            m_fac = _FACTURA_INLINE.search(cell_text(cell))
            if 'external_number' not in out and m_fac:
                out['external_number'] = m_fac.group(1)
                continue
            val = inline_val if inline_val else _neighbor(grid, r, c)
            text = cell_text(val) if val is not None else ''
            if 'external_number' not in out and _LABEL_FACTURA.search(t):
                num = cell_number(val)
                out['external_number'] = str(int(num)) if num is not None and num == int(num) else (text or None)
            elif 'date' not in out and _LABEL_FECHA.search(t):
                out['date'] = _as_date(val) or _as_date(inline_val) or _first_date_in(cell_text(cell))
            elif 'customer' not in out and _LABEL_CLIENTE.search(t):
                out['customer'] = text or inline_val
            elif 'tax_id' not in out and _LABEL_RUC.search(t):
                out['tax_id'] = text or inline_val
            elif 'dv' not in out and _LABEL_DV.search(t):
                out['dv'] = text or inline_val
            elif 'address' not in out and _LABEL_DIR.search(t):
                out['address'] = text or inline_val
            elif 'phone' not in out and _LABEL_TEL.search(t):
                out['phone'] = text or inline_val
            elif 'email' not in out and _LABEL_EMAIL.search(t):
                out['email'] = text or inline_val
    if not out.get('date'):
        blob = ' '.join(cell_text(c) for row in grid[:limit] for c in row)
        out['date'] = _first_date_in(blob)
    if not out.get('email'):
        blob = ' '.join(cell_text(c) for row in grid[:limit] for c in row)
        m = _EMAIL.search(blob)
        if m:
            out['email'] = m.group(0)
    if not out.get('external_number'):
        blob = ' '.join(cell_text(c) for row in grid[:limit] for c in row)
        m = _FACTURA_INLINE.search(blob)
        if m:
            out['external_number'] = m.group(1)
    return out


def _first_date_in(text: str) -> str | None:
    m = _DATE_INLINE.search(text or '')
    if not m:
        return None
    return _as_date(m.group(1))


def _as_date(value: Any) -> str | None:
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = cell_text(value)
    if not text:
        return None
    m = _DATE_INLINE.search(text)
    if m:
        text = m.group(1)
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y', '%d/%m/%y'):
        try:
            return datetime.strptime(text[:10], fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _footer_totals(grid: list[list[Any]], start_row: int) -> dict[str, float | None]:
    found: dict[str, float | None] = {}
    tax_rate = None
    qty_total_candidate = None
    loose_total = None
    for row in grid[start_row:]:
        joined = ' '.join(cell_text(c) for c in row)
        if _STOP_FOOTER.search(joined):
            break
        t = joined.lower()
        nums = [cell_number(c) for c in row]
        nums = [n for n in nums if n is not None]
        if _LABEL_SUB.search(t):
            if nums:
                found['subtotal'] = nums[-1]
            continue
        if _LABEL_TAX.search(t) and 'sub' not in t:
            has_pct = '%' in joined
            if has_pct:
                percents = [cell_percent(c) for c in row]
                percents = [p for p in percents if p is not None]
                tax_rate = percents[-1] if percents else tax_rate
                money_vals = [n for n in nums if tax_rate is None or abs(n - float(tax_rate)) > 0.05]
                money_vals = [n for n in money_vals if n > 15]
                found['tax'] = money_vals[-1] if money_vals else 0.0
            elif nums:
                n = nums[-1]
                if 0 < n <= 1:
                    tax_rate = round(n * 100.0, 4)
                    found['tax'] = 0.0
                else:
                    found['tax'] = n
            continue
        if _LABEL_TOTAL_PAY.search(t):
            if nums:
                found['total'] = nums[-1]
            continue
        if t.strip().startswith('total') and 'pagar' not in t and 'sub' not in t:
            if not nums:
                continue
            n = nums[-1]
            sub = found.get('subtotal')
            if sub is not None:
                if n + 0.05 >= float(sub):
                    found['total'] = n
                elif float(n).is_integer():
                    qty_total_candidate = n
            elif float(n).is_integer() and n < 100000 and len(nums) == 1:
                qty_total_candidate = n
            else:
                loose_total = n
            continue
    if 'total' not in found:
        if loose_total is not None and loose_total != qty_total_candidate:
            found['total'] = loose_total
        elif found.get('subtotal') is not None:
            found['total'] = found['subtotal']
    if found.get('tax') is None and tax_rate is not None:
        found['tax'] = 0.0
    found['tax_rate'] = tax_rate
    return found


def _apply_footer_tax_to_lines(lines: list[SalesImportLine], totals: dict[str, float | None]) -> None:
    sub = totals.get('subtotal')
    grand = totals.get('total')
    rate = totals.get('tax_rate')
    tax_amt = totals.get('tax')
    tax_in_total = (
        sub is not None
        and grand is not None
        and abs(float(grand) - float(sub)) > 0.05
    )
    if not tax_in_total:
        if tax_amt in (None, 0, 0.0) and rate:
            totals['tax'] = 0.0
        for ln in lines:
            if ln.tax_rate is None:
                ln.tax_rate = 0.0
        return
    if rate:
        for ln in lines:
            if ln.tax_rate is None:
                ln.tax_rate = float(rate)


def _clean_placeholder_ruc(tax_id: str | None) -> str | None:
    raw = (tax_id or '').strip()
    if not raw:
        return None
    digits = re.sub(r'\D', '', raw)
    if digits and set(digits) <= {'0'}:
        return None
    return raw


def _split_ruc_dv(tax_id: str | None, dv: str | None) -> tuple[str | None, str | None]:
    raw = (tax_id or '').strip()
    dv_out = (dv or '').strip() or None
    if not dv_out and raw:
        m = _DV_NEAR.search(raw)
        if m:
            dv_out = m.group(1)
            raw = _DV_NEAR.sub('', raw).strip(' -')
    if raw:
        m = _RUC.search(raw.replace(' ', ''))
        raw = m.group(1) if m else raw
    return (raw or None), dv_out
