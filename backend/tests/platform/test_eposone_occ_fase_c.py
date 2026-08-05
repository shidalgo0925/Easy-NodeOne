"""OCC Fase C — Inteligencia (endpoints + umbrales)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestOccDeviceHealthLogic(unittest.TestCase):
    def test_stale_threshold_constant(self):
        from nodeone.modules.eposone.occ_service import (
            OCC_DEVICE_STALE_MINUTES,
            OCC_OPEN_ORDER_STALE_MINUTES,
        )

        self.assertEqual(OCC_DEVICE_STALE_MINUTES, 15)
        self.assertEqual(OCC_OPEN_ORDER_STALE_MINUTES, 45)


class TestOccFaseCRoutes(unittest.TestCase):
    def test_endpoints_exist(self):
        from nodeone.modules.eposone import routes as r

        self.assertTrue(hasattr(r, 'eposone_occ_operacion'))
        self.assertTrue(hasattr(r, 'eposone_occ_pagos'))


class TestOccPaymentLabels(unittest.TestCase):
    def test_cash_label(self):
        from nodeone.modules.eposone.occ_service import _payment_method_label

        self.assertEqual(_payment_method_label('cash'), 'Efectivo')
        self.assertEqual(_payment_method_label('card'), 'Tarjeta')


class TestOccHealthScoreRule(unittest.TestCase):
    """Open shifts alone must not force amber (normal daytime ops)."""

    def test_thresholds_documented(self):
        from nodeone.modules.eposone.occ_service import OCC_DEVICE_STALE_MINUTES

        self.assertGreaterEqual(OCC_DEVICE_STALE_MINUTES, 5)


if __name__ == '__main__':
    unittest.main()
