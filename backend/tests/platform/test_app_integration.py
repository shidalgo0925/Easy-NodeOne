"""Tests integración apps — Etapa 5 (EMembership)."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestAppIntegration(unittest.TestCase):
    def tearDown(self):
        for key in os.environ:
            if key.startswith('NODEONE_APP_RUNTIME_'):
                os.environ.pop(key, None)

    def test_env_runtime_emembership(self):
        from nodeone.core.platform.app_integration import get_app_runtime

        os.environ['NODEONE_APP_RUNTIME_EMEMBERSHIP_ORG_IDS'] = '1'
        os.environ['NODEONE_APP_RUNTIME_EMEMBERSHIP'] = 'plataforma'
        self.assertEqual(get_app_runtime(1, 'emembership'), 'plataforma')
        self.assertEqual(get_app_runtime(2, 'emembership'), 'legacy')

    def test_filter_launcher_when_integrated(self):
        from nodeone.core.platform.app_integration import filter_launcher_apps_for_org

        apps = [
            {'id': 'membresias', 'platform_app_id': 'emembership', 'label': 'Membresías'},
            {'id': 'eventos', 'platform_app_id': 'eevents', 'label': 'Eventos'},
        ]
        with patch(
            'nodeone.core.platform.app_integration.organization_has_integrated_apps',
            return_value=True,
        ):
            with patch(
                'nodeone.core.platform.app_integration.get_app_runtime',
                side_effect=lambda oid, aid: 'plataforma' if aid == 'emembership' else 'legacy',
            ):
                filtered = filter_launcher_apps_for_org(1, apps)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['id'], 'membresias')

    def test_emembership_manifest(self):
        from nodeone.modules.emembership.manifest import MODULE

        self.assertEqual(MODULE['id'], 'emembership')
        self.assertIn('memberships', MODULE['saas_codes'])
        self.assertEqual(MODULE['nav_area_id'], 'membresias')


class TestLauncherIntegratedMode(unittest.TestCase):
    def tearDown(self):
        os.environ.pop('NODEONE_LAUNCHER_APPS_ORG_IDS', None)
        os.environ.pop('NODEONE_LAUNCHER_CLASSIC_ORG_IDS', None)

    def test_integrated_org_uses_apps_mode(self):
        from nodeone.core.platform.launcher import launcher_mode_for_organization

        with patch(
            'nodeone.core.platform.app_integration.organization_has_integrated_apps',
            return_value=True,
        ):
            self.assertEqual(launcher_mode_for_organization(1), 'apps')


if __name__ == '__main__':
    unittest.main()
