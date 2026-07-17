"""Tests RegisterLicenseService — unidad comercial = Caja."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestRegisterLicenseSnapshot(unittest.TestCase):
    def test_unlicensed_cannot_operate(self):
        from nodeone.modules.eposone.register_license_service import RegisterLicenseService

        with patch.object(RegisterLicenseService, 'get_or_create') as mock_goc:
            # snapshot without row path
            with patch(
                'nodeone.modules.eposone.register_license_service.EposoneRegisterLicense'
            ) as mock_model:
                mock_model.query.filter_by.return_value.first.return_value = None
                snap = RegisterLicenseService.snapshot(1, 'caja-01')
        self.assertFalse(snap.can_operate)
        self.assertEqual(snap.commercial_ui_key(), 'unlicensed')

    def test_trial_payload(self):
        from nodeone.modules.eposone.register_license_service import RegisterLicenseSnapshot

        now = datetime.utcnow()
        snap = RegisterLicenseSnapshot(
            register_ref='caja-01',
            license_type='trial',
            status='active',
            plan_code='eposone',
            starts_at=now,
            expires_at=now + timedelta(days=45),
            trial_used=True,
            days_remaining=45,
            can_operate=True,
            commercial_ui='Trial',
            reason=None,
        )
        payload = snap.to_device_payload()
        self.assertTrue(payload['can_operate'])
        self.assertEqual(payload['status'], 'trial')
        self.assertEqual(payload['days_remaining'], 45)


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
