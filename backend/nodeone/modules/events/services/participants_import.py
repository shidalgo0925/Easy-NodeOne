"""Importación de participantes desde Excel.

Columnas A–G (revisores típicos): nombres, documento, email, teléfono.
Opcional **H, I, J**: tipo participante, estado de pago, notas (plan A.4).

Valores por defecto si faltan H–J en import «revisores»: tipo reviewer, pago not_required.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_PAYMENT_ALLOWED = frozenset({'pending', 'paid', 'complimentary', 'waived', 'not_required'})
_TYPE_ALLOWED = frozenset({'external', 'reviewer', 'member', 'invited', 'speaker', 'staff'})


def _normalize_spaces(value: str) -> str:
    value = (value or '').strip()
    return ' '.join(value.split()) if value else ''


def _normalize_name_cell(value: str) -> str:
    """Trata puntos y guiones sueltos como vacío (listas revisores en Word/Excel)."""
    v = _normalize_spaces(value)
    if v in ('.', '-', '—', '–', 'N/A', 'n/a', 'NA', 'S/N', 's/n'):
        return ''
    return v


@dataclass
class ParsedParticipantRow:
    row_index: int
    first_name: str
    middle_name: str
    last_name: str
    second_last_name: str
    document_id: str
    email: str
    phone: str
    participant_type_col: str = ''
    payment_status_col: str = ''
    notes_col: str = ''
    errors: list[str] = field(default_factory=list)
    skip: bool = False

    def full_name(self) -> str:
        return ' '.join(
            p
            for p in (
                self.first_name,
                self.middle_name,
                self.last_name,
                self.second_last_name,
            )
            if p
        ).strip()


def _cell(row: tuple[Any, ...], idx: int) -> str:
    if idx >= len(row) or row[idx] is None:
        return ''
    val = row[idx]
    if isinstance(val, float) and math.isnan(val):
        return ''
    if isinstance(val, float):
        if val == int(val):
            return str(int(val))
        return str(val).strip()
    return str(val).strip()


def _looks_like_header(cells: list[str]) -> bool:
    joined = ' '.join(cells).lower()
    if any(
        w in joined
        for w in (
            'nombre',
            'apellido',
            'email',
            'documento',
            'teléfono',
            'telefono',
            'cedula',
            'cédula',
            'tipo',
            'participante',
            'pago',
            'notas',
        )
    ):
        return True
    # No usar «mail» suelto: dispara falso positivo en hotmail.com / gmail.com.
    if any(w in joined for w in ('first', 'last', 'phone', 'document', 'payment', 'notes')):
        return True
    if re.search(r'\b(e-?mail|correo)\b', joined):
        return True
    if re.search(r'\bnombre\b', joined) and re.search(r'\b(apellido|email|documento)\b', joined):
        return True
    return False


def _is_skippable_leading_row(base: list[str]) -> bool:
    """Filas de título o separadores antes de los datos (p. ej. «LISTA PARA CERTIFICADOS…»)."""
    if not any(base):
        return True
    has_name = bool(base[0] or base[2])
    has_email = bool(base[5])
    if has_name and has_email:
        return False
    if base[0] and not base[2] and not base[5]:
        return True
    return not has_name and not has_email


def _header_probe_cells(first_row: tuple[Any, ...]) -> list[str]:
    """Primeras hasta 10 columnas para detectar cabecera."""
    out = []
    for i in range(min(10, len(first_row) if first_row else 0)):
        out.append(_normalize_spaces(_cell(first_row or (), i)))
    while len(out) < 10:
        out.append('')
    return out


def parse_matrix_rows(raw_rows: list[tuple[Any, ...]]) -> tuple[list[ParsedParticipantRow], bool]:
    rows_out: list[ParsedParticipantRow] = []
    if not raw_rows:
        return [], False
    first = raw_rows[0]
    probe = _header_probe_cells(first)
    had_header = _looks_like_header(probe[:7])
    data_rows = list(raw_rows[1:]) if had_header else list(raw_rows)

    start_idx = 2 if had_header else 1
    for offset, row in enumerate(data_rows):
        ri = start_idx + offset
        base = [_normalize_name_cell(_cell(row, i) if row else '') for i in range(7)]
        if _is_skippable_leading_row(base):
            continue
        if not any(base):
            continue
        pt_extra = _normalize_spaces(_cell(row, 7) if row else '')
        pay_extra = _normalize_spaces(_cell(row, 8) if row else '').lower()
        notes_extra = _normalize_spaces(_cell(row, 9) if row else '')
        pr = ParsedParticipantRow(
            row_index=ri,
            first_name=base[0],
            middle_name=base[1],
            last_name=base[2],
            second_last_name=base[3],
            document_id=base[4],
            email=base[5].lower(),
            phone=base[6],
            participant_type_col=pt_extra[:50],
            payment_status_col=pay_extra[:50],
            notes_col=notes_extra[:2000] if notes_extra else '',
        )
        if not pr.first_name:
            pr.errors.append('Falta primer nombre')
        if not pr.last_name:
            pr.errors.append('Falta primer apellido')
        if pr.email and not _EMAIL_RE.match(pr.email):
            pr.errors.append('Email inválido')
        if pr.participant_type_col:
            t = pr.participant_type_col.strip().lower().replace(' ', '_')
            if t not in _TYPE_ALLOWED:
                pr.errors.append(f'Tipo participante no válido: use {_TYPE_ALLOWED}')
            else:
                pr.participant_type_col = t
        if pr.payment_status_col:
            if pr.payment_status_col not in _PAYMENT_ALLOWED:
                pr.errors.append(f'Estado de pago no válido: use {_PAYMENT_ALLOWED}')
        rows_out.append(pr)
    return rows_out, had_header


def parse_workbook_rows(sheet) -> tuple[list[ParsedParticipantRow], bool]:
    raw_rows = [tuple(r) for r in sheet.iter_rows(values_only=True)]
    return parse_matrix_rows(raw_rows)


def serialize_preview(rows: list[ParsedParticipantRow]) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        out.append(
            {
                'row_index': r.row_index,
                'first_name': r.first_name,
                'middle_name': r.middle_name,
                'last_name': r.last_name,
                'second_last_name': r.second_last_name,
                'document_id': r.document_id,
                'email': r.email,
                'phone': r.phone,
                'participant_type_col': r.participant_type_col,
                'payment_status_col': r.payment_status_col,
                'notes_col': r.notes_col,
                'full_name': r.full_name(),
                'errors': list(r.errors),
                'skip': r.skip,
            }
        )
    return out


def deserialize_preview(data: list[dict[str, Any]]) -> list[ParsedParticipantRow]:
    rows = []
    for d in data:
        r = ParsedParticipantRow(
            row_index=int(d['row_index']),
            first_name=d.get('first_name') or '',
            middle_name=d.get('middle_name') or '',
            last_name=d.get('last_name') or '',
            second_last_name=d.get('second_last_name') or '',
            document_id=d.get('document_id') or '',
            email=d.get('email') or '',
            phone=d.get('phone') or '',
            participant_type_col=d.get('participant_type_col') or '',
            payment_status_col=d.get('payment_status_col') or '',
            notes_col=d.get('notes_col') or '',
        )
        r.errors = list(d.get('errors') or [])
        r.skip = bool(d.get('skip'))
        rows.append(r)
    return rows


def participant_duplicate_key(r: ParsedParticipantRow) -> str:
    if r.document_id:
        return f'doc:{r.document_id.strip().lower()}'
    if r.email:
        return f'email:{r.email.strip().lower()}'
    return f'name:{r.full_name().strip().lower()}|phone:{r.phone.strip()}'


def mark_duplicates_within_file(rows: list[ParsedParticipantRow]) -> None:
    seen: dict[str, int] = {}
    for r in rows:
        if r.errors:
            continue
        k = participant_duplicate_key(r)
        if k in seen:
            r.errors.append('Duplicado en el archivo')
            r.skip = True
        else:
            seen[k] = r.row_index


def default_import_participant_type(
    r: ParsedParticipantRow,
    empty_column_fallback: str = 'external',
) -> str:
    """Si la columna H está vacía, usa ``empty_column_fallback`` (§4: external; §29 lista revisores: reviewer)."""
    if r.participant_type_col:
        return r.participant_type_col
    fb = (empty_column_fallback or 'external').strip().lower().replace(' ', '_')
    if fb not in _TYPE_ALLOWED:
        fb = 'external'
    return fb


def default_import_payment_status(r: ParsedParticipantRow) -> str:
    if r.payment_status_col:
        return r.payment_status_col
    return 'not_required'
