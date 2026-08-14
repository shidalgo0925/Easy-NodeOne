"""Tests ADR-039 F3 — Inventory UI wiring (module + endpoints + nav visibility helpers)."""

from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestEn1InventoryF3(unittest.TestCase):
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
        self.org = SaasOrganization(name=f'InvUI {suffix}', subdomain=f'invui{suffix}')
        self.db.session.add(self.org)
        self.db.session.commit()
        self.oid = int(self.org.id)
        sync_organization_modules_from_saas(self.oid)
        ok, err = enable_module(self.oid, 'products')
        self.assertTrue(ok, err)
        ok, err = enable_module(self.oid, 'inventory')
        self.assertTrue(ok, err)
        self.ref = f'SKU-F3-{suffix}'

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

    def test_blueprint_endpoints_registered(self):
        vf = self.app.view_functions
        for name in (
            'en1_inventory.inventory_balances',
            'en1_inventory.inventory_movements',
            'en1_inventory.inventory_receipt',
            'en1_inventory.inventory_adjust',
            'en1_inventory.inventory_kardex',
            'en1_inventory.inventory_warehouses',
        ):
            self.assertIn(name, vf, name)

    def test_ui_flow_via_service_and_templates_exist(self):
        from pathlib import Path

        from nodeone.core.master.product import CoreProductService
        from nodeone.core.platform import inventory_service as inv

        root = Path(__file__).resolve().parents[3] / 'templates' / 'admin' / 'en1_inventory'
        for name in ('balances', 'movements', 'receipt', 'adjust', 'kardex', 'warehouses'):
            self.assertTrue((root / f'{name}.html').is_file(), name)

        CoreProductService.create(
            self.oid,
            {
                'product_ref': self.ref,
                'name': 'F3 item',
                'product_type': 'good',
                'tracks_inventory': True,
                'source_app_id': 'test_f3',
            },
        )
        inv.ensure_default_warehouse(self.oid)
        inv.record_movement(
            self.oid,
            product_ref=self.ref,
            kind='RECEIPT',
            quantity=10,
            source_system='TEST',
            source_event_id=f'f3-in-{self.ref}',
        )
        self.assertEqual(inv.get_on_hand(self.oid, self.ref), 10.0)
        rows = inv.kardex(self.oid, self.ref)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['saldo'], 10.0)

    def test_nav_v2_includes_inventario(self):
        from nodeone.core.nav_menu import _SIDEBAR_V2_FLAT_AREA_IDS

        self.assertIn('inventario', _SIDEBAR_V2_FLAT_AREA_IDS)
        self.assertNotIn('productos', _SIDEBAR_V2_FLAT_AREA_IDS)

    def test_inventario_area_has_productos_chip(self):
        from nodeone.core.nav_menu import APP_AREAS

        inv = next(a for a in APP_AREAS if a.id == 'inventario')
        ids = [i.id for i in inv.items]
        self.assertEqual(ids[0], 'productos')
        self.assertIn('existencias', ids)


if __name__ == '__main__':
    unittest.main()
