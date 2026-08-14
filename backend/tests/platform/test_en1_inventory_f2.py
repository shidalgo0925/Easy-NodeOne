"""Tests ADR-039 F2 — Inventory Core (Coca-Cola gate + tenant + idempotency)."""

from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestEn1InventoryF2(unittest.TestCase):
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
        from nodeone.core.platform.module_registry import (
            enable_module,
            sync_organization_modules_from_saas,
        )

        self.ctx = self.app.app_context()
        self.ctx.push()
        suffix = uuid.uuid4().hex[:8]
        self.org_a = SaasOrganization(name=f'InvA {suffix}', subdomain=f'inva{suffix}')
        self.org_b = SaasOrganization(name=f'InvB {suffix}', subdomain=f'invb{suffix}')
        self.db.session.add(self.org_a)
        self.db.session.add(self.org_b)
        self.db.session.commit()
        self.oid_a = int(self.org_a.id)
        self.oid_b = int(self.org_b.id)
        sync_organization_modules_from_saas(self.oid_a)
        sync_organization_modules_from_saas(self.oid_b)
        self.assertTrue(enable_module(self.oid_a, 'products')[0])
        self.assertTrue(enable_module(self.oid_a, 'inventory')[0])
        self.ref = f'COC355-{suffix}'
        CoreProductService.create(
            self.oid_a,
            {
                'product_ref': self.ref,
                'name': 'Coca-Cola 355 ml',
                'product_type': 'good',
                'tracks_inventory': True,
                'unit_price': 1.0,
                'status': 'active',
            },
        )

    def tearDown(self):
        from models.commercial_core import CoreStockBalance, CoreStockMovement
        from models.core_master import CoreOrgUnit, CoreProduct
        from models.module_registry import OrganizationModule
        from models.saas import SaasOrgModule, SaasOrganization

        try:
            CoreStockMovement.query.filter(
                CoreStockMovement.organization_id.in_([self.oid_a, self.oid_b])
            ).delete(synchronize_session=False)
            CoreStockBalance.query.filter(
                CoreStockBalance.organization_id.in_([self.oid_a, self.oid_b])
            ).delete(synchronize_session=False)
            CoreProduct.query.filter(
                CoreProduct.organization_id.in_([self.oid_a, self.oid_b])
            ).delete(synchronize_session=False)
            CoreOrgUnit.query.filter(
                CoreOrgUnit.organization_id.in_([self.oid_a, self.oid_b])
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

    def test_coca_cola_gate_and_kardex(self):
        from nodeone.core.platform import inventory_service as inv

        inv.record_movement(self.oid_a, product_ref=self.ref, kind='OPENING', quantity=100)
        inv.record_movement(self.oid_a, product_ref=self.ref, kind='SALE', quantity=2)
        inv.record_movement(
            self.oid_a,
            product_ref=self.ref,
            kind='ADJUSTMENT_OUT',
            quantity=1,
            reason='physical_count',
        )
        on_hand = inv.get_on_hand(self.oid_a, self.ref)
        self.assertEqual(on_hand, 97.0)
        kx = inv.kardex(self.oid_a, self.ref)
        self.assertEqual(kx[-1]['saldo'], 97.0)
        entradas = sum(r['entrada'] for r in kx)
        salidas = sum(r['salida'] for r in kx)
        self.assertEqual(entradas, 100.0)
        self.assertEqual(salidas, 3.0)

    def test_tenant_isolation_balances(self):
        from nodeone.core.platform import inventory_service as inv
        from nodeone.core.platform.module_registry import enable_module

        enable_module(self.oid_b, 'products')
        enable_module(self.oid_b, 'inventory')
        inv.record_movement(self.oid_a, product_ref=self.ref, kind='OPENING', quantity=50)
        # Org B no tiene el producto ni el saldo
        self.assertEqual(inv.get_on_hand(self.oid_b, self.ref), 0.0)
        bals_b = __import__(
            'nodeone.core.commerce.stock', fromlist=['StockService']
        ).StockService.list_balances(self.oid_b, product_ref=self.ref)
        self.assertEqual(bals_b, [])

    def test_idempotent_source_event(self):
        from nodeone.core.platform import inventory_service as inv

        inv.record_movement(self.oid_a, product_ref=self.ref, kind='OPENING', quantity=10)
        r2 = inv.record_movement(
            self.oid_a,
            product_ref=self.ref,
            kind='SALE',
            quantity=2,
            source_system='EP1',
            source_event_id='ticket-002',
        )
        self.assertEqual(r2['status'], 'applied')
        r3 = inv.record_movement(
            self.oid_a,
            product_ref=self.ref,
            kind='SALE',
            quantity=2,
            source_system='EP1',
            source_event_id='ticket-002',
        )
        self.assertEqual(r3['status'], 'already_processed')
        self.assertEqual(inv.get_on_hand(self.oid_a, self.ref), 8.0)


if __name__ == '__main__':
    unittest.main()
