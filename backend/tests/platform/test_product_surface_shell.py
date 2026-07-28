"""Surface EPosOne — shell forzado en Host product."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestProductSurfaceShell(unittest.TestCase):
    def test_primary_app_id_on_eposone_host(self):
        from nodeone.core.platform.app_shell import product_surface_primary_app_id
        from nodeone.core.platform.context_resolver import ContextResolver

        bundled = ContextResolver.resolve('eposone.easytech.services')
        with patch(
            'nodeone.core.platform.context_resolver.current_app_context',
            return_value=bundled,
        ):
            self.assertEqual(product_surface_primary_app_id(), 'eposone')

    def test_no_primary_on_platform_host(self):
        from nodeone.core.platform.app_shell import product_surface_primary_app_id
        from nodeone.core.platform.context_resolver import ContextResolver

        bundled = ContextResolver.resolve('appdev.easynodeone.com')
        with patch(
            'nodeone.core.platform.context_resolver.current_app_context',
            return_value=bundled,
        ):
            self.assertIsNone(product_surface_primary_app_id())

    def test_post_login_uses_home_hint(self):
        from nodeone.core.platform.context_resolver import ContextResolver
        from nodeone.core.platform.launcher import post_login_redirect_target

        bundled = ContextResolver.resolve('eposone.easytech.services')
        session = {}
        user = MagicMock()
        usable = [{'product_code': 'eposone', 'is_entitled': True}]

        with patch(
            'nodeone.core.platform.context_resolver.current_app_context',
            return_value=bundled,
        ), patch(
            'nodeone.modules.ets_portal.portal_service.PortalService.list_usable_products_for_current_tenant',
            return_value=usable,
        ), patch(
            'flask.url_for',
            side_effect=lambda ep, **kw: f'/resolved/{ep}',
        ):
            dest = post_login_redirect_target(next_page=None, user=user, session=session)
        self.assertEqual(dest, '/resolved/eposone.eposone_home')
        self.assertEqual(session.get('platform_active_app_id'), 'eposone')

    def test_post_login_many_products_still_opens_host_product(self):
        """Con entitlement del producto del host → dashboard, aunque haya N productos."""
        from nodeone.core.platform.context_resolver import ContextResolver
        from nodeone.core.platform.launcher import post_login_redirect_target

        bundled = ContextResolver.resolve('eposone.easytech.services')
        usable = [
            {'product_code': 'eposone', 'is_entitled': True},
            {'product_code': 'epayroll', 'is_entitled': True},
        ]
        session = {}
        with patch(
            'nodeone.core.platform.context_resolver.current_app_context',
            return_value=bundled,
        ), patch(
            'nodeone.modules.ets_portal.portal_service.PortalService.list_usable_products_for_current_tenant',
            return_value=usable,
        ), patch(
            'flask.url_for',
            side_effect=lambda ep, **kw: f'/resolved/{ep}',
        ):
            dest = post_login_redirect_target(next_page=None, user=MagicMock(), session=session)
        self.assertEqual(dest, '/resolved/eposone.eposone_home')
        self.assertEqual(session.get('platform_active_app_id'), 'eposone')

    def test_post_login_without_host_product_goes_to_canonical_portal(self):
        from nodeone.core.platform.context_resolver import ContextResolver
        from nodeone.core.platform.launcher import post_login_redirect_target
        from nodeone.core.platform.portal_urls import portal_products_url

        bundled = ContextResolver.resolve('eposone.easytech.services')
        usable = [{'product_code': 'epayroll', 'is_entitled': True}]
        with patch(
            'nodeone.core.platform.context_resolver.current_app_context',
            return_value=bundled,
        ), patch(
            'nodeone.modules.ets_portal.portal_service.PortalService.list_usable_products_for_current_tenant',
            return_value=usable,
        ), patch(
            'nodeone.core.platform.launcher._try_session_org_with_product',
            return_value=False,
        ):
            dest = post_login_redirect_target(next_page=None, user=MagicMock(), session={})
        self.assertEqual(dest, portal_products_url())
        self.assertTrue(dest.startswith('https://'))
        self.assertIn('/portal/products', dest)


if __name__ == '__main__':
    unittest.main()
