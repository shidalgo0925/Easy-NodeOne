"""Categorías fiscales PA + cálculo de ITBMS por línea."""

from __future__ import annotations

import unittest

from nodeone.modules.eposone.fiscal_categories import (
    FISCAL_CATEGORY_ITBMS_10,
    FISCAL_CATEGORY_ITBMS_7,
    line_tax_amount,
    normalize_fiscal_category,
    tax_percent_for_category,
)


class TestFiscalCategoriesPA(unittest.TestCase):
    def test_alcohol_is_10(self):
        self.assertEqual(tax_percent_for_category(FISCAL_CATEGORY_ITBMS_10), 10.0)
        self.assertEqual(normalize_fiscal_category('alcohol'), FISCAL_CATEGORY_ITBMS_10)
        self.assertEqual(normalize_fiscal_category('LICOR'), FISCAL_CATEGORY_ITBMS_10)

    def test_general_is_7(self):
        self.assertEqual(tax_percent_for_category(FISCAL_CATEGORY_ITBMS_7), 7.0)
        self.assertEqual(tax_percent_for_category(None), 7.0)

    def test_line_tax_alcohol(self):
        # B/.10.00 × 10% = 1.00
        self.assertEqual(
            line_tax_amount(qty=1, unit_price=10.0, fiscal_category='ITBMS_10'),
            1.0,
        )

    def test_line_tax_general(self):
        # B/.20.00 × 7% = 1.40
        self.assertEqual(
            line_tax_amount(qty=2, unit_price=10.0, fiscal_category='ITBMS_7'),
            1.4,
        )

    def test_exento(self):
        self.assertEqual(
            line_tax_amount(qty=1, unit_price=50.0, fiscal_category='EXENTO'),
            0.0,
        )


if __name__ == '__main__':
    unittest.main()
