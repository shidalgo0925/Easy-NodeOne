"""Toma física + camino canónico Connected EP1 (DEV)."""

from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestPhysicalInventoryCount(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app, db
        from nodeone.core.platform.module_registry import ensure_module_registry
        from nodeone.services.physical_inventory_schema import ensure_physical_inventory_schema
        from nodeone.services.saas_catalog_defaults import ensure_saas_catalog_full

        cls.app = app
        cls.db = db
        with app.app_context():
            ensure_saas_catalog_full()
            ensure_module_registry(printfn=None)
            ensure_physical_inventory_schema(db, db.engine, printfn=None)

    def setUp(self):
        from models.saas import SaasOrganization
        from nodeone.core.master.product import CoreProductService
        from nodeone.core.platform import inventory_service as inv
        from nodeone.core.platform.module_registry import enable_module, sync_organization_modules_from_saas

        self.ctx = self.app.app_context()
        self.ctx.push()
        suffix = uuid.uuid4().hex[:8]
        self.org = SaasOrganization(name=f'Phys {suffix}', subdomain=f'phys{suffix}')
        self.org_b = SaasOrganization(name=f'PhysB {suffix}', subdomain=f'physb{suffix}')
        self.db.session.add_all([self.org, self.org_b])
        self.db.session.commit()
        self.oid = int(self.org.id)
        self.oid_b = int(self.org_b.id)
        sync_organization_modules_from_saas(self.oid)
        sync_organization_modules_from_saas(self.oid_b)
        self.assertTrue(enable_module(self.oid, 'products')[0])
        self.assertTrue(enable_module(self.oid, 'inventory')[0])
        self.assertTrue(enable_module(self.oid_b, 'products')[0])
        self.assertTrue(enable_module(self.oid_b, 'inventory')[0])
        self.ref = f'ATLAS-{suffix}'
        CoreProductService.create(
            self.oid,
            {
                'product_ref': self.ref,
                'name': 'Cerveza Atlas',
                'product_type': 'good',
                'tracks_inventory': True,
                'status': 'active',
                'uom': 'und',
            },
        )
        CoreProductService.create(
            self.oid_b,
            {
                'product_ref': self.ref,
                'name': 'Cerveza Atlas B',
                'product_type': 'good',
                'tracks_inventory': True,
                'status': 'active',
            },
        )
        self.wh = inv.ensure_default_warehouse(self.oid)
        self.wh_b = inv.ensure_default_warehouse(self.oid_b)
        inv.record_movement(
            self.oid,
            product_ref=self.ref,
            kind='OPENING',
            quantity=20,
            warehouse_org_unit_id=int(self.wh['id']),
        )

    def tearDown(self):
        from models.commercial_core import (
            CoreCommercialOrder,
            CoreCommercialOrderLine,
            CoreStockBalance,
            CoreStockMovement,
        )
        from models.core_master import CoreOrgUnit, CoreProduct
        from models.module_registry import OrganizationModule
        from models.physical_inventory import PhysicalInventoryCount, PhysicalInventoryCountLine
        from models.saas import SaasOrgModule, SaasOrganization

        try:
            PhysicalInventoryCountLine.query.filter(
                PhysicalInventoryCountLine.organization_id.in_([self.oid, self.oid_b])
            ).delete(synchronize_session=False)
            PhysicalInventoryCount.query.filter(
                PhysicalInventoryCount.organization_id.in_([self.oid, self.oid_b])
            ).delete(synchronize_session=False)
            order_ids = [
                r.id
                for r in CoreCommercialOrder.query.filter(
                    CoreCommercialOrder.organization_id.in_([self.oid, self.oid_b])
                ).all()
            ]
            if order_ids:
                CoreCommercialOrderLine.query.filter(
                    CoreCommercialOrderLine.order_id.in_(order_ids)
                ).delete(synchronize_session=False)
            CoreCommercialOrder.query.filter(
                CoreCommercialOrder.organization_id.in_([self.oid, self.oid_b])
            ).delete(synchronize_session=False)
            CoreStockMovement.query.filter(
                CoreStockMovement.organization_id.in_([self.oid, self.oid_b])
            ).delete(synchronize_session=False)
            CoreStockBalance.query.filter(
                CoreStockBalance.organization_id.in_([self.oid, self.oid_b])
            ).delete(synchronize_session=False)
            CoreProduct.query.filter(
                CoreProduct.organization_id.in_([self.oid, self.oid_b])
            ).delete(synchronize_session=False)
            CoreOrgUnit.query.filter(
                CoreOrgUnit.organization_id.in_([self.oid, self.oid_b])
            ).delete(synchronize_session=False)
            OrganizationModule.query.filter(
                OrganizationModule.organization_id.in_([self.oid, self.oid_b])
            ).delete(synchronize_session=False)
            SaasOrgModule.query.filter(
                SaasOrgModule.organization_id.in_([self.oid, self.oid_b])
            ).delete(synchronize_session=False)
            SaasOrganization.query.filter(
                SaasOrganization.id.in_([self.oid, self.oid_b])
            ).delete(synchronize_session=False)
            self.db.session.commit()
        except Exception:
            self.db.session.rollback()
        self.ctx.pop()

    def _start(self, **kwargs):
        from nodeone.core.platform.physical_count_service import start_count

        params = {
            'warehouse_org_unit_id': int(self.wh['id']),
            'created_by_user_id': 101,
            **kwargs,
        }
        return start_count(self.oid, **params)

    def test_01_start_count(self):
        payload = self._start()
        self.assertEqual(payload['status'], 'COUNTING')
        self.assertEqual(payload['count_mode'], 'BLIND')
        self.assertTrue(payload['lines'])
        listed = __import__(
            'nodeone.core.platform.physical_count_service', fromlist=['list_counts']
        ).list_counts(self.oid)
        self.assertTrue(any(int(c['id']) == int(payload['id']) for c in listed))
        line = payload['lines'][0]
        self.assertIn('physical_qty', line)
        self.assertNotIn('snapshot_qty', line)

    def test_02_save_lines(self):
        from models.physical_inventory import PhysicalInventoryCount
        from nodeone.core.platform.physical_count_service import upsert_lines

        payload = self._start()
        row = PhysicalInventoryCount.query.get(int(payload['id']))
        out = upsert_lines(
            self.oid,
            int(payload['id']),
            [
                {
                    'product_ref': self.ref,
                    'physical_qty': 18,
                    'client_line_id': 'line-1',
                    'counted_at': row.started_at,
                }
            ],
        )
        counted = [ln for ln in out['lines'] if ln['product_ref'] == self.ref][0]
        self.assertEqual(counted['physical_qty'], 18.0)
        self.assertEqual(counted['client_line_id'], 'line-1')

    def test_03_complete_does_not_change_stock(self):
        from models.physical_inventory import PhysicalInventoryCount
        from nodeone.core.platform import inventory_service as inv
        from nodeone.core.platform.physical_count_service import complete_count, upsert_lines

        before = inv.get_on_hand(self.oid, self.ref, warehouse_org_unit_id=int(self.wh['id']))
        payload = self._start()
        row = PhysicalInventoryCount.query.get(int(payload['id']))
        upsert_lines(
            self.oid,
            int(payload['id']),
            [{'product_ref': self.ref, 'physical_qty': 18, 'counted_at': row.started_at}],
        )
        complete_count(self.oid, int(payload['id']))
        after = inv.get_on_hand(self.oid, self.ref, warehouse_org_unit_id=int(self.wh['id']))
        self.assertEqual(before, after)

    def test_04_05_approve_idempotent(self):
        from models.physical_inventory import PhysicalInventoryCount
        from nodeone.core.platform import inventory_service as inv
        from nodeone.core.platform.physical_count_service import (
            approve_count,
            complete_count,
            upsert_lines,
        )

        payload = self._start()
        cid = int(payload['id'])
        row = PhysicalInventoryCount.query.get(cid)
        upsert_lines(
            self.oid,
            cid,
            [{'product_ref': self.ref, 'physical_qty': 18, 'counted_at': row.started_at}],
        )
        complete_count(self.oid, cid)
        first = approve_count(self.oid, cid, approved_by_user_id=202)
        second = approve_count(self.oid, cid, approved_by_user_id=202)
        self.assertEqual(first['status'], 'APPROVED')
        self.assertEqual(second['status'], 'APPROVED')
        self.assertEqual(
            inv.get_on_hand(self.oid, self.ref, warehouse_org_unit_id=int(self.wh['id'])),
            18.0,
        )
        kx = inv.kardex(self.oid, self.ref, warehouse_org_unit_id=int(self.wh['id']))
        adj = [r for r in kx if r.get('kind') == 'ADJUSTMENT_OUT']
        self.assertEqual(len(adj), 1)
        self.assertEqual(adj[0]['physical_count_id'], cid)

    def test_06_positive_difference(self):
        from models.physical_inventory import PhysicalInventoryCount
        from nodeone.core.platform import inventory_service as inv
        from nodeone.core.platform.physical_count_service import (
            approve_count,
            complete_count,
            upsert_lines,
        )

        payload = self._start()
        cid = int(payload['id'])
        row = PhysicalInventoryCount.query.get(cid)
        upsert_lines(
            self.oid,
            cid,
            [{'product_ref': self.ref, 'physical_qty': 22, 'counted_at': row.started_at}],
        )
        done = complete_count(self.oid, cid)
        line = [ln for ln in done['lines'] if ln['product_ref'] == self.ref][0]
        self.assertEqual(line['difference_qty'], 2.0)
        approve_count(self.oid, cid, approved_by_user_id=202)
        self.assertEqual(
            inv.get_on_hand(self.oid, self.ref, warehouse_org_unit_id=int(self.wh['id'])),
            22.0,
        )

    def test_07_negative_difference(self):
        from models.physical_inventory import PhysicalInventoryCount
        from nodeone.core.platform.physical_count_service import complete_count, upsert_lines

        payload = self._start()
        cid = int(payload['id'])
        row = PhysicalInventoryCount.query.get(cid)
        upsert_lines(
            self.oid,
            cid,
            [{'product_ref': self.ref, 'physical_qty': 18, 'counted_at': row.started_at}],
        )
        done = complete_count(self.oid, cid)
        line = [ln for ln in done['lines'] if ln['product_ref'] == self.ref][0]
        self.assertEqual(line['difference_qty'], -2.0)

    def test_08_zero_difference_no_movement(self):
        from models.physical_inventory import PhysicalInventoryCount
        from nodeone.core.platform import inventory_service as inv
        from nodeone.core.platform.physical_count_service import (
            approve_count,
            complete_count,
            upsert_lines,
        )

        payload = self._start()
        cid = int(payload['id'])
        row = PhysicalInventoryCount.query.get(cid)
        upsert_lines(
            self.oid,
            cid,
            [{'product_ref': self.ref, 'physical_qty': 20, 'counted_at': row.started_at}],
        )
        complete_count(self.oid, cid)
        out = approve_count(self.oid, cid, approved_by_user_id=202)
        self.assertEqual(out.get('adjustments'), [])
        kx = inv.kardex(self.oid, self.ref, warehouse_org_unit_id=int(self.wh['id']))
        self.assertFalse(any(r.get('physical_count_id') == cid for r in kx))

    def test_09_sale_during_count(self):
        from models.physical_inventory import PhysicalInventoryCount
        from nodeone.core.platform import inventory_service as inv
        from nodeone.core.platform.physical_count_service import (
            approve_count,
            complete_count,
            upsert_lines,
        )

        payload = self._start()
        cid = int(payload['id'])
        row = PhysicalInventoryCount.query.get(cid)
        upsert_lines(
            self.oid,
            cid,
            [{'product_ref': self.ref, 'physical_qty': 18, 'counted_at': row.started_at}],
        )
        inv.record_movement(
            self.oid,
            product_ref=self.ref,
            kind='SALE',
            quantity=3,
            warehouse_org_unit_id=int(self.wh['id']),
            source_system='EP1',
            source_event_id=f'sale-during-{cid}',
        )
        done = complete_count(self.oid, cid)
        line = [ln for ln in done['lines'] if ln['product_ref'] == self.ref][0]
        self.assertEqual(line['expected_qty'], 20.0)
        self.assertEqual(line['difference_qty'], -2.0)
        approve_count(self.oid, cid, approved_by_user_id=202)
        # 20 - 3 venta - 2 ajuste = 15
        self.assertEqual(
            inv.get_on_hand(self.oid, self.ref, warehouse_org_unit_id=int(self.wh['id'])),
            15.0,
        )

    def test_10_negative_stock_allowed(self):
        from nodeone.core.platform import inventory_service as inv

        inv.set_stock_policy(self.oid, 'BLOCK_NEGATIVE')
        result = inv.record_movement(
            self.oid,
            product_ref=self.ref,
            kind='SALE',
            quantity=25,
            warehouse_org_unit_id=int(self.wh['id']),
            source_system='EP1',
            source_event_id='neg-sale-1',
        )
        self.assertEqual(result['status'], 'applied')
        self.assertTrue(result['stock_negative'])
        self.assertEqual(
            inv.get_on_hand(self.oid, self.ref, warehouse_org_unit_id=int(self.wh['id'])),
            -5.0,
        )

    def test_11_offline_retry_count(self):
        client = f'apk-{uuid.uuid4().hex[:10]}'
        a = self._start(client_count_id=client)
        b = self._start(client_count_id=client)
        self.assertEqual(a['id'], b['id'])

    def test_12_retry_line(self):
        from models.physical_inventory import PhysicalInventoryCount
        from nodeone.core.platform.physical_count_service import upsert_lines

        payload = self._start()
        cid = int(payload['id'])
        row = PhysicalInventoryCount.query.get(cid)
        body = [
            {
                'product_ref': self.ref,
                'physical_qty': 17,
                'client_line_id': 'dev-line-9',
                'counted_at': row.started_at,
            }
        ]
        upsert_lines(self.oid, cid, body)
        again = upsert_lines(self.oid, cid, body)
        lines = [ln for ln in again['lines'] if ln['client_line_id'] == 'dev-line-9']
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['physical_qty'], 17.0)

    def test_13_org_isolation(self):
        from nodeone.core.platform.physical_count_service import PhysicalCountError, get_count

        payload = self._start()
        with self.assertRaises(PhysicalCountError):
            get_count(self.oid_b, int(payload['id']))

    def test_14_warehouse_isolation(self):
        from nodeone.core.platform import inventory_service as inv
        from nodeone.core.platform.physical_count_service import PhysicalCountError, start_count

        other = inv.create_warehouse(self.oid, unit_ref='barra', name='Barra')
        payload = start_count(
            self.oid,
            warehouse_org_unit_id=int(other['id']),
            created_by_user_id=101,
        )
        self.assertEqual(payload['warehouse_org_unit_id'], int(other['id']))
        with self.assertRaises(PhysicalCountError):
            start_count(self.oid, warehouse_org_unit_id=int(self.wh_b['id']))

    def test_15_sale_deduct_idempotent(self):
        from nodeone.core.commerce.constants import STOCK_MOVEMENT_DEDUCT
        from nodeone.core.commerce.order import OrderService
        from nodeone.core.platform import inventory_service as inv
        from nodeone.core.platform.connected_inventory import apply_connected_order_movement

        dto = OrderService.create(
            self.oid,
            {
                'lines': [
                    {
                        'product_ref': self.ref,
                        'description': 'Atlas',
                        'quantity': 2,
                        'unit_price': 1,
                    }
                ]
            },
        )
        a = apply_connected_order_movement(self.oid, dto.order_ref, STOCK_MOVEMENT_DEDUCT)
        b = apply_connected_order_movement(self.oid, dto.order_ref, STOCK_MOVEMENT_DEDUCT)
        self.assertEqual(a['applied'], 1)
        self.assertEqual(b['applied'], 1)
        self.assertEqual(
            inv.get_on_hand(self.oid, self.ref, warehouse_org_unit_id=int(self.wh['id'])),
            18.0,
        )

    def test_16_return_restores(self):
        from nodeone.core.commerce.constants import STOCK_MOVEMENT_DEDUCT, STOCK_MOVEMENT_RETURN
        from nodeone.core.commerce.order import OrderService
        from nodeone.core.platform import inventory_service as inv
        from nodeone.core.platform.connected_inventory import apply_connected_order_movement

        dto = OrderService.create(
            self.oid,
            {
                'lines': [
                    {
                        'product_ref': self.ref,
                        'description': 'Atlas',
                        'quantity': 4,
                        'unit_price': 1,
                    }
                ]
            },
        )
        apply_connected_order_movement(self.oid, dto.order_ref, STOCK_MOVEMENT_DEDUCT)
        apply_connected_order_movement(self.oid, dto.order_ref, STOCK_MOVEMENT_RETURN)
        self.assertEqual(
            inv.get_on_hand(self.oid, self.ref, warehouse_org_unit_id=int(self.wh['id'])),
            20.0,
        )

    def test_17_kardex_trace(self):
        from models.physical_inventory import PhysicalInventoryCount
        from nodeone.core.platform import inventory_service as inv
        from nodeone.core.platform.physical_count_service import (
            approve_count,
            complete_count,
            upsert_lines,
        )

        payload = self._start()
        cid = int(payload['id'])
        row = PhysicalInventoryCount.query.get(cid)
        upsert_lines(
            self.oid,
            cid,
            [{'product_ref': self.ref, 'physical_qty': 18, 'counted_at': row.started_at}],
        )
        complete_count(self.oid, cid)
        approve_count(self.oid, cid, approved_by_user_id=202)
        kx = inv.kardex(self.oid, self.ref, warehouse_org_unit_id=int(self.wh['id']))
        traced = [r for r in kx if r.get('physical_count_id') == cid]
        self.assertEqual(len(traced), 1)
        self.assertEqual(traced[0]['kind'], 'ADJUSTMENT_OUT')
        self.assertEqual(traced[0]['salida'], 2.0)

    def test_cannot_self_approve(self):
        from models.physical_inventory import PhysicalInventoryCount
        from nodeone.core.platform.physical_count_service import (
            PhysicalCountError,
            approve_count,
            complete_count,
            upsert_lines,
        )

        payload = self._start()
        cid = int(payload['id'])
        row = PhysicalInventoryCount.query.get(cid)
        upsert_lines(
            self.oid,
            cid,
            [{'product_ref': self.ref, 'physical_qty': 18, 'counted_at': row.started_at}],
        )
        complete_count(self.oid, cid)
        with self.assertRaises(PhysicalCountError):
            approve_count(self.oid, cid, approved_by_user_id=101)

    def test_conversion_not_improvised(self):
        from nodeone.core.platform.inventory_service import InventoryError, convert_closed_to_open

        with self.assertRaises(InventoryError) as ctx:
            convert_closed_to_open(
                self.oid,
                closed_product_ref=self.ref,
                open_product_ref='RON-ML',
                closed_quantity=1,
                open_quantity=750,
            )
        self.assertIn('uom_conversion_not_implemented', str(ctx.exception))

    def test_blind_catalog_omits_on_hand(self):
        from nodeone.core.platform.physical_count_service import list_location_products

        items = list_location_products(self.oid, int(self.wh['id']), blind=True)
        self.assertTrue(items)
        self.assertNotIn('quantity_on_hand', items[0])


if __name__ == '__main__':
    unittest.main()
