"""Tests: variables de fecha desglosadas en plantillas de certificado."""
import sys
import unittest
from datetime import datetime
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from nodeone.services.certificate_template_data import (
    build_certificate_template_data,
    date_parts_to_template_keys,
    split_date_parts,
)


class _FakeEvent:
    name = 'Certificado prueba'
    institution = 'Inst'
    partner_organization = ''
    rector_name = ''
    academic_director_name = ''
    code_prefix = 'MEM'
    duration_hours = None
    start_date = datetime(2025, 3, 10)
    end_date = datetime(2025, 6, 15)
    background_url = ''
    logo_left_url = ''
    logo_right_url = ''
    seal_url = ''
    membership_required_id = None


class TestSplitDateParts(unittest.TestCase):
    def test_iso_date(self):
        p = split_date_parts('2026-06-14')
        self.assertEqual(p['dia'], '14')
        self.assertEqual(p['mes'], 'junio')
        self.assertEqual(p['anio'], '2026')

    def test_empty(self):
        p = split_date_parts('')
        self.assertEqual(p, {'dia': '', 'mes': '', 'anio': ''})

    def test_keys_prefix(self):
        keys = date_parts_to_template_keys('membresia_inicio', '2025-01-05')
        self.assertEqual(keys['dia_membresia_inicio'], '5')
        self.assertEqual(keys['mes_membresia_inicio'], 'enero')
        self.assertEqual(keys['anio_membresia_inicio'], '2025')


class TestBuildCertificateTemplateData(unittest.TestCase):
    def test_legacy_fields_preserved(self):
        data = build_certificate_template_data(
            _FakeEvent(),
            membership_start='2025-01-01',
            membership_end='2026-01-01',
            issue_date=datetime(2026, 6, 14),
        )
        self.assertIn('membership_start', data)
        self.assertIn('issue_date_legal', data)
        self.assertTrue(data['membership_start'])

    def test_split_date_fields_present(self):
        data = build_certificate_template_data(
            _FakeEvent(),
            membership_start='2025-01-01',
            membership_end='2026-01-01',
            issue_date=datetime(2026, 6, 14),
        )
        self.assertEqual(data['dia_emision'], '14')
        self.assertEqual(data['mes_emision'], 'junio')
        self.assertEqual(data['anio_emision'], '2026')
        self.assertEqual(data['dia_membresia_inicio'], '1')
        self.assertEqual(data['mes_membresia_inicio'], 'enero')
        self.assertEqual(data['dia_inicio'], '10')
        self.assertEqual(data['mes_inicio'], 'marzo')
        self.assertEqual(data['dia_fin'], '15')
        self.assertEqual(data['mes_fin'], 'junio')


if __name__ == '__main__':
    unittest.main()
