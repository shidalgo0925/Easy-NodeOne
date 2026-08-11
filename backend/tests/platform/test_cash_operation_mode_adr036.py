"""ADR-036 — cash_operation_mode normalize + custody close gate (unit)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestCashOperationMode(unittest.TestCase):
    def test_normalize(self):
        from nodeone.modules.eposone.cash_operation_mode import (
            CASH_MODE_CHAIN_OF_CUSTODY,
            CASH_MODE_SIMPLE,
            normalize_cash_operation_mode,
        )

        self.assertEqual(normalize_cash_operation_mode(None), CASH_MODE_SIMPLE)
        self.assertEqual(normalize_cash_operation_mode('simple'), CASH_MODE_SIMPLE)
        self.assertEqual(
            normalize_cash_operation_mode('CHAIN_OF_CUSTODY'), CASH_MODE_CHAIN_OF_CUSTODY
        )
        self.assertEqual(normalize_cash_operation_mode('weird'), CASH_MODE_SIMPLE)


class TestCustodyCloseGate(unittest.TestCase):
    def test_close_rejects_non_custodian_in_mode_b(self):
        from nodeone.modules.eposone.cash_shift_http_service import (
            CashShiftHttpError,
            CashShiftHttpService,
        )

        device = SimpleNamespace(organization_id=1, register_ref='REG-1')
        row = MagicMock()
        row.id = 10
        row.organization_id = 1
        row.register_ref = 'REG-1'
        status = 'open'
        row.status = status
        row.cashier_contact_id = 7
        row.custodian_cashier_contact_id = 7
        row.cashier_name = 'A'
        row.custodian_cashier_name = 'A'
        row.opening_balance = 0
        row.opened_at = None
        row.closed_at = None
        row.counted_amount = None
        row.expected_balance = None
        row.closing_balance = None
        row.closed_by_cashier_contact_id = None
        row.client_shift_id = None

        other = MagicMock()
        other.id = 99
        other.display_name = 'B'

        with patch(
            'nodeone.modules.eposone.cash_shift_http_service.CoreCashShift'
        ) as MockShift, patch(
            'nodeone.modules.eposone.cash_shift_http_service.CashierService.require_cashier',
            return_value=other,
        ), patch(
            'nodeone.modules.eposone.cash_operation_mode.is_chain_of_custody',
            return_value=True,
        ), patch(
            'nodeone.modules.eposone.cash_shift_http_service._register_meta',
            return_value=('REG-1', 'Caja'),
        ):
            MockShift.query.filter_by.return_value.first.return_value = row
            with self.assertRaises(CashShiftHttpError) as ctx:
                CashShiftHttpService.close_shift(
                    device, 10, {'cashier_contact_id': 99, 'counted_amount': 10}
                )
            self.assertEqual(ctx.exception.code, 'custody_required')
            self.assertEqual(ctx.exception.http_status, 409)


if __name__ == '__main__':
    unittest.main()
