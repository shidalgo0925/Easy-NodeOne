"""Tests EPosOne V4 Sprint 6 — Dispositivos POS."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestDeviceRegistryMemory(unittest.TestCase):
    def setUp(self):
        from nodeone.core.eposone_domain.devices import registry_from_bundle
        from nodeone.core.eposone_domain.memory import MemoryProviderBundle
        from nodeone.core.eposone_domain.ports import DeviceRepository

        self.bundle = MemoryProviderBundle()
        self.assertIsInstance(self.bundle.devices, DeviceRepository)
        self.reg = registry_from_bundle(self.bundle)

    def test_register_assign_heartbeat(self):
        from nodeone.core.eposone_domain.devices import RegisterDeviceInput, new_device_id

        did = new_device_id()
        d = self.reg.register(
            RegisterDeviceInput(
                device_id=did,
                profile='handheld',
                name='Tablet mesero',
                business_id='biz1',
                branch_id='br1',
                register_id='reg1',
                platform='android',
                device_model='Galaxy Tab',
                app_version='1.0.0',
            )
        )
        self.assertEqual(d.id, did)
        self.assertEqual(d.profile, 'handheld')
        self.assertTrue(d.sync_enabled)
        assigned = self.reg.assign(did, register_id='reg2')
        self.assertEqual(assigned.register_id, 'reg2')
        hb = self.reg.heartbeat(did, app_version='1.0.1')
        self.assertEqual(hb.app_version, '1.0.1')
        self.assertIsNotNone(hb.last_seen_at)
        self.assertEqual(len(self.reg.list_active()), 1)

    def test_invalid_profile_and_deactivate(self):
        from nodeone.core.eposone_domain.devices import (
            DeviceRegistryError,
            RegisterDeviceInput,
        )

        with self.assertRaises(DeviceRegistryError):
            self.reg.register(RegisterDeviceInput(profile='kiosk'))  # type: ignore[arg-type]
        d = self.reg.register(RegisterDeviceInput(name='Caja', profile='fixed'))
        off = self.reg.deactivate(d.id)
        self.assertEqual(off.status, 'inactive')
        self.assertFalse(off.sync_enabled)
        self.assertEqual(len(self.reg.list_active()), 0)


class TestDeviceSqlite(unittest.TestCase):
    def test_sqlite_roundtrip(self):
        from nodeone.core.eposone_domain.devices import RegisterDeviceInput, registry_from_bundle
        from nodeone.core.eposone_domain.sqlite import SqliteProviderBundle

        with tempfile.TemporaryDirectory() as tmp:
            b = SqliteProviderBundle(Path(tmp) / 'dev.db')
            reg = registry_from_bundle(b)
            d = reg.register(
                RegisterDeviceInput(profile='fixed', name='POS-1', platform='android')
            )
            got = b.devices.get(d.id)
            self.assertIsNotNone(got)
            assert got is not None
            self.assertEqual(got.name, 'POS-1')


class TestTerminalDtoMapping(unittest.TestCase):
    def test_api_mapper(self):
        from nodeone.core.eposone_domain.api import terminal_dto_to_device

        dto = SimpleNamespace(
            terminal_ref='uuid-1',
            organization_id=3,
            device_label='Caja',
            register_ref='reg-a',
            status='active',
            profile='fixed',
            platform='android',
            device_model='Sunmi',
            app_version='2.0',
            branch_ref='br-1',
            sync_enabled=True,
            last_seen_at=None,
        )
        d = terminal_dto_to_device(dto)
        self.assertEqual(d.id, 'uuid-1')
        self.assertEqual(d.business_id, '3')
        self.assertEqual(d.register_id, 'reg-a')
        self.assertEqual(d.profile, 'fixed')


class TestPosTerminalDtoDict(unittest.TestCase):
    def test_to_dict_includes_v4(self):
        from nodeone.core.commerce.dtos import PosTerminalDTO

        dto = PosTerminalDTO(
            id=1,
            organization_id=1,
            terminal_ref='dev-uuid',
            register_ref='caja-1',
            status='active',
            device_label='Mostrador',
            profile='fixed',
            platform='android',
            sync_enabled=True,
        )
        data = dto.to_dict()
        self.assertEqual(data['device_id'], 'dev-uuid')
        self.assertEqual(data['profile'], 'fixed')
        self.assertTrue(data['sync_enabled'])


if __name__ == '__main__':
    unittest.main()
