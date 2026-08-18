"""ADR-EN1-EP1 — ciclo TEST/OPERATIONAL, handoff de dinero, catalog INACTIVE."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestOpsLifecycleNormalize(unittest.TestCase):
    def test_normalize_lifecycle_and_handoff(self):
        from nodeone.modules.eposone.ops_lifecycle import (
            catalog_sync_status,
            normalize_money_handoff_mode,
            normalize_ops_lifecycle,
        )

        self.assertEqual(normalize_ops_lifecycle(None), 'TEST')
        self.assertEqual(normalize_ops_lifecycle('operational'), 'OPERATIONAL')
        self.assertEqual(normalize_money_handoff_mode('CHAIN_OF_CUSTODY'), 'CHAIN_OF_CUSTODY')
        self.assertEqual(normalize_money_handoff_mode('nope'), 'SIMPLE')
        self.assertEqual(catalog_sync_status('active'), 'ACTIVE')
        self.assertEqual(catalog_sync_status('inactive'), 'INACTIVE')

    def test_cannot_leave_operational(self):
        from nodeone.core.commerce.order import OrderValidationError
        from nodeone.modules.eposone.settings_service import EposoneSettingsService

        row = MagicMock()
        row.organization_id = 8
        row.default_currency = 'USD'
        row.kds_auto_enqueue = True
        row.delivery_auto_create = True
        row.fiscal_on_payment = False
        row.supervisor_approval_required = True
        row.trial_days_default = 15
        row.trial_start_policy = 'on_first_provision'
        row.provisioning_code_ttl_minutes = 30
        row.offline_grace_days = 7
        row.cash_operation_mode = 'SIMPLE'
        row.money_handoff_mode = 'SIMPLE'
        row.operational_lifecycle = 'OPERATIONAL'
        row.test_session_id = None

        with patch('nodeone.modules.eposone.settings_service.EposoneSettings') as mock_set, patch(
            'app.db'
        ):
            mock_set.query.filter_by.return_value.first.return_value = row
            with self.assertRaises(OrderValidationError) as ctx:
                EposoneSettingsService.update_settings(8, operational_lifecycle='TEST')
            self.assertIn('cannot_leave_operational', str(ctx.exception))

    def test_product_delete_blocked_when_movements(self):
        from nodeone.core.master.constants import MasterDataError
        from nodeone.core.master.product import CoreProductService

        with patch.object(CoreProductService, 'has_operational_usage', return_value=True):
            with patch('nodeone.core.master.product.CoreProduct') as mock_p, patch('app.db'):
                mock_p.query.filter_by.return_value.first.return_value = MagicMock()
                with self.assertRaises(MasterDataError) as ctx:
                    CoreProductService.delete(8, 'SKU-1')
                self.assertEqual(str(ctx.exception), 'product_has_movements')

    def test_handoff_confirm_idempotent(self):
        from nodeone.modules.eposone.money_handoff_service import MoneyHandoffService
        from nodeone.modules.eposone.ops_lifecycle import HANDOFF_CONFIRMED

        row = MagicMock()
        row.id = 1
        row.organization_id = 8
        row.client_handoff_id = 'h1'
        row.status = HANDOFF_CONFIRMED
        row.expected_amount = 50
        row.received_amount = 50
        row.difference_amount = 0
        row.other_tender_amount = 0
        row.order_refs_json = '[]'
        row.cashier_contact_id = 3
        row.cashier_name = 'Ana'
        row.shift_id = 9
        row.register_ref = 'caja-1'
        row.received_by_label = 'Caja'
        row.received_at = None
        row.reversed_by_label = None
        row.reversed_at = None
        row.reverse_reason = None
        row.is_test = True
        row.test_session_id = 't1'
        row.created_at = None

        with patch('nodeone.modules.eposone.money_handoff_service.EposoneMoneyHandoff') as mock_m:
            mock_m.query.filter_by.return_value.first.return_value = row
            out = MoneyHandoffService.confirm(
                8, 1, received_amount=50, actor_user_id=1, actor_label='x'
            )
            self.assertEqual(out['status'], HANDOFF_CONFIRMED)

    def test_catalog_inactive_mapping(self):
        from nodeone.modules.eposone.ops_lifecycle import catalog_sync_status

        self.assertEqual(catalog_sync_status('ACTIVE'), 'ACTIVE')
        self.assertEqual(catalog_sync_status('disabled'), 'INACTIVE')

    def test_close_test_phrase_required(self):
        from nodeone.modules.eposone.money_handoff_service import MoneyHandoffError, close_test_period

        with patch(
            'nodeone.modules.eposone.money_handoff_service.resolve_ops_lifecycle',
            return_value='TEST',
        ):
            with self.assertRaises(MoneyHandoffError) as ctx:
                close_test_period(8, confirm_phrase='BORRAR TODO', actor_user_id=1, actor_label='A')
            self.assertIn('confirm_phrase_invalid', str(ctx.exception))

    def test_close_test_blocked_when_operational(self):
        from nodeone.modules.eposone.money_handoff_service import MoneyHandoffError, close_test_period

        with patch(
            'nodeone.modules.eposone.money_handoff_service.resolve_ops_lifecycle',
            return_value='OPERATIONAL',
        ):
            with self.assertRaises(MoneyHandoffError):
                close_test_period(
                    8, confirm_phrase='PREPARAR OPERACION REAL', actor_user_id=1, actor_label='A'
                )


if __name__ == '__main__':
    unittest.main()
