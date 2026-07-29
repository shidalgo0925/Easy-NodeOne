"""Motor comercial de planes EPosOne."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestCommercialPlans(unittest.TestCase):
    def test_plan_prices_and_order(self):
        from nodeone.core.platform.commercial_plans import list_commercial_plans

        plans = list_commercial_plans()
        self.assertEqual([p['code'] for p in plans], ['starter', 'business', 'enterprise'])
        self.assertEqual(plans[0]['price_monthly'], 29.95)
        self.assertEqual(plans[1]['price_monthly'], 49.95)
        self.assertEqual(plans[2]['price_monthly'], 79.95)

    def test_kds_locked_on_starter_available_on_business(self):
        from nodeone.core.platform.commercial_plans import (
            feature_nav_state_for_plan,
            upgrade_message,
        )

        self.assertEqual(feature_nav_state_for_plan('starter', 'kds'), 'locked')
        self.assertEqual(feature_nav_state_for_plan('business', 'kds'), 'available')
        msg = upgrade_message(current_plan_code='starter', feature='kds')
        self.assertEqual(msg['state'], 'locked')
        self.assertEqual(msg['target_plan']['code'], 'business')
        self.assertIn('49.95', msg['body'])

    def test_analytics_coming_soon(self):
        from nodeone.core.platform.commercial_plans import feature_nav_state_for_plan

        self.assertEqual(feature_nav_state_for_plan('enterprise', 'analytics'), 'coming_soon')

    def test_entitlement_template_uses_commercial(self):
        from nodeone.core.platform.entitlement_plans import get_plan_template

        starter = get_plan_template('eposone', 'starter')
        self.assertFalse(starter['features']['kds'])
        self.assertEqual(starter['resource_limits']['registers'], 1)
        business = get_plan_template('eposone', 'professional')  # alias
        self.assertTrue(business['features']['kds'])
        self.assertEqual(business['resource_limits']['registers'], 5)

    def test_count_usage_rollbacks_after_sql_failure(self):
        """Regression Mi plan: fallo al contar cajeros no debe abortar la txn de la request."""
        from sqlalchemy.exc import ProgrammingError
        from unittest.mock import MagicMock

        from app import app, db
        from nodeone.core.platform.commercial_plans import _count_usage
        from sqlalchemy import text

        boom = ProgrammingError('SELECT', {}, Exception('relation missing'))
        with app.app_context():
            db.session.rollback()
            with patch(
                'models.eposone_cashier.EposoneCashierCredential.query',
                new_callable=MagicMock,
            ) as q:
                q.filter_by.return_value.count.side_effect = boom
                usage = _count_usage(1)
            self.assertIn('cashiers', usage)
            # Sesión usable tras el best-effort
            self.assertEqual(db.session.execute(text('SELECT 1')).scalar(), 1)


class TestNavShowsLockedFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    def test_kds_serialized_as_locked_without_org_defaults_starter(self):
        from nodeone.core.nav_menu import build_nav_context
        from nodeone.core.platform.app_nav import serialize_nav_sidebar
        from nodeone.modules.eposone.nav import build_nav_tree

        ctx = build_nav_context(
            nav_can=lambda _p: True,
            saas_module_enabled=lambda code: code in {'eposone', 'sales'},
            saas_module_enabled_chain=lambda *_c: True,
            has_view_endpoint=lambda _e: True,
            show_academic_admin_nav=False,
            office365_module_enabled=False,
            show_platform_admin_nav=False,
            is_platform_admin=False,
            is_advisor=False,
            show_tenant_admin_menu=True,
        )
        with self.app.test_request_context('/admin/eposone/dashboard'):
            with patch(
                'nodeone.core.platform.nav_effective_access.current_nav_organization_id',
                return_value=None,
            ):
                rows = serialize_nav_sidebar(build_nav_tree(ctx), ctx)
        mas = next(r for r in rows if r['id'] == 'mas')
        kds = next(c for c in mas['children'] if c['id'] == 'kds')
        self.assertTrue(kds.get('locked'))
        self.assertIn('upgrade', (kds.get('url') or ''))


if __name__ == '__main__':
    unittest.main()
