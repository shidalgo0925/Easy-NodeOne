"""Tests EPosOne — app nativa Etapa 6."""

import os
import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestEPosOne(unittest.TestCase):
    def test_eposone_manifest(self):
        from nodeone.modules.eposone.manifest import MODULE

        self.assertEqual(MODULE['id'], 'eposone')
        self.assertIn('eposone', MODULE['saas_codes'])
        self.assertEqual(MODULE['nav_area_id'], 'eposone')
        self.assertTrue(MODULE['native_platform'])
        self.assertIn('contacts', MODULE['depends_on'])
        self.assertNotIn('emembership', MODULE.get('legacy_modules', ()))

    def test_registry_native_eposone(self):
        from nodeone.core.platform.app_registry import get_application

        epos = get_application('eposone')
        self.assertIsNotNone(epos)
        self.assertTrue(epos.native_platform)
        self.assertIn('contacts', epos.depends_on)

    def test_launcher_maps_eposone_nav(self):
        from nodeone.core.platform.launcher import NAV_AREA_TO_PLATFORM_APP

        self.assertEqual(NAV_AREA_TO_PLATFORM_APP.get('eposone'), 'eposone')


class TestEPosOneRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    def test_eposone_blueprint_registered(self):
        self.assertIn('eposone', self.app.blueprints)

    def test_eposone_home_redirects_anonymous(self):
        with self.app.test_client() as c:
            r = c.get('/admin/eposone/', follow_redirects=False)
            self.assertIn(r.status_code, (302, 401))


if __name__ == '__main__':
    unittest.main()
