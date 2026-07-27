"""Tests RegisterLicenseService — License Engine V1 contrato bootstrap."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestRegisterLicenseSnapshot(unittest.TestCase):
    def test_unlicensed_cannot_operate(self):
        from nodeone.modules.eposone.register_license_service import RegisterLicenseService

        with patch(
            'nodeone.modules.eposone.register_license_service.EposoneRegisterLicense'
        ) as mock_model:
            mock_model.query.filter_by.return_value.first.return_value = None
            snap = RegisterLicenseService.snapshot(1, 'caja-01')
        self.assertFalse(snap.can_operate)
        self.assertEqual(snap.commercial_ui_key(), 'unlicensed')

    def test_trial_payload_v1_contract(self):
        from nodeone.modules.eposone.register_license_service import RegisterLicenseSnapshot

        now = datetime.utcnow()
        snap = RegisterLicenseSnapshot(
            register_ref='caja-01',
            license_type='trial',
            status='active',
            plan_code='trial',
            starts_at=now,
            expires_at=now + timedelta(days=15),
            trial_used=True,
            days_remaining=15,
            can_operate=True,
            commercial_ui='Trial',
            reason=None,
            license_id='lic_123',
            activation_method='EN1',
            issued_at=now,
            grace_until=None,
            last_validation=now,
            updated_at=now,
            features=['sales', 'payments', 'cash_shifts', 'customers', 'reports'],
            limits={'max_devices': 1, 'max_cashiers': None, 'max_products': None},
            organization_id=1,
        )
        payload = snap.to_device_payload()
        self.assertEqual(payload['schema_version'], 1)
        self.assertEqual(payload['license_id'], 'lic_123')
        self.assertEqual(payload['license_type'], 'TRIAL')
        self.assertEqual(payload['status'], 'ACTIVE')
        self.assertEqual(payload['plan_code'], 'trial')
        self.assertEqual(payload['activation_method'], 'EN1')
        self.assertIsNone(payload['grace_until'])
        self.assertIn('sales', payload['features'])
        self.assertEqual(payload['limits']['max_devices'], 1)
        self.assertNotIn('can_operate', payload)


class TestCommercialUiKey(unittest.TestCase):
    def test_courtesy_and_perpetual(self):
        from nodeone.modules.eposone.register_license_service import RegisterLicenseSnapshot

        courtesy = RegisterLicenseSnapshot(
            register_ref='c',
            license_type='courtesy',
            status='active',
            plan_code='eposone',
            starts_at=None,
            expires_at=None,
            trial_used=False,
            days_remaining=None,
            can_operate=True,
            commercial_ui='Cortesía',
            reason=None,
        )
        self.assertEqual(courtesy.commercial_ui_key(), 'courtesy')


if __name__ == '__main__':
    unittest.main()
