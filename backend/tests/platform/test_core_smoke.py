"""Tests humo del Core de plataforma (Etapa 2)."""

import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestPlatformCorePackage(unittest.TestCase):
    def test_registry_contains_integration_apps(self):
        from nodeone.core.platform import APPLICATIONS, get_application

        self.assertIsNotNone(get_application('emembership'))
        self.assertIsNotNone(get_application('ecertificates'))
        epos = get_application('eposone')
        self.assertIsNotNone(epos)
        self.assertTrue(epos.native_platform)

        ordered = [a for a in APPLICATIONS if a.integration_order is not None]
        orders = [a.integration_order for a in ordered]
        self.assertEqual(orders, sorted(orders))

    def test_certificates_depends_on_events_and_membership(self):
        from nodeone.core.platform import get_application

        cert = get_application('ecertificates')
        self.assertIsNotNone(cert)
        self.assertIn('eevents', cert.depends_on)
        self.assertIn('emembership', cert.depends_on)

    def test_core_capabilities_enum(self):
        from nodeone.core.platform import CoreCapability

        self.assertEqual(CoreCapability.SECURITY.value, 'security')
        self.assertEqual(CoreCapability.LICENSING.value, 'licensing')


class TestPlatformCoreSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    def test_login_get_200(self):
        with self.app.test_client() as c:
            r = c.get('/login')
            self.assertEqual(r.status_code, 200)

    def test_register_platform_core_idempotent(self):
        from nodeone.core.platform import register_platform_core

        register_platform_core(self.app)
        register_platform_core(self.app)
        self.assertIn('auth', self.app.blueprints)

    def test_core_and_app_blueprints_registered(self):
        names = set(self.app.blueprints.keys())
        self.assertIn('auth', names)
        self.assertIn('events', names)

    def test_runtime_has_saas_module_default_org(self):
        from nodeone.core.platform import has_saas_module

        with self.app.app_context():
            # payments es is_core=True en catálogo
            self.assertTrue(has_saas_module('payments', organization_id=1))

    def test_runtime_resolve_organization_id_without_request(self):
        from nodeone.core.platform import resolve_organization_id

        with self.app.app_context():
            self.assertIsNone(resolve_organization_id())

    def test_runtime_has_permission_false_without_user(self):
        from nodeone.core.platform import has_permission

        self.assertFalse(has_permission(None, 'users.view'))


if __name__ == '__main__':
    unittest.main()
