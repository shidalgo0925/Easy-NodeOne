"""Tests ADR-039 F1 — Products module (core_product formalization)."""

from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestEn1ProductsF1(unittest.TestCase):
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
        from nodeone.core.platform.module_registry import enable_module, sync_organization_modules_from_saas

        self.ctx = self.app.app_context()
        self.ctx.push()
        suffix = uuid.uuid4().hex[:8]
        self.org_a = SaasOrganization(name=f'ProdA {suffix}', subdomain=f'proda{suffix}')
        self.org_b = SaasOrganization(name=f'ProdB {suffix}', subdomain=f'prodb{suffix}')
        self.db.session.add(self.org_a)
        self.db.session.add(self.org_b)
        self.db.session.commit()
        self.oid_a = int(self.org_a.id)
        self.oid_b = int(self.org_b.id)
        sync_organization_modules_from_saas(self.oid_a)
        sync_organization_modules_from_saas(self.oid_b)
        ok, err = enable_module(self.oid_a, 'products')
        self.assertTrue(ok, err)
        self.ref = f'COC355-{suffix}'

    def tearDown(self):
        from models.core_master import CoreProduct
        from models.module_registry import OrganizationModule
        from models.saas import SaasOrgModule, SaasOrganization

        try:
            CoreProduct.query.filter(
                CoreProduct.organization_id.in_([self.oid_a, self.oid_b])
            ).delete(synchronize_session=False)
            OrganizationModule.query.filter(
                OrganizationModule.organization_id.in_([self.oid_a, self.oid_b])
            ).delete(synchronize_session=False)
            SaasOrgModule.query.filter(
                SaasOrgModule.organization_id.in_([self.oid_a, self.oid_b])
            ).delete(synchronize_session=False)
            SaasOrganization.query.filter(
                SaasOrganization.id.in_([self.oid_a, self.oid_b])
            ).delete(synchronize_session=False)
            self.db.session.commit()
        except Exception:
            self.db.session.rollback()
        self.ctx.pop()

    def test_inventory_requires_products(self):
        from nodeone.core.platform.module_registry import disable_module, enable_module

        disable_module(self.oid_a, 'inventory')
        disable_module(self.oid_a, 'products')
        ok, err = enable_module(self.oid_a, 'inventory')
        self.assertFalse(ok)
        self.assertIn('products', (err or '').lower())

    def test_create_and_tenant_isolation(self):
        from nodeone.core.master.product import CoreProductService

        dto = CoreProductService.create(
            self.oid_a,
            {
                'product_ref': self.ref,
                'name': 'Coca-Cola 355 ml',
                'product_type': 'good',
                'tracks_inventory': True,
                'unit_price': 1.25,
                'status': 'active',
            },
        )
        self.assertEqual(dto.organization_id, self.oid_a)
        self.assertTrue(dto.tracks_inventory)
        self.assertIsNone(CoreProductService.get_by_ref(self.oid_b, self.ref))
        self.assertIsNotNone(CoreProductService.get_by_ref(self.oid_a, self.ref))

    def test_module_definitions_seeded(self):
        from models.module_registry import ModuleDefinition

        prod = ModuleDefinition.query.filter_by(module_key='products').first()
        inv = ModuleDefinition.query.filter_by(module_key='inventory').first()
        self.assertIsNotNone(prod)
        self.assertIsNotNone(inv)
        deps = (inv.dependencies_json or '')
        self.assertIn('products', deps)


if __name__ == '__main__':
    unittest.main()
