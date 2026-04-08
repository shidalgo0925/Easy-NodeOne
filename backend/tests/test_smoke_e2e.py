"""Humo end-to-end: app import, blueprints vía register_modules, /login."""
import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))


class TestAppSmokeE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    def test_login_get_200(self):
        with self.app.test_client() as c:
            r = c.get('/login')
            self.assertEqual(r.status_code, 200)

    def test_login_with_next_query_200(self):
        with self.app.test_client() as c:
            r = c.get('/login?next=%2Fdashboard')
            self.assertEqual(r.status_code, 200)

    def test_register_modules_idempotent(self):
        from nodeone.core.features import register_modules

        register_modules(self.app)
        register_modules(self.app)

    def test_core_blueprints_from_register_modules(self):
        names = set(self.app.blueprints.keys())
        for required in (
            'auth',
            'members',
            'payments',
            'policies',
            'appointments',
            'events',
            'marketing',
            'admin_services_catalog',
            'member_pages',
        ):
            self.assertIn(required, names, f'Falta blueprint {required}')


if __name__ == '__main__':
    unittest.main()
