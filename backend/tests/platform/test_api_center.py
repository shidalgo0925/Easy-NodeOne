"""Tests API Center nav + catalog (Sprint B)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestApiCenterNav(unittest.TestCase):
    def test_api_center_area_separate_from_comunicacion(self):
        from nodeone.core.nav_menu import APP_AREAS, _API_CENTER_ITEMS, _v_api_center, build_nav_context

        area = next(a for a in APP_AREAS if a.id == 'api_center')
        self.assertEqual(area.label, 'API Center')
        self.assertTrue(area.show_in_sidebar)
        labels = [it.label for it in _API_CENTER_ITEMS]
        self.assertEqual(
            labels,
            ['APIs Disponibles', 'API Keys', 'API Explorer', 'Registro'],
        )

        com = next(a for a in APP_AREAS if a.id == 'comunicacion')
        self.assertNotEqual(com.id, area.id)

        manager = build_nav_context(
            nav_can=lambda p: p == 'integrations.manage',
            saas_module_enabled=lambda _c: True,
            saas_module_enabled_chain=lambda *_a: True,
            has_view_endpoint=lambda _e: True,
            show_academic_admin_nav=False,
            office365_module_enabled=False,
            show_platform_admin_nav=False,
            is_platform_admin=False,
            is_advisor=False,
            show_tenant_admin_menu=True,
        )
        self.assertTrue(_v_api_center(manager))

        viewer = build_nav_context(
            nav_can=lambda p: p == 'integrations.view',
            saas_module_enabled=lambda _c: True,
            saas_module_enabled_chain=lambda *_a: True,
            has_view_endpoint=lambda _e: True,
            show_academic_admin_nav=False,
            office365_module_enabled=False,
            show_platform_admin_nav=False,
            is_platform_admin=False,
            is_advisor=False,
            show_tenant_admin_menu=True,
        )
        self.assertFalse(_v_api_center(viewer))

    def test_catalog_has_membership_verification(self):
        from nodeone.modules.membership_verification.catalog import API_CATALOG

        ids = [a['id'] for a in API_CATALOG]
        self.assertIn('membership_verification', ids)


class TestApiKeyLifecycleHelpers(unittest.TestCase):
    def test_generate_raw_has_prefix(self):
        from nodeone.services.integration_api_keys import generate_raw_api_key, hash_api_key

        raw, prefix, khash = generate_raw_api_key()
        self.assertTrue(raw.startswith('enk_'))
        self.assertEqual(prefix, raw[:12])
        self.assertEqual(khash, hash_api_key(raw))


if __name__ == '__main__':
    unittest.main()
