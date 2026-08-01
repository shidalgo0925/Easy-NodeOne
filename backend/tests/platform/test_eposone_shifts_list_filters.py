"""Filtros del historial de cierres por Caja (BO Turnos)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestShiftsListFilters(unittest.TestCase):
    def test_default_limit_without_filters(self):
        from nodeone.modules.eposone.routes import _shifts_list_filters

        f = _shifts_list_filters()
        self.assertIsNone(f['register_ref'])
        self.assertEqual(f['closed_limit'], 30)
        self.assertIsNone(f['closed_from_utc'])
        self.assertIsNone(f['closed_to_utc'])

    def test_register_raises_limit(self):
        from nodeone.modules.eposone.routes import _shifts_list_filters

        f = _shifts_list_filters(register_ref='  CAJA_01  ')
        self.assertEqual(f['register_ref'], 'CAJA_01')
        self.assertEqual(f['closed_limit'], 100)

    def test_date_bounds_panama(self):
        from nodeone.modules.eposone.routes import _shifts_list_filters

        f = _shifts_list_filters(date_from='2026-08-01', date_to='2026-08-01')
        self.assertEqual(f['date_from'], '2026-08-01')
        self.assertEqual(f['date_to'], '2026-08-01')
        self.assertIsNotNone(f['closed_from_utc'])
        self.assertIsNotNone(f['closed_to_utc'])
        self.assertLess(f['closed_from_utc'], f['closed_to_utc'])
        self.assertEqual(f['closed_limit'], 100)

    def test_invalid_dates_cleared(self):
        from nodeone.modules.eposone.routes import _shifts_list_filters

        f = _shifts_list_filters(date_from='no-es-fecha')
        self.assertIsNone(f['date_from'])
        self.assertIsNone(f['closed_from_utc'])


if __name__ == '__main__':
    unittest.main()
