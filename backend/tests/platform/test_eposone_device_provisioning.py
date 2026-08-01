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


class TestInstallationBlock(unittest.TestCase):
    def test_shape_and_defaults(self):
        from nodeone.modules.eposone.device_provisioning import build_installation_block

        with patch.dict('os.environ', {}, clear=False):
            # Clear optional gates without wiping whole env.
            with patch.dict(
                'os.environ',
                {
                    'EPOSONE_MIN_APP_VERSION': '',
                    'EPOSONE_DEPLOY_ENV': 'dev',
                    'EASYNODEONE_DEPLOY_ENV': '',
                    'EASYNODEONE_SILO': '',
                    'FLASK_ENV': 'production',
                },
                clear=False,
            ):
                block = build_installation_block()
        self.assertEqual(block['schema_version'], 1)
        self.assertTrue(block['bootstrap_required'])
        self.assertEqual(block['channel'], 'integrated')
        self.assertIsNone(block['min_app_version'])
        self.assertEqual(block['min_bootstrap_schema'], 1)
        self.assertEqual(
            block['capabilities'],
            {'cash_shifts': True, 'orders': True, 'offline': True},
        )
        self.assertEqual(
            block['sync_policy'],
            {
                'mode': 'bootstrap_then_incremental',
                'catalog_full_on_mismatch': True,
            },
        )
        self.assertEqual(block['deployment']['environment'], 'dev')
        self.assertTrue(str(block['deployment']['server_time']).endswith('Z'))

    def test_min_app_version_from_env(self):
        from nodeone.modules.eposone.device_provisioning import build_installation_block

        with patch.dict('os.environ', {'EPOSONE_MIN_APP_VERSION': '2.5.0'}, clear=False):
            block = build_installation_block()
        self.assertEqual(block['min_app_version'], '2.5.0')

    def test_bootstrap_includes_installation(self):
        from nodeone.modules.eposone.device_provisioning import DeviceProvisioningService

        row = MagicMock()
        row.organization_id = 9
        row.branch_ref = 'br-1'
        row.pos_ref = 'pos-1'
        row.register_ref = 'reg-1'

        with patch(
            'nodeone.modules.eposone.device_provisioning.DeviceProvisioningService.build_config'
        ) as mock_build_config, patch('app.db') as mock_db, patch(
            'models.core_master.CoreProduct'
        ) as mock_cp, patch(
            'nodeone.core.commerce.stock.StockService'
        ) as stock_svc, patch(
            'nodeone.core.services.product.ProductService'
        ) as prod_svc, patch(
            'nodeone.modules.eposone.cashier_service.CashierService'
        ) as cash_svc, patch(
            'nodeone.modules.eposone.commercial_policy_service.CommercialPolicyService'
        ) as pol_svc:
            mock_build_config.return_value = {
                'config_version': 3,
                'organization': {'id': 9},
                'branch': {'ref': 'br-1'},
                'pos': {'ref': 'pos-1'},
                'register': {'ref': 'reg-1'},
                'currency': 'USD',
                'timezone': 'America/Panama',
                'business_name': 'Test',
            }
            prod_svc.search.return_value = []
            mock_cp.query.filter_by.return_value.order_by.return_value.first.return_value = None
            stock_svc.resolve_warehouse_id.return_value = None
            stock_svc.list_balances.return_value = []
            cash_svc.snapshot.return_value = ([], 1)
            pol_svc.snapshot_for_terminal.return_value = {
                'policies_version': 1,
                'policies_changed': False,
            }
            payload = DeviceProvisioningService.build_bootstrap_for_terminal(
                row, include=frozenset({'config'})
            )

        mock_db.session.commit.assert_called()
        self.assertIn('installation', payload)
        inst = payload['installation']
        self.assertEqual(inst['schema_version'], 1)
        self.assertTrue(inst['bootstrap_required'])
        self.assertEqual(inst['channel'], 'integrated')
        self.assertEqual(payload['config_version'], 3)
        self.assertNotIn('products', payload)
        self.assertIn('ready_acked_at', payload['installation'])

    def test_ack_installation_ready_persists(self):
        from nodeone.modules.eposone.device_provisioning import DeviceProvisioningService

        row = MagicMock()
        row.organization_id = 9
        row.terminal_ref = 'dev-uuid-1'
        row.register_ref = 'reg-1'
        row.device_label = 'Tablet'
        row.status = 'active'
        row.created_at = None
        row.last_seen_at = None
        row.branch_ref = 'br-1'
        row.pos_ref = 'pos-1'
        row.app_version = '1.0.0'
        row.installation_ready_at = None
        row.client_install_id = None
        row.installation_checklist_json = None

        with patch('app.db') as mock_db, patch(
            'nodeone.modules.eposone.device_provisioning._audit_publish'
        ) as audit:
            out = DeviceProvisioningService.ack_installation_ready(
                row,
                {
                    'client_install_id': 'install-abc',
                    'app_version': '2.1.0',
                    'ready_at': '2026-08-01T16:00:00Z',
                    'checklist': {'bootstrap': True, 'license': True},
                },
            )

        mock_db.session.commit.assert_called()
        self.assertTrue(out['ok'])
        self.assertEqual(out['client_install_id'], 'install-abc')
        self.assertEqual(row.app_version, '2.1.0')
        self.assertEqual(row.client_install_id, 'install-abc')
        self.assertIsNotNone(row.installation_ready_at)
        self.assertIn('bootstrap', row.installation_checklist_json)
        audit.assert_called()
        self.assertEqual(audit.call_args[0][1], 'eposone.installation.ready')

    def test_ack_rejects_bad_checklist(self):
        from nodeone.modules.eposone.device_provisioning import (
            DeviceProvisioningError,
            DeviceProvisioningService,
        )

        row = MagicMock()
        with self.assertRaises(DeviceProvisioningError) as ctx:
            DeviceProvisioningService.ack_installation_ready(row, {'checklist': ['x']})
        self.assertEqual(ctx.exception.code, 'invalid_checklist')


if __name__ == '__main__':
    unittest.main()
