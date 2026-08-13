"""Tests ADR-039 F4 — transfers + minimum stock alerts."""

from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestEn1InventoryF4(unittest.TestCase):
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
        from nodeone.core.master.product import CoreProductService
        from nodeone.core.platform.module_registry import enable_module, sync_organization_modules_from_saas
        from nodeone.core.platform import inventory_service as inv

        self.ctx = self.app.app_context()
        self.ctx.push()
        suffix = uuid.uuid4().hex[:8]
        self.org = SaasOrganization(name=f'InvF4 {suffix}', subdomain=f'invf4{suffix}')
        self.db.session.add(self.org)
        self.db.session.commit()
        self.oid = int(self.org.id)
        sync_organization_modules_from_saas(self.oid)
        self.assertTrue(enable_module(self.oid, 'products')[0])
        self.assertTrue(enable_module(self.oid, 'inventory')[0])
        self.ref = f'SKU-F4-{suffix}'
        CoreProductService.create(
            self.oid,
            {
                'product_ref': self.ref,
                'name': 'Item F4',
                'product_type': 'good',
                'tracks_inventory': True,
                'min_stock': 20,
                'status': 'active',
            },
        )
        self.wh_main = inv.ensure_default_warehouse(self.oid)
        self.wh_b = inv.create_warehouse(self.oid, unit_ref=f'sec-{suffix}', name=f'Secundario {suffix}')

    def tearDown(self):
        from models.commercial_core import CoreStockBalance, CoreStockMovement
        from models.core_master import CoreOrgUnit, CoreProduct
        from models.module_registry import OrganizationModule
        from models.saas import SaasOrgModule, SaasOrganization

        try:
            CoreStockMovement.query.filter_by(organization_id=self.oid).delete(synchronize_session=False)
            CoreStockBalance.query.filter_by(organization_id=self.oid).delete(synchronize_session=False)
            CoreProduct.query.filter_by(organization_id=self.oid).delete(synchronize_session=False)
            CoreOrgUnit.query.filter_by(organization_id=self.oid).delete(synchronize_session=False)
            OrganizationModule.query.filter_by(organization_id=self.oid).delete(synchronize_session=False)
            SaasOrgModule.query.filter_by(organization_id=self.oid).delete(synchronize_session=False)
            SaasOrganization.query.filter_by(id=self.oid).delete(synchronize_session=False)
            self.db.session.commit()
        except Exception:
            self.db.session.rollback()
        self.ctx.pop()

    def test_transfer_between_warehouses(self):
        from nodeone.core.platform import inventory_service as inv

        inv.record_movement(
            self.oid,
            product_ref=self.ref,
            kind='RECEIPT',
            quantity=50,
            warehouse_org_unit_id=self.wh_main['id'],
        )
        res = inv.transfer(
            self.oid,
            product_ref=self.ref,
            quantity=12,
            from_warehouse_org_unit_id=self.wh_main['id'],
            to_warehouse_org_unit_id=self.wh_b['id'],
            source_event_id=f't-{self.ref}',
        )
        self.assertEqual(res['status'], 'applied')
        self.assertEqual(inv.get_on_hand(self.oid, self.ref, warehouse_org_unit_id=self.wh_main['id']), 38.0)
        self.assertEqual(inv.get_on_hand(self.oid, self.ref, warehouse_org_unit_id=self.wh_b['id']), 12.0)
        again = inv.transfer(
            self.oid,
            product_ref=self.ref,
            quantity=12,
            from_warehouse_org_unit_id=self.wh_main['id'],
            to_warehouse_org_unit_id=self.wh_b['id'],
            source_event_id=f't-{self.ref}',
        )
        self.assertEqual(again['status'], 'already_processed')
        self.assertEqual(inv.get_on_hand(self.oid, self.ref, warehouse_org_unit_id=self.wh_main['id']), 38.0)

    def test_below_minimum_alert(self):
        from nodeone.core.platform import inventory_service as inv

        inv.record_movement(
            self.oid,
            product_ref=self.ref,
            kind='RECEIPT',
            quantity=5,
            warehouse_org_unit_id=self.wh_main['id'],
        )
        alerts = inv.list_below_minimum(self.oid, warehouse_org_unit_id=self.wh_main['id'])
        hit = [a for a in alerts if a['product_ref'] == self.ref]
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]['deficit'], 15.0)

    def test_endpoints_registered(self):
        vf = self.app.view_functions
        self.assertIn('en1_inventory.inventory_transfer', vf)
        self.assertIn('en1_inventory.inventory_alerts', vf)


if __name__ == '__main__':
    unittest.main()
