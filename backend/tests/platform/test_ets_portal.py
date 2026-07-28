"""Tests Portal ETS MVP — PortalService (Subscription + Product registries)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestPortalService(unittest.TestCase):
    def test_open_url_from_product_registry(self):
        from nodeone.modules.ets_portal.portal_service import PortalService

        url = PortalService.open_url_for_product('eposone')
        self.assertEqual(url, 'https://eposone.easytech.services')
        self.assertIsNone(PortalService.open_url_for_product('no-such-product'))

    def test_list_filters_and_enrichment(self):
        from nodeone.modules.ets_portal.portal_service import PortalService

        fake = [
            {
                'product_code': 'eposone',
                'subscription_status': 'trial',
                'is_entitled': True,
                'starts_at': None,
                'ends_at': None,
                'trial_ends_at': '2026-08-01T00:00:00Z',
                'product': {
                    'name': 'EPosOne',
                    'primary_domain': 'eposone.easytech.services',
                    'icon': '',
                },
            },
            {
                'product_code': 'epayroll',
                'subscription_status': 'cancelled',
                'is_entitled': False,
                'product': {'name': 'EPayRoll', 'primary_domain': 'epayroll.easytech.services', 'icon': ''},
            },
        ]
        with patch(
            'nodeone.modules.ets_portal.portal_service.SubscriptionRegistry.list_tenant_products',
            return_value=fake,
        ):
            items = PortalService.list_products_for_tenant(1, scope_organization_id=1)
        codes = [i['product_code'] for i in items]
        self.assertEqual(codes, ['eposone'])
        self.assertEqual(items[0]['open_url'], 'https://eposone.easytech.services')
        desc = (items[0]['description'] or items[0]['name'] or '').lower()
        self.assertIn('punto de venta', desc)
        self.assertTrue(items[0].get('icon_url') or items[0].get('icon'))
        self.assertTrue(str(items[0].get('icon_url') or '').endswith('.svg'))
        self.assertEqual(items[0].get('brand_preset'), 'eposone')

    def test_context_resolver_platform_hosts(self):
        from nodeone.core.platform.context_resolver import ContextResolver

        for host in ('appprd.easynodeone.com', 'appdev.easynodeone.com'):
            ctx = ContextResolver.resolve(host)
            self.assertEqual(ctx.product_code, 'en1', host)
            self.assertEqual(ctx.surface, 'platform', host)

    def test_post_login_goes_to_portal(self):
        from flask import Flask

        from nodeone.core.platform.launcher import post_login_redirect_target

        app = Flask(__name__)
        app.add_url_rule('/portal/', endpoint='ets_portal.home', view_func=lambda: 'ok')
        app.add_url_rule('/dashboard', endpoint='dashboard', view_func=lambda: 'dash')

        class U:
            pass

        with app.test_request_context('/', headers={'Host': 'appprd.easynodeone.com'}):
            with patch(
                'nodeone.core.platform.context_resolver.ContextResolver.resolve_product_code',
                return_value='portal',
            ):
                dest = post_login_redirect_target(next_page=None, user=U(), session={})
        self.assertTrue(dest.endswith('/portal/') or dest == '/portal/')

    def test_portal_urls_canonical(self):
        from nodeone.core.platform.portal_urls import (
            absolute_portal_path,
            portal_account_domain,
            portal_products_url,
        )

        self.assertEqual(portal_account_domain(), 'appprd.easynodeone.com')
        self.assertEqual(portal_products_url(), 'https://appprd.easynodeone.com/portal/products')
        self.assertEqual(
            absolute_portal_path('/portal/products'),
            'https://appprd.easynodeone.com/portal/products',
        )

    def test_product_host_allows_portal_surface(self):
        from flask import Flask

        from nodeone.core.platform.context_resolver import ContextResolver
        from nodeone.modules.ets_portal.routes import _require_portal_surface

        app = Flask(__name__)
        bundled = ContextResolver.resolve('eposone.easytech.services')
        with app.test_request_context(
            '/portal/products',
            base_url='https://eposone.easytech.services',
            environ_overrides={'HTTP_HOST': 'eposone.easytech.services'},
        ):
            with patch(
                'nodeone.modules.ets_portal.routes.current_app_context',
                return_value=bundled,
            ):
                resp = _require_portal_surface()
        self.assertIsNone(resp)


if __name__ == '__main__':
    unittest.main()
