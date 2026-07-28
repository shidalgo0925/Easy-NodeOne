"""EP1 — nav_effective_access + product-shell platform flag."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestNavEffectiveAccess(unittest.TestCase):
    def test_is_system_administrator(self):
        from nodeone.core.platform.nav_effective_access import is_system_administrator

        self.assertTrue(is_system_administrator(MagicMock(is_admin=True)))
        self.assertFalse(is_system_administrator(MagicMock(is_admin=False)))
        self.assertFalse(is_system_administrator(MagicMock(spec=[])))


class TestProductShellPlatformFlag(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    @patch('nodeone.core.platform.app_shell.product_surface_primary_app_id', return_value='eposone')
    @patch('nodeone.core.platform.app_shell.build_nav_context_for_user')
    @patch('app._org_id_for_module_visibility', return_value=5)
    def test_sa_keeps_platform_nav_on_product_host(self, _oid, mock_ctx, _primary):
        from nodeone.core.nav_menu import build_nav_context
        from nodeone.core.platform.app_shell import merge_native_app_nav_context

        mock_ctx.return_value = build_nav_context(
            nav_can=lambda _p: True,
            saas_module_enabled=lambda _c: True,
            saas_module_enabled_chain=lambda *_c: True,
            has_view_endpoint=lambda _e: True,
            show_academic_admin_nav=False,
            office365_module_enabled=False,
            show_platform_admin_nav=True,
            is_platform_admin=True,
            is_advisor=False,
            show_tenant_admin_menu=True,
        )
        with self.app.test_request_context(
            '/admin/eposone/dashboard',
            base_url='https://eposone.easytech.services',
        ):
            out: dict = {'nav_active_area_id': 'eposone'}
            merge_native_app_nav_context(out, MagicMock(is_admin=True), {})
            self.assertTrue(out.get('app_nav_native_active'))
            self.assertTrue(out.get('show_platform_admin_nav'))

    @patch('nodeone.core.platform.app_shell.product_surface_primary_app_id', return_value='eposone')
    @patch('nodeone.core.platform.app_shell.build_nav_context_for_user')
    @patch('app._org_id_for_module_visibility', return_value=5)
    def test_tenant_no_platform_nav_on_product_host(self, _oid, mock_ctx, _primary):
        from nodeone.core.nav_menu import build_nav_context
        from nodeone.core.platform.app_shell import merge_native_app_nav_context

        mock_ctx.return_value = build_nav_context(
            nav_can=lambda _p: True,
            saas_module_enabled=lambda _c: True,
            saas_module_enabled_chain=lambda *_c: True,
            has_view_endpoint=lambda _e: True,
            show_academic_admin_nav=False,
            office365_module_enabled=False,
            show_platform_admin_nav=False,
            is_platform_admin=False,
            is_advisor=False,
            show_tenant_admin_menu=True,
        )
        with self.app.test_request_context(
            '/admin/eposone/dashboard',
            base_url='https://eposone.easytech.services',
        ):
            out: dict = {'nav_active_area_id': 'eposone'}
            merge_native_app_nav_context(out, MagicMock(is_admin=False), {})
            self.assertTrue(out.get('app_nav_native_active'))
            self.assertFalse(out.get('show_platform_admin_nav'))


if __name__ == '__main__':
    unittest.main()
