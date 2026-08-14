"""Tests ADR-038 F1 — Module Registry."""

from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestModuleRegistryF1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app, db
        from nodeone.core.platform.module_registry import ensure_module_registry
        from nodeone.services.saas_catalog_defaults import ensure_saas_catalog_full

        cls.app = app
        cls.db = db
        with app.app_context():
            ensure_saas_catalog_full()
            ensure_module_registry(printfn=None)

    def setUp(self):
        from models.saas import SaasOrganization

        self.ctx = self.app.app_context()
        self.ctx.push()
        suffix = uuid.uuid4().hex[:10]
        self.org = SaasOrganization(name=f'ModReg {suffix}', subdomain=f'modreg{suffix}')
        self.db.session.add(self.org)
        self.db.session.commit()
        self.oid = int(self.org.id)
        from nodeone.core.platform.module_registry import sync_organization_modules_from_saas

        sync_organization_modules_from_saas(self.oid)

    def tearDown(self):
        from models.module_registry import OrganizationModule
        from models.saas import SaasModule, SaasOrgModule, SaasOrganization

        try:
            OrganizationModule.query.filter_by(organization_id=self.oid).delete(synchronize_session=False)
            SaasOrgModule.query.filter_by(organization_id=self.oid).delete(synchronize_session=False)
            SaasOrganization.query.filter_by(id=self.oid).delete(synchronize_session=False)
            self.db.session.commit()
        except Exception:
            self.db.session.rollback()
        self.ctx.pop()

    def test_enable_fails_when_dependency_missing(self):
        from nodeone.core.platform.module_registry import disable_module, enable_module, is_module_enabled

        # office365 → communications
        disable_module(self.oid, 'office365')
        disable_module(self.oid, 'communications')
        self.assertFalse(is_module_enabled(self.oid, 'communications'))
        ok, err = enable_module(self.oid, 'office365')
        self.assertFalse(ok)
        self.assertIn('communications', (err or '').lower())
        self.assertFalse(is_module_enabled(self.oid, 'office365'))

    def test_disable_does_not_delete_row(self):
        from models.module_registry import OrganizationModule
        from nodeone.core.platform.module_registry import disable_module, enable_module, is_module_enabled

        ok, _ = enable_module(self.oid, 'communications')
        self.assertTrue(ok)
        self.assertTrue(is_module_enabled(self.oid, 'communications'))
        before = OrganizationModule.query.filter_by(
            organization_id=self.oid, module_key='communications'
        ).first()
        self.assertIsNotNone(before)
        row_id = before.id
        ok, _ = disable_module(self.oid, 'communications')
        self.assertTrue(ok)
        after = OrganizationModule.query.filter_by(
            organization_id=self.oid, module_key='communications'
        ).first()
        self.assertIsNotNone(after)
        self.assertEqual(after.id, row_id)
        self.assertFalse(after.enabled)
        self.assertIsNotNone(after.disabled_at)
        self.assertFalse(is_module_enabled(self.oid, 'communications'))

    def test_sync_roundtrip_from_saas(self):
        from models.module_registry import OrganizationModule
        from models.saas import SaasModule, SaasOrgModule
        from nodeone.core.platform.module_registry import (
            is_module_enabled,
            sync_organization_modules_from_saas,
        )

        sales = SaasModule.query.filter_by(code='sales').first()
        self.assertIsNotNone(sales)
        link = SaasOrgModule.query.filter_by(organization_id=self.oid, module_id=sales.id).first()
        if link is None:
            link = SaasOrgModule(organization_id=self.oid, module_id=sales.id, enabled=True)
            self.db.session.add(link)
        else:
            link.enabled = True
        self.db.session.commit()

        # Force registry off then sync from saas
        row = OrganizationModule.query.filter_by(organization_id=self.oid, module_key='sales').first()
        if row is not None:
            row.enabled = False
            self.db.session.commit()

        sync_organization_modules_from_saas(self.oid)
        self.assertTrue(is_module_enabled(self.oid, 'sales'))
        synced = OrganizationModule.query.filter_by(
            organization_id=self.oid, module_key='sales'
        ).first()
        self.assertIsNotNone(synced)
        self.assertTrue(synced.enabled)

    def test_dual_write_keeps_saas_in_sync(self):
        from models.saas import SaasModule, SaasOrgModule
        from nodeone.core.platform.module_registry import disable_module, enable_module

        ok, err = enable_module(self.oid, 'communications')
        self.assertTrue(ok, err)
        mod = SaasModule.query.filter_by(code='communications').first()
        link = SaasOrgModule.query.filter_by(organization_id=self.oid, module_id=mod.id).first()
        self.assertIsNotNone(link)
        self.assertTrue(link.enabled)

        ok, err = disable_module(self.oid, 'communications')
        self.assertTrue(ok, err)
        self.db.session.refresh(link)
        self.assertFalse(link.enabled)

    def test_saas_admin_api_delegates(self):
        from saas_admin_api import saas_set_module_enabled

        ok, err = saas_set_module_enabled(self.oid, 'communications', True)
        self.assertTrue(ok, err)
        ok, err = saas_set_module_enabled(self.oid, 'office365', True)
        self.assertTrue(ok, err)
        ok, err = saas_set_module_enabled(self.oid, 'communications', False)
        self.assertFalse(ok)
        self.assertIn('office365', (err or '').lower())


if __name__ == '__main__':
    unittest.main()
