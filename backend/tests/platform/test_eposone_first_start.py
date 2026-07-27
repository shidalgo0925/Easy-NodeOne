"""Tests EPosOne V4 Sprint 4 — primer inicio (Crear negocio | Conectar EN1)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestFirstStartChoices(unittest.TestCase):
    def test_two_paths_and_copy(self):
        from nodeone.core.eposone_domain.first_start import (
            FIRST_START_CHOICES,
            LABEL_CONNECT_EN1,
            LABEL_CREATE_BUSINESS,
            FirstStartWizard,
            PATH_CONNECT_EN1,
            PATH_CREATE_BUSINESS,
        )

        choices = FirstStartWizard.choices()
        self.assertEqual(len(choices), 2)
        self.assertEqual(choices[0].path, PATH_CREATE_BUSINESS)
        self.assertEqual(choices[0].label, LABEL_CREATE_BUSINESS)
        self.assertEqual(choices[1].path, PATH_CONNECT_EN1)
        self.assertEqual(choices[1].label, LABEL_CONNECT_EN1)
        joined = ' '.join(c.label + c.description for c in FIRST_START_CHOICES).lower()
        self.assertNotIn('migración', joined)
        self.assertNotIn('migracion', joined)


class TestCreateLocalBusiness(unittest.TestCase):
    def setUp(self):
        from nodeone.core.eposone_domain.first_start import wizard_from_memory_bundle
        from nodeone.core.eposone_domain.memory import MemoryProviderBundle

        self.bundle = MemoryProviderBundle()
        self.wizard = wizard_from_memory_bundle(self.bundle)

    def test_creates_business_branch_register_admin(self):
        from nodeone.core.eposone_domain.first_start import CreateBusinessInput, MODE_LOCAL

        self.assertTrue(self.wizard.needs_first_start())
        result = self.wizard.create_local_business(
            CreateBusinessInput(
                business_name='Café Demo',
                currency='usd',
                branch_name='Centro',
                register_name='Caja A',
                admin_display_name='Ana',
                admin_email='ana@demo.test',
            )
        )
        self.assertTrue(result.state.completed)
        self.assertEqual(result.state.operating_mode, MODE_LOCAL)
        self.assertEqual(result.business.name, 'Café Demo')
        self.assertEqual(result.business.currency, 'USD')
        self.assertEqual(result.branch.name, 'Centro')
        self.assertEqual(result.register.name, 'Caja A')
        self.assertEqual(result.admin.display_name, 'Ana')
        self.assertIn('manager', result.admin.operational_roles)
        self.assertFalse(self.wizard.needs_first_start())
        self.assertEqual(self.bundle.config.get_business().name, 'Café Demo')
        self.assertEqual(len(self.bundle.config.get_branches()), 1)
        self.assertEqual(len(self.bundle.config.get_registers()), 1)

    def test_rejects_empty_name_and_double_run(self):
        from nodeone.core.eposone_domain.first_start import CreateBusinessInput, FirstStartError

        with self.assertRaises(FirstStartError):
            self.wizard.create_local_business(CreateBusinessInput(business_name='  '))
        self.wizard.create_local_business(CreateBusinessInput(business_name='Ok'))
        with self.assertRaises(FirstStartError):
            self.wizard.create_local_business(CreateBusinessInput(business_name='Again'))


class TestConnectEn1(unittest.TestCase):
    def setUp(self):
        from nodeone.core.eposone_domain.first_start import wizard_from_memory_bundle
        from nodeone.core.eposone_domain.memory import MemoryProviderBundle

        self.bundle = MemoryProviderBundle()
        self.wizard = wizard_from_memory_bundle(self.bundle)

    def test_connect_requires_access_and_org(self):
        from nodeone.core.eposone_domain.first_start import ConnectEn1Input, FirstStartError

        with self.assertRaises(FirstStartError):
            self.wizard.connect_en1(
                ConnectEn1Input(organization_id='', access_granted=True)
            )
        with self.assertRaises(FirstStartError):
            self.wizard.connect_en1(
                ConnectEn1Input(organization_id='3', access_granted=False)
            )

    def test_connect_sets_platform_mode(self):
        from nodeone.core.eposone_domain.first_start import (
            ConnectEn1Input,
            MODE_PLATFORM,
            PATH_CONNECT_EN1,
        )

        result = self.wizard.connect_en1(
            ConnectEn1Input(
                organization_id='3',
                access_granted=True,
                business_name='Org Relatic Dev',
                currency='PAB',
                branch_name='Sucursal 1',
                register_name='POS-1',
            )
        )
        self.assertEqual(result.state.operating_mode, MODE_PLATFORM)
        self.assertEqual(result.state.path, PATH_CONNECT_EN1)
        self.assertEqual(result.state.en1_organization_id, '3')
        self.assertTrue(result.state.has_en1_credentials)
        self.assertEqual(result.business.currency, 'PAB')
        self.assertFalse(self.wizard.needs_first_start())


class TestSqliteFirstStartPersistence(unittest.TestCase):
    def setUp(self):
        from nodeone.core.eposone_domain.first_start import wizard_from_sqlite_bundle
        from nodeone.core.eposone_domain.sqlite import SqliteProviderBundle

        self._tmp = tempfile.TemporaryDirectory()
        path = Path(self._tmp.name) / 'first_start.db'
        self.path = path
        self.bundle = SqliteProviderBundle(path)
        self.wizard = wizard_from_sqlite_bundle(self.bundle)

    def tearDown(self):
        self._tmp.cleanup()

    def test_state_survives_reopen(self):
        from nodeone.core.eposone_domain.first_start import (
            CreateBusinessInput,
            MODE_LOCAL,
            wizard_from_sqlite_bundle,
        )
        from nodeone.core.eposone_domain.sqlite import SqliteProviderBundle

        self.wizard.create_local_business(
            CreateBusinessInput(business_name='Persist Café', currency='USD')
        )
        reopened = SqliteProviderBundle(self.path)
        wiz2 = wizard_from_sqlite_bundle(reopened)
        st = wiz2.current_state()
        self.assertTrue(st.completed)
        self.assertEqual(st.operating_mode, MODE_LOCAL)
        self.assertEqual(reopened.config.get_business().name, 'Persist Café')
        self.assertFalse(wiz2.needs_first_start())


if __name__ == '__main__':
    unittest.main()
