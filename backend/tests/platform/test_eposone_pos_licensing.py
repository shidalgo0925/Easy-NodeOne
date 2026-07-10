"""Tests LicensePolicy + sync por POS (ADR-005 / infraestructura sin cupos)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestLicensePolicy(unittest.TestCase):
    def test_always_allows(self):
        from nodeone.core.license.policy import LicensePolicy, LicenseLimits

        policy = LicensePolicy(LicenseLimits.unlimited())
        self.assertTrue(policy.can_create_company())
        self.assertTrue(policy.can_create_branch())
        self.assertTrue(policy.can_create_pos())
        self.assertTrue(policy.can_create_cash_register())
        self.assertTrue(policy.can_create_device())
        self.assertTrue(policy.can_create_user())
        self.assertTrue(policy.can_create('pos'))
        self.assertTrue(policy.has_feature('anything'))
        policy.assert_can_create('pos')  # no raise

    def test_unlimited_sentinel(self):
        from nodeone.core.license.policy import LicenseLimits

        self.assertTrue(LicenseLimits.is_unlimited(None))
        self.assertTrue(LicenseLimits.is_unlimited(-1))
        self.assertFalse(LicenseLimits.is_unlimited(0))
        self.assertFalse(LicenseLimits.is_unlimited(5))

    def test_policy_for_organization_unlimited(self):
        from nodeone.core.license.policy import policy_for_organization

        p = policy_for_organization(99)
        self.assertTrue(p.can_create_pos())
        self.assertEqual(p.limits.max_pos, -1)


class TestSyncByPos(unittest.TestCase):
    def test_client_id_prefers_pos(self):
        from nodeone.core.eposone_domain.models import Device
        from nodeone.core.eposone_domain.platform_sync import SyncClientContext

        device = Device(id='dev-1', profile='fixed', pos_id='POS-A')
        ctx = SyncClientContext(
            operating_mode='platform',
            device_id='dev-1',
            device=device,
            pos_id='POS-A',
        )
        self.assertEqual(ctx.client_id, 'pos:POS-A')
        self.assertEqual(ctx.sync_scope, 'POS-A')

    def test_client_id_fallback_device(self):
        from nodeone.core.eposone_domain.platform_sync import SyncClientContext

        ctx = SyncClientContext(operating_mode='platform', device_id='uuid-abc')
        self.assertEqual(ctx.client_id, 'uuid-abc')

    def test_resolve_pos_from_device(self):
        from nodeone.core.eposone_domain.devices import RegisterDeviceInput, registry_from_bundle
        from nodeone.core.eposone_domain.memory import MemoryProviderBundle
        from nodeone.core.eposone_domain.platform_sync import resolve_sync_context

        bundle = MemoryProviderBundle()
        reg = registry_from_bundle(bundle)
        reg.register(
            RegisterDeviceInput(device_id='dev-1', profile='fixed', pos_id='POS-01')
        )
        ctx = resolve_sync_context(
            operating_mode='platform',
            device_id='dev-1',
            devices=bundle.devices,
        )
        self.assertEqual(ctx.pos_id, 'POS-01')
        self.assertEqual(ctx.client_id, 'pos:POS-01')

    @patch('nodeone.core.sync.queue.SyncOperationService.enqueue')
    def test_enqueue_tags_pos_in_payload(self, mock_enqueue):
        from nodeone.core.eposone_domain.platform_sync import PlatformSyncBridge

        mock_enqueue.return_value = MagicMock()
        bridge = PlatformSyncBridge(default_mode='platform')
        bridge.enqueue(
            1,
            idempotency_key='k1',
            operation_type='create_order',
            payload={'lines': []},
            operating_mode='platform',
            device_id='tablet-uuid',
            pos_id='POS-MAIN',
        )
        kwargs = mock_enqueue.call_args.kwargs
        self.assertEqual(kwargs['client_id'], 'pos:POS-MAIN')
        self.assertEqual(kwargs['payload']['pos_id'], 'POS-MAIN')
        self.assertEqual(kwargs['payload']['sync_scope'], 'POS-MAIN')


class TestOrgUnitPosConstant(unittest.TestCase):
    def test_pos_in_types(self):
        from nodeone.core.master.constants import (
            ORG_UNIT_POS_TYPES,
            ORG_UNIT_TYPE_POS,
            ORG_UNIT_TYPES,
        )

        self.assertIn(ORG_UNIT_TYPE_POS, ORG_UNIT_TYPES)
        self.assertIn(ORG_UNIT_TYPE_POS, ORG_UNIT_POS_TYPES)


if __name__ == '__main__':
    unittest.main()
