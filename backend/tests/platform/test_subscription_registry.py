"""Tests ADR-014 — Subscription Registry V1."""

from __future__ import annotations

import sys
import unittest
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestSubscriptionRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app, db
        from nodeone.services.ets_subscription_schema import ensure_ets_product_subscription_schema

        cls.app = app
        cls.db = db
        with app.app_context():
            ensure_ets_product_subscription_schema(db, db.engine)

    def setUp(self):
        from models.ets_product_subscription import EtsProductSubscription
        from models.saas import SaasOrganization
        from nodeone.core.platform.context_resolver import reload_config
        from nodeone.core.platform.product_registry import reload_product_registry

        reload_config()
        reload_product_registry()
        self.ctx = self.app.app_context()
        self.ctx.push()
        suffix = uuid.uuid4().hex[:10]
        self.org_a = SaasOrganization(name=f'SubTest A {suffix}', subdomain=f'subta{suffix}')
        self.org_b = SaasOrganization(name=f'SubTest B {suffix}', subdomain=f'subtb{suffix}')
        self.db.session.add(self.org_a)
        self.db.session.add(self.org_b)
        self.db.session.commit()
        self.oid_a = int(self.org_a.id)
        self.oid_b = int(self.org_b.id)
        # limpia filas residuales
        EtsProductSubscription.query.filter(
            EtsProductSubscription.organization_id.in_([self.oid_a, self.oid_b])
        ).delete(synchronize_session=False)
        self.db.session.commit()

    def tearDown(self):
        from models.ets_product_subscription import EtsProductSubscription
        from models.saas import SaasOrganization

        try:
            EtsProductSubscription.query.filter(
                EtsProductSubscription.organization_id.in_([self.oid_a, self.oid_b])
            ).delete(synchronize_session=False)
            SaasOrganization.query.filter(
                SaasOrganization.id.in_([self.oid_a, self.oid_b])
            ).delete(synchronize_session=False)
            self.db.session.commit()
        except Exception:
            self.db.session.rollback()
        self.ctx.pop()

    def test_create_trial_and_list_products(self):
        from nodeone.core.platform.subscription_registry import SubscriptionRegistry

        trial_end = datetime.utcnow() + timedelta(days=15)
        with patch('nodeone.core.platform.subscription_registry._audit'):
            rec = SubscriptionRegistry.create_trial(
                self.oid_a, 'eposone', trial_end, sync_licenses=False
            )
        self.assertEqual(rec.status, 'trial')
        self.assertEqual(rec.product_code, 'eposone')
        self.assertTrue(SubscriptionRegistry.has_product(self.oid_a, 'eposone'))
        products = SubscriptionRegistry.list_tenant_products(self.oid_a)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['product_code'], 'eposone')
        self.assertEqual(products[0]['product']['name'], 'EPosOne')
        self.assertEqual(products[0]['product']['primary_domain'], 'eposone.easytech.services')

    def test_reject_unknown_product(self):
        from nodeone.core.platform.subscription_registry import SubscriptionError, SubscriptionRegistry

        with self.assertRaises(SubscriptionError) as ctx:
            SubscriptionRegistry.create_trial(
                self.oid_a, 'no-existe-xyz', datetime.utcnow() + timedelta(days=1)
            )
        self.assertEqual(ctx.exception.code, 'unknown_product')

    def test_reject_platform_product(self):
        from nodeone.core.platform.subscription_registry import SubscriptionError, SubscriptionRegistry

        with self.assertRaises(SubscriptionError) as ctx:
            SubscriptionRegistry.activate(self.oid_a, 'en1')
        self.assertEqual(ctx.exception.code, 'not_subscribable')

    def test_reject_duplicate_active(self):
        from nodeone.core.platform.subscription_registry import SubscriptionError, SubscriptionRegistry

        trial_end = datetime.utcnow() + timedelta(days=15)
        with patch('nodeone.core.platform.subscription_registry._audit'):
            SubscriptionRegistry.create_trial(self.oid_a, 'eposone', trial_end)
            with self.assertRaises(SubscriptionError) as ctx:
                SubscriptionRegistry.create_trial(self.oid_a, 'eposone', trial_end)
        self.assertEqual(ctx.exception.code, 'duplicate_active')

    def test_activate_suspend_cancel(self):
        from nodeone.core.platform.subscription_registry import SubscriptionRegistry

        with patch('nodeone.core.platform.subscription_registry._audit'):
            with patch('nodeone.core.platform.subscription_registry._sync_licenses_minimal'):
                SubscriptionRegistry.activate(self.oid_a, 'epayroll')
                self.assertTrue(SubscriptionRegistry.has_product(self.oid_a, 'epayroll'))
                SubscriptionRegistry.suspend(self.oid_a, 'epayroll', reason='test', sync_licenses=False)
                self.assertFalse(SubscriptionRegistry.has_product(self.oid_a, 'epayroll'))
                sus = SubscriptionRegistry.get_for_tenant_product(self.oid_a, 'epayroll')
                self.assertEqual(sus.status, 'suspended')
                SubscriptionRegistry.cancel(self.oid_a, 'epayroll', reason='bye', sync_licenses=False)
                can = SubscriptionRegistry.get_for_tenant_product(self.oid_a, 'epayroll')
                self.assertEqual(can.status, 'cancelled')

    def test_tenant_isolation(self):
        from nodeone.core.platform.subscription_registry import SubscriptionError, SubscriptionRegistry

        with patch('nodeone.core.platform.subscription_registry._audit'):
            SubscriptionRegistry.activate(self.oid_a, 'eposone')
        self.assertFalse(SubscriptionRegistry.has_product(self.oid_b, 'eposone'))
        with self.assertRaises(SubscriptionError) as ctx:
            SubscriptionRegistry.list_for_tenant(self.oid_a, scope_organization_id=self.oid_b)
        self.assertEqual(ctx.exception.code, 'tenant_isolation')

    def test_product_registry_not_copied_to_db(self):
        from models.ets_product_subscription import EtsProductSubscription
        from nodeone.core.platform.subscription_registry import SubscriptionRegistry

        with patch('nodeone.core.platform.subscription_registry._audit'):
            SubscriptionRegistry.activate(self.oid_a, 'eposone')
        row = EtsProductSubscription.query.filter_by(
            organization_id=self.oid_a, product_code='eposone'
        ).first()
        self.assertIsNotNone(row)
        cols = {c.name for c in row.__table__.columns}
        self.assertNotIn('name', cols)
        self.assertNotIn('primary_domain', cols)
        self.assertNotIn('app_ids', cols)
        self.assertNotIn('theme', cols)

    def test_context_resolver_unchanged(self):
        from nodeone.core.platform.app_registry import get_application
        from nodeone.core.platform.context_resolver import ContextResolver

        self.assertEqual(
            ContextResolver.resolve_product_code('eposone.easytech.services'),
            'eposone',
        )
        self.assertIsNotNone(get_application('eposone'))


if __name__ == '__main__':
    unittest.main()
