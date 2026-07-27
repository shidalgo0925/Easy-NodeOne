"""Tests Hito EN1-01 — DeviceProvisioningService (sin Flask app completa)."""

from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestTokenHash(unittest.TestCase):
    def test_hash_stable(self):
        from nodeone.modules.eposone.device_provisioning import _hash_token

        a = _hash_token('abc')
        b = _hash_token('abc')
        self.assertEqual(a, b)
        self.assertEqual(len(a), 64)
        self.assertEqual(a, hashlib.sha256(b'abc').hexdigest())


class TestDeviceProvisioningErrors(unittest.TestCase):
    def test_error_carries_status(self):
        from nodeone.modules.eposone.device_provisioning import DeviceProvisioningError

        err = DeviceProvisioningError('unauthorized', http_status=401)
        self.assertEqual(err.code, 'unauthorized')
        self.assertEqual(err.http_status, 401)


class TestAuthenticateBearer(unittest.TestCase):
    @patch('nodeone.modules.eposone.device_provisioning.CorePosTerminal')
    def test_missing_bearer(self, mock_model):
        from nodeone.modules.eposone.device_provisioning import (
            DeviceProvisioningError,
            DeviceProvisioningService,
        )

        with self.assertRaises(DeviceProvisioningError) as ctx:
            DeviceProvisioningService.authenticate_bearer(None)
        self.assertEqual(ctx.exception.http_status, 401)
        mock_model.query.filter_by.assert_not_called()

    @patch('nodeone.modules.eposone.device_provisioning.CorePosTerminal')
    def test_valid_token(self, mock_model):
        from nodeone.modules.eposone.device_provisioning import (
            DeviceProvisioningService,
            _hash_token,
        )

        row = MagicMock()
        row.status = 'active'
        mock_model.query.filter_by.return_value.first.return_value = row
        token = 'secret-token'
        out = DeviceProvisioningService.authenticate_bearer(f'Bearer {token}')
        self.assertIs(out, row)
        mock_model.query.filter_by.assert_called_with(access_token_hash=_hash_token(token))


class TestContractPaths(unittest.TestCase):
    def test_blueprint_prefix(self):
        from nodeone.modules.eposone.devices_v1_routes import eposone_devices_v1_bp

        self.assertEqual(eposone_devices_v1_bp.url_prefix, '/api/v1/devices')


if __name__ == '__main__':
    unittest.main()
