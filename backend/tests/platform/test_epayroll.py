"""Tests EPayroll — app nativa Etapa 9."""

import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestEPayroll(unittest.TestCase):
    def test_epayroll_manifest_active(self):
        from nodeone.modules.epayroll.manifest import MODULE

        self.assertEqual(MODULE['id'], 'epayroll')
        self.assertEqual(MODULE['lifecycle'], 'active')
        self.assertIn('register', MODULE)
        self.assertTrue(MODULE['native_platform'])

    def test_manifest_registry_validates_epayroll(self):
        from nodeone.core.platform.manifest_registry import load_manifest, validate_manifest

        m = load_manifest('nodeone.modules.epayroll.manifest')
        self.assertEqual(validate_manifest(m), [])

    def test_launcher_maps_epayroll_nav(self):
        from nodeone.core.platform.launcher import NAV_AREA_TO_PLATFORM_APP

        self.assertEqual(NAV_AREA_TO_PLATFORM_APP.get('epayroll'), 'epayroll')


class TestEPayrollRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    def test_epayroll_blueprint_registered(self):
        self.assertIn('epayroll', self.app.blueprints)

    def test_epayroll_home_redirects_anonymous(self):
        with self.app.test_client() as c:
            r = c.get('/admin/epayroll/', follow_redirects=False)
            self.assertIn(r.status_code, (302, 401))


if __name__ == '__main__':
    unittest.main()
