"""Tests EPosOne V4 Sprint 5 — Vincular con EasyNodeOne."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


def _seed_local_business():
    from nodeone.core.eposone_domain.first_start import (
        CreateBusinessInput,
        wizard_from_memory_bundle,
    )
    from nodeone.core.eposone_domain.memory import MemoryProviderBundle
    from nodeone.core.eposone_domain.models import Customer, Order, OrderLine, Product

    local = MemoryProviderBundle()
    wiz = wizard_from_memory_bundle(local)
    wiz.create_local_business(
        CreateBusinessInput(
            business_name='Café Local',
            currency='USD',
            admin_email='admin@cafe.local',
        )
    )
    local.products.upsert(
        Product(
            id='p-local',
            name='Espresso',
            unit_price=2.0,
            currency='USD',
            product_type='simple',
            active=True,
            track_stock=True,
            created_at='2026-07-09T12:00:00Z',
            sku='ESP-01',
        )
    )
    local.customers.upsert(
        Customer(
            id='c-local',
            display_name='Cliente Uno',
            active=True,
            created_at='2026-07-09T12:00:00Z',
            email='cliente@test.local',
        )
    )
    local.orders.create(
        Order(
            id='o-local',
            order_ref='L-1',
            business_id=local.config.get_business().id,
            branch_id=local.config.get_branches()[0].id,
            operational_status='confirmed',
            payment_status='paid',
            fiscal_status='not_required',
            currency='USD',
            subtotal=2.0,
            tax_total=0,
            discount_total=0,
            grand_total=2.0,
            amount_paid=2.0,
            version=1,
            lines=(
                OrderLine(
                    id='ol1',
                    description='Espresso',
                    quantity=1,
                    unit_price=2.0,
                    line_total=2.0,
                    line_status='pending',
                    product_id='p-local',
                ),
            ),
            created_at='2026-07-09T12:00:00Z',
            customer_id='c-local',
        )
    )
    local.inventory.adjust(
        'p-local',
        local.config.get_branches()[0].id,
        delta_on_hand=10,
        updated_at='2026-07-09T12:00:00Z',
    )
    return local


class TestLinkLabelAndAvailability(unittest.TestCase):
    def test_label_and_not_migration(self):
        from nodeone.core.eposone_domain.link_en1 import LABEL_LINK_EN1, LinkEn1Assistant

        self.assertEqual(LinkEn1Assistant.label(), LABEL_LINK_EN1)
        self.assertNotIn('migr', LABEL_LINK_EN1.lower())

    def test_unavailable_when_not_local(self):
        from nodeone.core.eposone_domain.first_start import FirstStartState, MODE_PLATFORM
        from nodeone.core.eposone_domain.link_en1 import assistant_from_memory_bundles
        from nodeone.core.eposone_domain.memory import MemoryProviderBundle

        local = MemoryProviderBundle()
        target = MemoryProviderBundle()
        asst = assistant_from_memory_bundles(
            local,
            target,
            first_start_state=FirstStartState(
                completed=True,
                operating_mode=MODE_PLATFORM,
                en1_organization_id='1',
                has_en1_credentials=True,
            ),
        )
        self.assertFalse(asst.is_available())


class TestLinkHappyPath(unittest.TestCase):
    def test_full_flow_local_to_platform(self):
        from nodeone.core.eposone_domain.first_start import MODE_LOCAL, MODE_PLATFORM
        from nodeone.core.eposone_domain.link_en1 import assistant_from_memory_bundles
        from nodeone.core.eposone_domain.memory import MemoryProviderBundle

        local = _seed_local_business()
        self.assertEqual(local.store.first_start.operating_mode, MODE_LOCAL)
        target = MemoryProviderBundle()
        asst = assistant_from_memory_bundles(local, target)

        self.assertTrue(asst.is_available())
        asst.start()
        asst.grant_access(access_granted=True)
        asst.select_organization('99')
        asst.select_enterprise('create_en1')
        asst.select_branch()
        asst.select_register()
        result = asst.run_transfer()

        self.assertEqual(result.link_state.phase, 'completed')
        self.assertEqual(result.first_start_state.operating_mode, MODE_PLATFORM)
        self.assertEqual(result.first_start_state.en1_organization_id, '99')
        self.assertGreaterEqual(result.transfer.products, 1)
        self.assertGreaterEqual(result.transfer.customers, 1)
        self.assertGreaterEqual(result.transfer.orders, 1)
        self.assertFalse(asst.is_available())
        # Target received catalog
        self.assertTrue(any(p.sku == 'ESP-01' for p in target.products.list(active_only=False)))
        self.assertTrue(
            any(c.email == 'cliente@test.local' for c in target.customers.list(active_only=False))
        )

    def test_link_existing_enterprise(self):
        from nodeone.core.eposone_domain.link_en1 import assistant_from_memory_bundles
        from nodeone.core.eposone_domain.memory import MemoryProviderBundle
        from nodeone.core.eposone_domain.models import BusinessConfig

        local = _seed_local_business()
        target = MemoryProviderBundle()
        target.config.upsert_config(
            BusinessConfig(
                id='en1-biz-1',
                name='Empresa EN1',
                currency='USD',
                created_at='2026-07-01T00:00:00Z',
            ),
            branches=[],
            registers=[],
        )
        asst = assistant_from_memory_bundles(local, target)
        asst.start()
        asst.grant_access(access_granted=True)
        asst.select_organization('1')
        asst.select_enterprise('link_existing', en1_business_id='en1-biz-1')
        asst.select_branch()
        asst.select_register()
        result = asst.run_transfer()
        self.assertEqual(result.link_state.en1_business_id, 'en1-biz-1')
        self.assertEqual(result.first_start_state.business_id, 'en1-biz-1')


class TestSkuConflictAndResume(unittest.TestCase):
    def test_sku_merge_policy(self):
        from nodeone.core.eposone_domain.link_en1 import assistant_from_memory_bundles
        from nodeone.core.eposone_domain.memory import MemoryProviderBundle
        from nodeone.core.eposone_domain.models import Product

        local = _seed_local_business()
        target = MemoryProviderBundle()
        target.products.upsert(
            Product(
                id='p-remote',
                name='Old Espresso',
                unit_price=1.0,
                currency='USD',
                product_type='simple',
                active=True,
                track_stock=True,
                created_at='2026-07-01T00:00:00Z',
                sku='ESP-01',
            )
        )
        asst = assistant_from_memory_bundles(local, target)
        asst.start()
        asst.grant_access(access_granted=True)
        asst.select_organization('1')
        asst.select_enterprise('create_en1')
        asst.select_branch()
        # Force merge policy (default)
        st = asst._get_link()
        from dataclasses import replace

        asst._set_link(replace(st, sku_policy='merge'))
        asst.select_register()
        result = asst.run_transfer()
        self.assertEqual(result.transfer.sku_merged, 1)
        remotes = [p for p in target.products.list(active_only=False) if p.sku == 'ESP-01']
        self.assertEqual(len(remotes), 1)
        self.assertEqual(remotes[0].name, 'Espresso')

    def test_resume_after_failed(self):
        from nodeone.core.eposone_domain.link_en1 import assistant_from_memory_bundles
        from nodeone.core.eposone_domain.memory import MemoryProviderBundle

        local = _seed_local_business()
        target = MemoryProviderBundle()
        asst = assistant_from_memory_bundles(local, target)
        asst.start()
        asst.mark_failed('network')
        self.assertEqual(asst.current_state().phase, 'failed')
        resumed = asst.resume()
        self.assertEqual(resumed.phase, 'awaiting_login')

    def test_export_envelope(self):
        from nodeone.core.eposone_domain.link_en1 import assistant_from_memory_bundles
        from nodeone.core.eposone_domain.memory import MemoryProviderBundle

        local = _seed_local_business()
        asst = assistant_from_memory_bundles(local, MemoryProviderBundle())
        env = asst.export_local_envelope()
        self.assertEqual(env['schema_version'], 1)
        self.assertEqual(env['mode_at_export'], 'local')
        self.assertEqual(env['business']['name'], 'Café Local')
        self.assertGreaterEqual(len(env['products']), 1)


class TestPhaseGuards(unittest.TestCase):
    def test_wrong_phase(self):
        from nodeone.core.eposone_domain.link_en1 import (
            LinkEn1Error,
            assistant_from_memory_bundles,
        )
        from nodeone.core.eposone_domain.memory import MemoryProviderBundle

        local = _seed_local_business()
        asst = assistant_from_memory_bundles(local, MemoryProviderBundle())
        with self.assertRaises(LinkEn1Error):
            asst.grant_access(access_granted=True)


if __name__ == '__main__':
    unittest.main()
