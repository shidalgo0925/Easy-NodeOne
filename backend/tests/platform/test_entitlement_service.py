"""Tests ADR-016 — Entitlement Engine V1 (Paso 1)."""

from __future__ import annotations

import sys
import unittest
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestEntitlementService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app, db
        from nodeone.services.ets_entitlement_schema import ensure_ets_product_entitlement_schema
        from nodeone.services.ets_subscription_schema import ensure_ets_product_subscription_schema

        cls.app = app
        cls.db = db
        with app.app_context():
            ensure_ets_product_subscription_schema(db, db.engine)
            ensure_ets_product_entitlement_schema(db, db.engine)

    def setUp(self):
        from models.ets_product_entitlement import EtsProductEntitlement
        from models.ets_product_subscription import EtsProductSubscription
        from models.saas import SaasOrganization
        from nodeone.core.platform.context_resolver import reload_config
        from nodeone.core.platform.product_registry import reload_product_registry

        reload_config()
        reload_product_registry()
        self.ctx = self.app.app_context()
        self.ctx.push()
        suffix = uuid.uuid4().hex[:10]
        self.org = SaasOrganization(name=f'EntTest {suffix}', subdomain=f'entt{suffix}')
        self.db.session.add(self.org)
        self.db.session.commit()
        self.oid = int(self.org.id)
        EtsProductEntitlement.query.filter_by(organization_id=self.oid).delete(
            synchronize_session=False
        )
        EtsProductSubscription.query.filter_by(organization_id=self.oid).delete(
            synchronize_session=False
        )
        self.db.session.commit()

    def tearDown(self):
        from models.ets_product_entitlement import EtsProductEntitlement
        from models.ets_product_subscription import EtsProductSubscription
        from models.saas import SaasOrganization

        try:
            EtsProductEntitlement.query.filter_by(organization_id=self.oid).delete(
                synchronize_session=False
            )
            EtsProductSubscription.query.filter_by(organization_id=self.oid).delete(
                synchronize_session=False
            )
            SaasOrganization.query.filter_by(id=self.oid).delete(synchronize_session=False)
            self.db.session.commit()
        except Exception:
            self.db.session.rollback()
        self.ctx.pop()

    def _activate_sub(self):
        from nodeone.core.platform.subscription_registry import SubscriptionRegistry

        with patch('nodeone.core.platform.subscription_registry._audit'):
            return SubscriptionRegistry.activate(self.oid, 'eposone')

    def test_create_from_subscription_professional(self):
        from nodeone.core.platform.entitlement_service import EntitlementService

        self._activate_sub()
        with patch('nodeone.core.platform.entitlement_service._audit'):
            rec = EntitlementService.create_from_subscription(
                self.oid, 'eposone', plan_code='professional'
            )
        self.assertEqual(rec.product_code, 'eposone')
        # professional es alias comercial de business
        self.assertEqual(rec.plan_code, 'business')
        self.assertEqual(rec.effective_state, 'active')
        self.assertEqual(rec.effective_limits.get('pos'), 3)
        self.assertTrue(rec.features.get('kds'))
        self.assertFalse(rec.features.get('api'))
        self.assertTrue(rec.is_operable)

    def test_requires_subscription(self):
        from nodeone.core.platform.entitlement_service import EntitlementError, EntitlementService

        with self.assertRaises(EntitlementError) as ctx:
            EntitlementService.create_from_subscription(self.oid, 'eposone')
        self.assertEqual(ctx.exception.code, 'subscription_required')

    def test_overrides_without_new_plan(self):
        from nodeone.core.platform.entitlement_service import EntitlementService

        self._activate_sub()
        with patch('nodeone.core.platform.entitlement_service._audit'):
            EntitlementService.create_from_subscription(
                self.oid, 'eposone', plan_code='starter'
            )
            rec = EntitlementService.set_overrides(
                self.oid, 'eposone', {'tablets': 5, 'kds': True}
            )
        self.assertEqual(rec.plan_code, 'starter')
        self.assertEqual(rec.resource_limits.get('tablets'), 1)
        self.assertEqual(rec.effective_limits.get('tablets'), 5)
        self.assertTrue(EntitlementService.has_feature(self.oid, 'eposone', 'kds'))

    def test_has_capacity(self):
        from nodeone.core.platform.entitlement_service import EntitlementService

        self._activate_sub()
        with patch('nodeone.core.platform.entitlement_service._audit'):
            EntitlementService.create_from_subscription(
                self.oid, 'eposone', plan_code='starter'
            )
        self.assertTrue(EntitlementService.has_capacity(self.oid, 'eposone', 'pos', current_count=0))
        self.assertFalse(EntitlementService.has_capacity(self.oid, 'eposone', 'pos', current_count=1))
        self.assertTrue(EntitlementService.has_feature(self.oid, 'eposone', 'offline'))
        self.assertFalse(EntitlementService.has_feature(self.oid, 'eposone', 'api'))

    def test_enterprise_unlimited(self):
        from nodeone.core.platform.entitlement_service import EntitlementService

        self._activate_sub()
        with patch('nodeone.core.platform.entitlement_service._audit'):
            EntitlementService.create_from_subscription(
                self.oid, 'eposone', plan_code='enterprise'
            )
        self.assertTrue(
            EntitlementService.has_capacity(self.oid, 'eposone', 'pos', current_count=999)
        )
        self.assertTrue(EntitlementService.has_feature(self.oid, 'eposone', 'api'))

    def test_ensure_idempotent_and_sync(self):
        from nodeone.core.platform.entitlement_service import EntitlementService
        from nodeone.core.platform.subscription_registry import SubscriptionRegistry

        self._activate_sub()
        with patch('nodeone.core.platform.entitlement_service._audit'):
            with patch('nodeone.core.platform.subscription_registry._audit'):
                with patch('nodeone.core.platform.subscription_registry._sync_licenses_minimal'):
                    a = EntitlementService.ensure_for_subscription(
                        self.oid, 'eposone', plan_code='professional'
                    )
                    b = EntitlementService.ensure_for_subscription(self.oid, 'eposone')
                    self.assertEqual(a.id, b.id)
                    SubscriptionRegistry.suspend(
                        self.oid, 'eposone', reason='test', sync_licenses=False
                    )
                    c = EntitlementService.ensure_for_subscription(self.oid, 'eposone')
        self.assertEqual(c.effective_state, 'suspended')
        self.assertFalse(c.is_operable)

    def test_grace_state(self):
        from nodeone.core.platform.entitlement_service import EntitlementService

        self._activate_sub()
        with patch('nodeone.core.platform.entitlement_service._audit'):
            EntitlementService.create_from_subscription(self.oid, 'eposone')
            rec = EntitlementService.set_effective_state(self.oid, 'eposone', 'grace')
        self.assertEqual(rec.effective_state, 'grace')
        self.assertTrue(rec.is_operable)

    def test_tenant_isolation(self):
        from models.saas import SaasOrganization
        from nodeone.core.platform.entitlement_service import EntitlementError, EntitlementService

        other = SaasOrganization(
            name=f'EntOther {uuid.uuid4().hex[:8]}',
            subdomain=f'ento{uuid.uuid4().hex[:8]}',
        )
        self.db.session.add(other)
        self.db.session.commit()
        other_id = int(other.id)
        self._activate_sub()
        with patch('nodeone.core.platform.entitlement_service._audit'):
            EntitlementService.create_from_subscription(self.oid, 'eposone')
        with self.assertRaises(EntitlementError) as ctx:
            EntitlementService.list_for_tenant(self.oid, scope_organization_id=other_id)
        self.assertEqual(ctx.exception.code, 'tenant_isolation')
        SaasOrganization.query.filter_by(id=other_id).delete(synchronize_session=False)
        self.db.session.commit()


class TestEntitlementPlans(unittest.TestCase):
    def test_plan_templates(self):
        from nodeone.core.platform.entitlement_plans import get_plan_template, list_plan_codes

        codes = list_plan_codes('eposone')
        self.assertIn('starter', codes)
        self.assertIn('business', codes)
        self.assertIn('enterprise', codes)
        pro = get_plan_template('eposone', 'professional')
        self.assertEqual(pro['resource_limits']['registers'], 5)
        self.assertTrue(pro['features']['fiscal'])


if __name__ == '__main__':
    unittest.main()
