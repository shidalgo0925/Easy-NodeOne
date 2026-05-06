"""Tests unitarios: parse_matrix_rows import participantes (A–J)."""

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parents[2]
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from nodeone.modules.events.services.participants_import import (
    ParsedParticipantRow,
    default_import_participant_type,
    default_import_payment_status,
    deserialize_preview,
    parse_matrix_rows,
    serialize_preview,
)


def test_parse_seven_columns_defaults_type_and_payment():
    rows, had_header = parse_matrix_rows(
        [('Juan', '', 'Pérez', '', '123', 'juan@example.com', '555')],
    )
    assert not had_header
    assert len(rows) == 1
    r = rows[0]
    assert not r.errors
    assert r.participant_type_col == ''
    assert r.payment_status_col == ''
    assert default_import_participant_type(r) == 'external'
    assert default_import_participant_type(r, empty_column_fallback='reviewer') == 'reviewer'
    assert default_import_payment_status(r) == 'not_required'


def test_parse_ten_columns_type_payment_notes():
    rows, had_header = parse_matrix_rows(
        [
            (
                'Ana',
                'M.',
                'López',
                '',
                'DOC1',
                'ana@example.com',
                '123',
                'speaker',
                'paid',
                'Nota de prueba',
            ),
        ],
    )
    assert not had_header
    r = rows[0]
    assert not r.errors
    assert r.participant_type_col == 'speaker'
    assert r.payment_status_col == 'paid'
    assert 'Nota de prueba' in r.notes_col


def test_parse_invalid_participant_type():
    rows, _ = parse_matrix_rows(
        [('X', '', 'Y', '', '', '', '', 'tipo_invalido', '', '')],
    )
    assert rows[0].errors


def test_parse_invalid_payment_status():
    rows, _ = parse_matrix_rows(
        [('X', '', 'Y', '', '', 'z@z.com', '', 'reviewer', 'cash_only', '')],
    )
    assert rows[0].errors


def test_serialize_preview_roundtrip_preserves_h_to_j():
    r = ParsedParticipantRow(
        row_index=3,
        first_name='A',
        middle_name='',
        last_name='B',
        second_last_name='',
        document_id='',
        email='a@b.com',
        phone='',
        participant_type_col='staff',
        payment_status_col='paid',
        notes_col='nota',
    )
    back = deserialize_preview(serialize_preview([r]))[0]
    assert back.row_index == 3
    assert back.participant_type_col == 'staff'
    assert back.payment_status_col == 'paid'
    assert back.notes_col == 'nota'


def test_header_row_skipped_with_optional_columns():
    rows, had_header = parse_matrix_rows(
        [
            ('nombre', 'segundo', 'apellido', 'segundo_ap', 'doc', 'email', 'tel', 'tipo', 'pago', 'notas'),
            ('Juan', '', 'Pérez', '', '99', 'j@j.com', '555', 'reviewer', 'not_required', 'ok'),
        ],
    )
    assert had_header
    assert len(rows) == 1
    r = rows[0]
    assert not r.errors
    assert r.first_name == 'Juan'
    assert r.participant_type_col == 'reviewer'
