"""Tests ADR-039 F6 — Connected inventory bridge (EN1-only)."""

from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestEn1InventoryF6(unittest.TestCase):
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
        from nodeone.core.platform import inventory_service as inv
        from nodeone.core.platform.module_registry import enable_module, sync_organization_modules_from_saas

        self.ctx = self.app.app_context()
        self.ctx.push()
        suffix = uuid.uuid4().hex[:8]
        self.org = SaasOrganization(name=f'InvF6 {suffix}', subdomain=f'invf6{suffix}')
        self.db.session.add(self.org)
        self.db.session.commit()
        self.oid = int(self.org.id)
        sync_organization_modules_from_saas(self.oid)
        self.assertTrue(enable_module(self.oid, 'products')[0])
        self.assertTrue(enable_module(self.oid, 'inventory')[0])
        self.ref = f'SKU-F6-{suffix}'
        CoreProductService.create(
            self.oid,
            {
                'product_ref': self.ref,
                'name': 'Item F6',
                'product_type': 'good',
                'tracks_inventory': True,
                'status': 'active',
            },
        )
        self.wh = inv.ensure_default_warehouse(self.oid)

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

    @patch('nodeone.core.commerce.authorization.CommerceAuthorizationService.assert_supervisor', return_value=0)
    def test_connected_adjust_uses_inventory_kinds(self, _mock_sup):
        from nodeone.core.platform import inventory_service as inv
        from nodeone.core.platform.connected_inventory import record_connected_adjust

        bal = record_connected_adjust(
            self.oid,
            {
                'warehouse_org_unit_id': self.wh['id'],
                'product_ref': self.ref,
                'quantity': 25,
                'reason': 'physical_count',
                'idempotency_key': f'f6-in-{self.ref}',
            },
            source_system='EP1',
        )
        self.assertEqual(bal.quantity_on_hand, 25.0)
        again = record_connected_adjust(
            self.oid,
            {
                'warehouse_org_unit_id': self.wh['id'],
                'product_ref': self.ref,
                'quantity': 25,
                'reason': 'physical_count',
                'idempotency_key': f'f6-in-{self.ref}',
            },
            source_system='EP1',
        )
        self.assertEqual(again.quantity_on_hand, 25.0)
        kx = inv.kardex(self.oid, self.ref, warehouse_org_unit_id=self.wh['id'])
        self.assertEqual(len(kx), 1)
        self.assertEqual(kx[0]['kind'], 'ADJUSTMENT_IN')

    @patch('nodeone.core.commerce.authorization.CommerceAuthorizationService.assert_supervisor', return_value=0)
    def test_fallback_without_inventory_module(self, _mock_sup):
        from nodeone.core.platform.connected_inventory import record_connected_adjust
        from nodeone.core.platform.module_registry import disable_module

        disable_module(self.oid, 'inventory')
        with patch(
            'nodeone.core.commerce.stock.StockService.record_manual_adjust'
        ) as mock_legacy:
            from nodeone.core.commerce.stock import StockBalanceDTO

            mock_legacy.return_value = StockBalanceDTO(
                id=1,
                organization_id=self.oid,
                warehouse_org_unit_id=self.wh['id'],
                product_ref=self.ref,
                quantity_on_hand=1.0,
                quantity_reserved=0.0,
                quantity_available=1.0,
            )
            record_connected_adjust(
                self.oid,
                {
                    'warehouse_org_unit_id': self.wh['id'],
                    'product_ref': self.ref,
                    'quantity': 1,
                },
            )
            mock_legacy.assert_called_once()


if __name__ == '__main__':
    unittest.main()
