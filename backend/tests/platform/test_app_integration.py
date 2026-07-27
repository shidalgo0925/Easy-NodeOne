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

    def test_ecrm_manifest(self):
        from nodeone.modules.ecrm.manifest import MODULE

        self.assertEqual(MODULE['id'], 'ecrm')
        self.assertIn('crm', MODULE['saas_codes'])
        self.assertEqual(MODULE['nav_area_id'], 'crm')
        self.assertIn('contacts', MODULE['depends_on'])

    def test_eevents_manifest(self):
        from nodeone.modules.eevents.manifest import MODULE

        self.assertEqual(MODULE['id'], 'eevents')
        self.assertIn('events', MODULE['saas_codes'])
        self.assertEqual(MODULE['nav_area_id'], 'eventos')
        self.assertEqual(MODULE['integration_order'], 3)

    def test_ecertificates_manifest(self):
        from nodeone.modules.ecertificates.manifest import MODULE

        self.assertEqual(MODULE['id'], 'ecertificates')
        self.assertIn('certificates', MODULE['saas_codes'])
        self.assertEqual(MODULE['nav_area_id'], 'certificados')
        self.assertIn('eevents', MODULE['depends_on'])
        self.assertIn('emembership', MODULE['depends_on'])

    def test_eappointments_manifest(self):
        from nodeone.modules.eappointments.manifest import MODULE

        self.assertEqual(MODULE['id'], 'eappointments')
        self.assertIn('appointments', MODULE['saas_codes'])
        self.assertEqual(MODULE['nav_area_id'], 'agenda')
        self.assertEqual(MODULE['integration_order'], 5)
        self.assertEqual(MODULE['depends_on'], ())

    def test_certificates_hidden_without_dependencies(self):
        from nodeone.core.platform.app_integration import filter_launcher_apps_for_org

        apps = [
            {'id': 'certificados', 'platform_app_id': 'ecertificates', 'label': 'Certificados'},
        ]

        with patch(
            'nodeone.core.platform.app_integration.organization_has_integrated_apps',
            return_value=True,
        ):
            with patch(
                'nodeone.core.platform.app_integration.get_app_runtime',
                side_effect=lambda oid, aid: 'plataforma' if aid == 'ecertificates' else 'legacy',
            ):
                filtered = filter_launcher_apps_for_org(1, apps)
        self.assertEqual(filtered, [])

    def test_filter_multiple_integrated_apps(self):
        from nodeone.core.platform.app_integration import filter_launcher_apps_for_org

        apps = [
            {'id': 'membresias', 'platform_app_id': 'emembership', 'label': 'Membresías'},
            {'id': 'crm', 'platform_app_id': 'ecrm', 'label': 'CRM'},
            {'id': 'eventos', 'platform_app_id': 'eevents', 'label': 'Eventos'},
        ]

        def _runtime(oid, aid):
            if aid in ('emembership', 'ecrm'):
                return 'plataforma'
            return 'legacy'

        with patch(
            'nodeone.core.platform.app_integration.organization_has_integrated_apps',
            return_value=True,
        ):
            with patch('nodeone.core.platform.app_integration.get_app_runtime', side_effect=_runtime):
                filtered = filter_launcher_apps_for_org(1, apps)
        self.assertEqual({a['id'] for a in filtered}, {'membresias', 'crm'})


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
