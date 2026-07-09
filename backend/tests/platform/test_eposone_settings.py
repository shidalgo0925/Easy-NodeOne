"""Tests configuración EPosOne."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestEposoneSettingsService(unittest.TestCase):
    @patch('nodeone.modules.eposone.settings_service.EposoneSettings')
    def test_get_settings_defaults_when_missing(self, mock_cls):
        from nodeone.modules.eposone.settings_service import EposoneSettingsService

        mock_cls.query.filter_by.return_value.first.return_value = None
        dto = EposoneSettingsService.get_settings(1)
        self.assertEqual(dto.organization_id, 1)
        self.assertEqual(dto.default_currency, 'USD')
        self.assertTrue(dto.kds_auto_enqueue)

    @patch('app.db')
    @patch('nodeone.modules.eposone.settings_service.EposoneSettings')
    def test_update_settings_creates_row(self, mock_cls, mock_db):
        from nodeone.modules.eposone.settings_service import EposoneSettingsService

        row = MagicMock()
        row.organization_id = 1
        row.default_currency = 'USD'
        row.kds_auto_enqueue = True
        row.delivery_auto_create = True
        row.fiscal_on_payment = False
        row.supervisor_approval_required = True
        mock_cls.query.filter_by.return_value.first.return_value = None
        mock_cls.return_value = row

        dto = EposoneSettingsService.update_settings(
            1,
            default_currency='PAB',
            fiscal_on_payment=True,
        )
        self.assertEqual(dto.default_currency, 'PAB')
        self.assertTrue(dto.fiscal_on_payment)

    @patch('app.db')
    @patch('nodeone.modules.eposone.settings_service.EposoneSettings')
    def test_update_settings_rejects_invalid_currency(self, mock_cls, mock_db):
        from nodeone.core.commerce.order import OrderValidationError
        from nodeone.modules.eposone.settings_service import EposoneSettingsService

        row = MagicMock()
        row.organization_id = 1
        row.default_currency = 'USD'
        row.kds_auto_enqueue = True
        row.delivery_auto_create = True
        row.fiscal_on_payment = False
        row.supervisor_approval_required = True
        mock_cls.query.filter_by.return_value.first.return_value = row

        with self.assertRaises(OrderValidationError):
            EposoneSettingsService.update_settings(1, default_currency='XYZ')


class TestEposoneSettingsRuntime(unittest.TestCase):
    @patch('nodeone.modules.eposone.kds_service.KdsService.maybe_enqueue_for_order_status')
    @patch('nodeone.modules.eposone.settings_service.EposoneSettingsService.runtime_for')
    @patch('nodeone.core.commerce.order.OrderService.publish_confirmed')
    @patch('nodeone.core.commerce.order.OrderService.publish_status_changed')
    @patch('nodeone.core.commerce.order.OrderService.can_transition', return_value=True)
    @patch('app.db')
    @patch('nodeone.core.commerce.order.CoreCommercialOrder')
    def test_transition_skips_kds_when_disabled(
        self, mock_order_cls, mock_db, _can, _pub_status, _pub_conf, mock_runtime, mock_kds
    ):
        from types import SimpleNamespace

        from nodeone.core.commerce.constants import ORDER_STATUS_CONFIRMED, ORDER_STATUS_DRAFT
        from nodeone.core.commerce.order import OrderService

        mock_runtime.return_value = SimpleNamespace(kds_auto_enqueue=False, delivery_auto_create=True)
        row = MagicMock()
        row.id = 5
        row.order_ref = 'POS-0005'
        row.status = ORDER_STATUS_DRAFT
        row.version = 1
        row.lines = []
        mock_order_cls.query.filter_by.return_value.first.return_value = row

        OrderService.transition_status(1, 5, ORDER_STATUS_CONFIRMED)
        mock_kds.assert_not_called()

    @patch('nodeone.modules.eposone.settings_service.EposoneSettingsService.runtime_for')
    def test_assert_supervisor_skipped_when_not_required(self, mock_runtime):
        from types import SimpleNamespace

        from nodeone.core.commerce.authorization import CommerceAuthorizationService

        mock_runtime.return_value = SimpleNamespace(supervisor_approval_required=False)
        uid = CommerceAuthorizationService.assert_supervisor(1, {}, action='cash.manual_movement')
        self.assertEqual(uid, 0)


class TestEposoneSettingsSections(unittest.TestCase):
    def test_settings_slug(self):
        from nodeone.modules.eposone.sections import EPOSONE_SECTION_SLUGS

        self.assertIn('settings', EPOSONE_SECTION_SLUGS)


if __name__ == '__main__':
    unittest.main()
