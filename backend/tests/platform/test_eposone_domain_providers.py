"""Tests EPosOne V4 Sprint 3 — data providers (Memory + SQLite + mapeo API)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestPortsRuntimeCheckable(unittest.TestCase):
    def test_memory_bundle_satisfies_protocols(self):
        from nodeone.core.eposone_domain.memory import MemoryProviderBundle
        from nodeone.core.eposone_domain.ports import (
            CashShiftRepository,
            ConfigRepository,
            CustomerRepository,
            EmployeeRepository,
            InventoryRepository,
            OrderRepository,
            ProductRepository,
            PromotionRepository,
        )

        b = MemoryProviderBundle()
        self.assertIsInstance(b.products, ProductRepository)
        self.assertIsInstance(b.customers, CustomerRepository)
        self.assertIsInstance(b.employees, EmployeeRepository)
        self.assertIsInstance(b.orders, OrderRepository)
        self.assertIsInstance(b.cash_shifts, CashShiftRepository)
        self.assertIsInstance(b.inventory, InventoryRepository)
        self.assertIsInstance(b.config, ConfigRepository)
        self.assertIsInstance(b.promotions, PromotionRepository)


class TestMemoryProviders(unittest.TestCase):
    def setUp(self):
        from nodeone.core.eposone_domain.memory import MemoryProviderBundle

        self.b = MemoryProviderBundle()

    def test_product_upsert_list_deactivate(self):
        from nodeone.core.eposone_domain.models import Product

        p = self.b.products.upsert(
            Product(
                id='p1',
                name='Café',
                unit_price=2.5,
                currency='USD',
                product_type='simple',
                active=True,
                track_stock=True,
                created_at='2026-07-09T12:00:00Z',
                sku='CAF-01',
            )
        )
        self.assertEqual(p.id, 'p1')
        self.assertEqual(len(self.b.products.list()), 1)
        deactivated = self.b.products.deactivate('p1')
        self.assertIsNotNone(deactivated)
        assert deactivated is not None
        self.assertFalse(deactivated.active)
        self.assertEqual(len(self.b.products.list(active_only=True)), 0)
        self.assertEqual(len(self.b.products.list(active_only=False)), 1)

    def test_order_create_idempotent_and_payment(self):
        from nodeone.core.eposone_domain.models import Order, OrderLine, Payment

        order = Order(
            id='',
            order_ref='ORD-1',
            business_id='biz1',
            branch_id='br1',
            operational_status='draft',
            payment_status='unpaid',
            fiscal_status='not_required',
            currency='USD',
            subtotal=10.0,
            tax_total=0.0,
            discount_total=0.0,
            grand_total=10.0,
            amount_paid=0.0,
            version=1,
            lines=(
                OrderLine(
                    id='l1',
                    description='Item',
                    quantity=1,
                    unit_price=10,
                    line_total=10,
                    line_status='pending',
                ),
            ),
            created_at='2026-07-09T12:00:00Z',
            idempotency_key='idem-1',
        )
        a = self.b.orders.create(order, idempotency_key='idem-1')
        b = self.b.orders.create(order, idempotency_key='idem-1')
        self.assertEqual(a.id, b.id)
        paid = self.b.orders.add_payment(
            a.id,
            Payment(
                id='',
                order_id=a.id,
                payment_ref='PAY-1',
                status='captured',
                payment_type='cash',
                amount=10.0,
                currency='USD',
            ),
        )
        self.assertEqual(paid.payment_status, 'paid')
        self.assertEqual(paid.amount_paid, 10.0)

    def test_cash_shift_one_open_per_register(self):
        from nodeone.core.eposone_domain.models import CashShift

        s = CashShift(
            id='',
            register_id='reg1',
            branch_id='br1',
            opened_by_employee_id='e1',
            status='open',
            opening_float=100.0,
            currency='USD',
            opened_at='2026-07-09T12:00:00Z',
        )
        opened = self.b.cash_shifts.open(s)
        with self.assertRaises(ValueError):
            self.b.cash_shifts.open(s)
        closed = self.b.cash_shifts.close(
            opened.id,
            closed_by_employee_id='e1',
            closing_counted=120.0,
            expected_cash=110.0,
            closed_at='2026-07-09T20:00:00Z',
        )
        self.assertEqual(closed.status, 'closed')
        self.assertIsNone(self.b.cash_shifts.get_open('reg1'))

    def test_config_and_inventory(self):
        from nodeone.core.eposone_domain.models import Branch, BusinessConfig, Register

        biz = self.b.config.upsert_config(
            BusinessConfig(
                id='biz1',
                name='Demo Cafe',
                currency='USD',
                created_at='2026-07-09T12:00:00Z',
            ),
            branches=[
                Branch(id='br1', business_id='biz1', name='Centro', is_default=True),
            ],
            registers=[
                Register(id='reg1', branch_id='br1', name='Caja 1', is_default=True),
            ],
        )
        self.assertEqual(biz.name, 'Demo Cafe')
        self.assertEqual(len(self.b.config.get_branches()), 1)
        bal = self.b.inventory.adjust(
            'p1', 'br1', delta_on_hand=5, updated_at='2026-07-09T12:00:00Z'
        )
        self.assertEqual(bal.quantity_on_hand, 5.0)
        self.assertEqual(len(self.b.inventory.list_alerts(below=10)), 1)


class TestSqliteProviders(unittest.TestCase):
    def setUp(self):
        from nodeone.core.eposone_domain.sqlite import SqliteProviderBundle

        self._tmp = tempfile.TemporaryDirectory()
        path = Path(self._tmp.name) / 'eposone_local.db'
        self.b = SqliteProviderBundle(path)

    def tearDown(self):
        self._tmp.cleanup()

    def test_sqlite_product_and_order_roundtrip(self):
        from nodeone.core.eposone_domain.models import Order, OrderLine, Product
        from nodeone.core.eposone_domain.ports import OrderRepository, ProductRepository

        self.assertIsInstance(self.b.products, ProductRepository)
        self.assertIsInstance(self.b.orders, OrderRepository)

        p = self.b.products.upsert(
            Product(
                id='p-sqlite',
                name='Té',
                unit_price=1.5,
                currency='USD',
                product_type='simple',
                active=True,
                track_stock=False,
                created_at='2026-07-09T12:00:00Z',
            )
        )
        self.assertEqual(self.b.products.get(p.id).name, 'Té')

        order = self.b.orders.create(
            Order(
                id='',
                order_ref='S-1',
                business_id='biz',
                branch_id='br',
                operational_status='confirmed',
                payment_status='unpaid',
                fiscal_status='not_required',
                currency='USD',
                subtotal=1.5,
                tax_total=0,
                discount_total=0,
                grand_total=1.5,
                amount_paid=0,
                version=1,
                lines=(
                    OrderLine(
                        id='l1',
                        description='Té',
                        quantity=1,
                        unit_price=1.5,
                        line_total=1.5,
                        line_status='pending',
                        product_id=p.id,
                    ),
                ),
                created_at='2026-07-09T12:00:00Z',
            ),
            idempotency_key='sq-idem',
        )
        again = self.b.orders.create(
            Order(
                id='',
                order_ref='S-1b',
                business_id='biz',
                branch_id='br',
                operational_status='draft',
                payment_status='unpaid',
                fiscal_status='not_required',
                currency='USD',
                subtotal=0,
                tax_total=0,
                discount_total=0,
                grand_total=0,
                amount_paid=0,
                version=1,
                lines=(),
                created_at='2026-07-09T12:00:00Z',
            ),
            idempotency_key='sq-idem',
        )
        self.assertEqual(order.id, again.id)
        updated = self.b.orders.update_status(order.id, 'ready')
        self.assertEqual(updated.operational_status, 'ready')
        self.assertEqual(updated.version, 2)


class TestApiMapping(unittest.TestCase):
    def test_product_dto_mapping(self):
        from nodeone.core.eposone_domain.api import product_dto_to_portable

        dto = SimpleNamespace(
            id=42,
            product_ref='SKU-1',
            name='Burger',
            description=None,
            unit_price=8.5,
            currency='USD',
            product_type='good',
            status='active',
            tracks_inventory=True,
        )
        p = product_dto_to_portable(dto)
        self.assertEqual(p.id, '42')
        self.assertEqual(p.sku, 'SKU-1')
        self.assertEqual(p.product_type, 'simple')
        self.assertTrue(p.track_stock)

    def test_order_dto_mapping(self):
        from nodeone.core.eposone_domain.api import order_dto_to_portable

        line = SimpleNamespace(
            id=1,
            description='Item',
            quantity=2,
            unit_price=5,
            line_total=10,
            line_status='pending',
            product_ref='SKU-1',
        )
        dto = SimpleNamespace(
            id=99,
            order_ref='ORD-99',
            status='confirmed',
            payment_status='unpaid',
            fiscal_status='not_required',
            currency='USD',
            subtotal=10,
            tax_total=0,
            discount_total=0,
            grand_total=10,
            amount_paid=0,
            lines=(line,),
            created_at=None,
            branch_org_unit_id=7,
            pos_terminal_id=None,
            contact_id=3,
            promotion_ref=None,
            parent_order_id=None,
        )
        order = order_dto_to_portable(dto, business_id='1')
        self.assertEqual(order.id, '99')
        self.assertEqual(order.branch_id, '7')
        self.assertEqual(order.customer_id, '3')
        self.assertEqual(order.lines[0].product_id, 'SKU-1')


if __name__ == '__main__':
    unittest.main()
