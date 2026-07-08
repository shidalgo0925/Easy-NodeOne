"""Tests shell por aplicación (Etapa 4)."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestAppShellNav(unittest.TestCase):
    def test_build_app_shell_nav_payload_single_area(self):
        from nodeone.core.nav_menu import build_nav_context
        from nodeone.core.platform.app_shell import build_app_shell_nav_payload

        ctx = build_nav_context(
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
        with patch('nodeone.core.nav_menu.has_request_context', return_value=False):
            payload = build_app_shell_nav_payload('crm', ctx)
        self.assertTrue(payload['platform_app_shell_active'])
        self.assertEqual(payload['nav_active_area_id'], 'crm')
        self.assertEqual(payload['nav_sidebar_groups'], [])
        self.assertEqual(payload['nav_app_areas'], [])

    def test_is_app_shell_enabled_requires_active_app(self):
        from nodeone.core.platform.app_shell import is_app_shell_enabled

        os.environ['NODEONE_LAUNCHER_APPS_ORG_IDS'] = '1'
        self.assertFalse(is_app_shell_enabled(1, {}))
        self.assertTrue(is_app_shell_enabled(1, {'platform_active_app_id': 'crm'}))
        os.environ.pop('NODEONE_LAUNCHER_APPS_ORG_IDS', None)


class TestAppShellMerge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    def test_merge_skips_launcher_blueprint(self):
        from nodeone.core.platform.app_shell import merge_app_shell_nav_context

        with self.app.test_request_context('/platform/apps'):
            out = {'nav_app_areas': [{'id': 'crm'}]}
            user = MagicMock()
            merge_app_shell_nav_context(out, user, {'platform_active_app_id': 'crm'})
            self.assertFalse(out.get('platform_app_shell_active'))


if __name__ == '__main__':
    unittest.main()
