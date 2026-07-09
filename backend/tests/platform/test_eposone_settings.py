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


class TestEposoneSettingsSections(unittest.TestCase):
    def test_settings_slug(self):
        from nodeone.modules.eposone.sections import EPOSONE_SECTION_SLUGS

        self.assertIn('settings', EPOSONE_SECTION_SLUGS)


if __name__ == '__main__':
    unittest.main()
