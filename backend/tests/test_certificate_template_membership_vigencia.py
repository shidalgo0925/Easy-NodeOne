"""Tests: variables de fin de vigencia en plantillas MEM/PLAN."""
import json
import unittest

from nodeone.services.certificate_template_membership_vigencia import (
    ensure_membership_end_variables_in_layout,
)


class TestCertificateTemplateMembershipVigencia(unittest.TestCase):
    def test_adds_fin_variables_from_inicio(self):
        layout = {
            'canvas': {'width': 1024, 'height': 768},
            'elements': [
                {
                    'id': 'var_5',
                    'type': 'variable',
                    'name': 'dia_membresia_inicio',
                    'x': 485,
                    'y': 540,
                    'font_size': 13,
                },
                {
                    'id': 'var_7',
                    'type': 'variable',
                    'name': 'membership_start',
                    'x': 444,
                    'y': 407,
                    'font_size': 16,
                },
            ],
        }
        new_layout, changed = ensure_membership_end_variables_in_layout(layout)
        self.assertTrue(changed)
        names = {
            e['name']
            for e in new_layout['elements']
            if e.get('type') == 'variable'
        }
        self.assertIn('dia_membresia_fin', names)
        self.assertIn('membership_end', names)
        fin_dia = next(e for e in new_layout['elements'] if e['name'] == 'dia_membresia_fin')
        self.assertEqual(fin_dia['y'], 575)
        fin_mem = next(e for e in new_layout['elements'] if e['name'] == 'membership_end')
        self.assertEqual(fin_mem['y'], 432)

    def test_idempotent_when_fin_exists(self):
        layout = {
            'elements': [
                {'type': 'variable', 'name': 'membership_end', 'x': 1, 'y': 2},
            ]
        }
        _, changed = ensure_membership_end_variables_in_layout(layout)
        self.assertFalse(changed)


if __name__ == '__main__':
    unittest.main()
