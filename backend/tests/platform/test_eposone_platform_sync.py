"""Tests EPosOne V4 Sprint 7 — sync policy Modo Plataforma."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestPlatformSyncPolicy(unittest.TestCase):
    def test_local_mode_blocked(self):
        from nodeone.core.eposone_domain.platform_sync import (
            PlatformSyncError,
            SyncClientContext,
            assert_platform_sync_allowed,
        )

        with self.assertRaises(PlatformSyncError) as ctx:
            assert_platform_sync_allowed(
                SyncClientContext(operating_mode='local', organization_id='1')
            )
        self.assertIn('local', str(ctx.exception))

    def test_uninitialized_blocked(self):
        from nodeone.core.eposone_domain.platform_sync import (
            PlatformSyncError,
            SyncClientContext,
            assert_platform_sync_allowed,
        )

        with self.assertRaises(PlatformSyncError):
            assert_platform_sync_allowed(SyncClientContext(operating_mode='uninitialized'))

    def test_platform_allowed(self):
        from nodeone.core.eposone_domain.platform_sync import (
            SyncClientContext,
            assert_platform_sync_allowed,
        )

        assert_platform_sync_allowed(
            SyncClientContext(operating_mode='platform', organization_id='1')
        )

    def test_device_sync_disabled(self):
        from nodeone.core.eposone_domain.models import Device
        from nodeone.core.eposone_domain.platform_sync import (
            PlatformSyncError,
            SyncClientContext,
            assert_platform_sync_allowed,
        )

        device = Device(
            id='d1',
            profile='fixed',
            status='active',
            sync_enabled=False,
        )
        with self.assertRaises(PlatformSyncError) as ctx:
            assert_platform_sync_allowed(
                SyncClientContext(operating_mode='platform', device=device)
            )
        self.assertIn('device', str(ctx.exception))

    def test_client_id_from_device(self):
        from nodeone.core.eposone_domain.platform_sync import SyncClientContext

        ctx = SyncClientContext(operating_mode='platform', device_id='uuid-abc')
        self.assertEqual(ctx.client_id, 'uuid-abc')


class TestResolveSyncContext(unittest.TestCase):
    def test_default_platform_for_en1_web(self):
        from nodeone.core.eposone_domain.platform_sync import resolve_sync_context

        ctx = resolve_sync_context(operating_mode=None, organization_id=3)
        self.assertEqual(ctx.operating_mode, 'platform')

    def test_loads_device_from_repo(self):
        from nodeone.core.eposone_domain.devices import RegisterDeviceInput, registry_from_bundle
        from nodeone.core.eposone_domain.memory import MemoryProviderBundle
        from nodeone.core.eposone_domain.platform_sync import resolve_sync_context

        bundle = MemoryProviderBundle()
        reg = registry_from_bundle(bundle)
        d = reg.register(RegisterDeviceInput(device_id='dev-1', profile='fixed'))
        ctx = resolve_sync_context(
            operating_mode='platform',
            device_id='dev-1',
            devices=bundle.devices,
        )
        self.assertIsNotNone(ctx.device)
        assert ctx.device is not None
        self.assertEqual(ctx.device.id, d.id)


class TestPlatformSyncBridgeEnqueue(unittest.TestCase):
    @patch('nodeone.core.sync.queue.SyncOperationService.enqueue')
    def test_enqueue_blocked_in_local(self, mock_enqueue):
        from nodeone.core.eposone_domain.platform_sync import (
            PlatformSyncBridge,
            PlatformSyncError,
        )

        bridge = PlatformSyncBridge(default_mode='platform')
        with self.assertRaises(PlatformSyncError):
            bridge.enqueue(
                1,
                idempotency_key='k1',
                operation_type='create_order',
                operating_mode='local',
                device_id='d1',
            )
        mock_enqueue.assert_not_called()

    @patch('nodeone.core.sync.queue.SyncOperationService.enqueue')
    def test_enqueue_platform_passes_client_id(self, mock_enqueue):
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
        )
        kwargs = mock_enqueue.call_args.kwargs
        self.assertEqual(kwargs['client_id'], 'tablet-uuid')
        self.assertEqual(kwargs['idempotency_key'], 'k1')


if __name__ == '__main__':
    unittest.main()
