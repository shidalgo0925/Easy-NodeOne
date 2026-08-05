"""OCC Fase B — Excepciones + umbrales (ADR-025)."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


def _row(**kwargs):
    base = {
        'shift_id': 1,
        'register_ref': 'caja-1',
        'register_name': 'Caja 1',
        'branch_name': 'Sucursal',
        'branch_ref': 'br-1',
        'cashier_name': 'Ana',
        'shift_status': 'closed',
        'sales': 100.0,
        'expected': 100.0,
        'counted': 100.0,
        'variance': 0.0,
        'occ_status': 'ok',
        'occ_status_label': 'Conciliado',
        'orders_count': 1,
        'opened_at': datetime.utcnow() - timedelta(hours=2),
        'closed_at': datetime.utcnow(),
        'detail_url_path': '/admin/eposone/shifts/1',
    }
    base.update(kwargs)
    return base


class TestOccExceptions(unittest.TestCase):
    def test_cash_difference_high(self):
        from nodeone.modules.eposone.occ_service import (
            OCC_SEV_HIGH,
            exceptions_for_shift_row,
        )

        row = _row(occ_status='alert', variance=-5.0, counted=95.0, expected=100.0)
        excs = exceptions_for_shift_row(row)
        self.assertEqual(len(excs), 1)
        self.assertEqual(excs[0]['code'], 'cash_difference')
        self.assertEqual(excs[0]['severity'], OCC_SEV_HIGH)

    def test_cash_difference_critical_ge_20(self):
        from nodeone.modules.eposone.occ_service import (
            OCC_SEV_CRITICAL,
            exceptions_for_shift_row,
        )

        row = _row(occ_status='alert', variance=-25.0, counted=75.0, expected=100.0)
        excs = exceptions_for_shift_row(row)
        self.assertEqual(excs[0]['severity'], OCC_SEV_CRITICAL)

    def test_open_long_shift(self):
        from nodeone.modules.eposone.occ_service import (
            OCC_SEV_HIGH,
            exceptions_for_shift_row,
        )

        now = datetime.utcnow()
        row = _row(
            shift_status='open',
            occ_status='open',
            counted=None,
            variance=None,
            closed_at=None,
            opened_at=now - timedelta(hours=13),
        )
        excs = exceptions_for_shift_row(row, now=now)
        codes = {e['code'] for e in excs}
        self.assertIn('shift_open_long', codes)
        self.assertEqual(
            next(e for e in excs if e['code'] == 'shift_open_long')['severity'],
            OCC_SEV_HIGH,
        )

    def test_open_short_no_exception(self):
        from nodeone.modules.eposone.occ_service import exceptions_for_shift_row

        now = datetime.utcnow()
        row = _row(
            shift_status='open',
            occ_status='open',
            counted=None,
            variance=None,
            closed_at=None,
            opened_at=now - timedelta(hours=3),
        )
        self.assertEqual(exceptions_for_shift_row(row, now=now), [])

    def test_pending_count_warn(self):
        from nodeone.modules.eposone.occ_service import (
            OCC_SEV_MEDIUM,
            exceptions_for_shift_row,
        )

        row = _row(
            shift_status='reconciling',
            occ_status='warn',
            counted=None,
            variance=None,
        )
        excs = exceptions_for_shift_row(row)
        self.assertEqual(excs[0]['code'], 'pending_count')
        self.assertEqual(excs[0]['severity'], OCC_SEV_MEDIUM)


class TestOccFaseBRoutes(unittest.TestCase):
    def test_endpoints_exist(self):
        from nodeone.modules.eposone import routes as r

        self.assertTrue(hasattr(r, 'eposone_occ_excepciones'))
        self.assertTrue(hasattr(r, 'eposone_occ_auditoria'))
        self.assertTrue(hasattr(r, 'eposone_occ_bitacora'))


if __name__ == '__main__':
    unittest.main()
