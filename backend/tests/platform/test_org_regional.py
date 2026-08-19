"""F1 regionalización: parse de números y defaults (sin fiscal)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestParseLocalizedNumber(unittest.TestCase):
    def test_us_format_thousands(self):
        from nodeone.core.regional_format import parse_localized_number

        self.assertAlmostEqual(parse_localized_number('1,234.56', '1,234.56'), 1234.56)
        self.assertAlmostEqual(parse_localized_number('$ 225,509.38', '1,234.56'), 225509.38)
        self.assertAlmostEqual(parse_localized_number('B/. 100.00', '1,234.56'), 100.0)

    def test_eu_format(self):
        from nodeone.core.regional_format import parse_localized_number

        self.assertAlmostEqual(parse_localized_number('1.234,56', '1.234,56'), 1234.56)
        self.assertAlmostEqual(parse_localized_number('1.234,56', '1,234.56'), 1.23456)

    def test_cell_number_respects_context(self):
        from nodeone.modules.sales.xls_import.workbook import (
            cell_number,
            reset_number_format,
            use_number_format,
        )

        tok = use_number_format('1.234,56')
        try:
            self.assertAlmostEqual(cell_number('1.234,56'), 1234.56)
        finally:
            reset_number_format(tok)
        tok = use_number_format('1,234.56')
        try:
            self.assertAlmostEqual(cell_number('1,234.56'), 1234.56)
            self.assertAlmostEqual(cell_number(1234.56), 1234.56)
        finally:
            reset_number_format(tok)


class TestRegionalNavEndpoint(unittest.TestCase):
    def test_format_money_us_and_eu(self):
        from nodeone.core.regional_format import format_money, format_plain_number

        self.assertEqual(format_plain_number(1234.56, number_format='1,234.56', decimals=2), '1,234.56')
        self.assertEqual(format_plain_number(1234.56, number_format='1.234,56', decimals=2), '1.234,56')
        self.assertEqual(
            format_money(1234.56, number_format='1,234.56', symbol='$', symbol_position='before'),
            '$ 1,234.56',
        )
        self.assertEqual(
            format_money(1234.56, number_format='1.234,56', symbol='€', symbol_position='after'),
            '1.234,56 €',
        )
        from nodeone.core.nav_menu import _CONFIG_ORG_ITEMS

        ids = [it.id for it in _CONFIG_ORG_ITEMS]
        self.assertIn('regional', ids)
        item = next(it for it in _CONFIG_ORG_ITEMS if it.id == 'regional')
        self.assertEqual(item.endpoint, 'admin_regional_settings')


if __name__ == '__main__':
    unittest.main()
