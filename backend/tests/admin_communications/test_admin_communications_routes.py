"""Smoke: blueprint admin_communications y rutas API."""
import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestAdminCommunicationsRoutes(unittest.TestCase):
    def test_blueprint_and_urls(self):
        from app import app

        self.assertIn('admin_communications', app.blueprints)
        endpoints = {r.endpoint for r in app.url_map.iter_rules()}
        required = {
            'admin_communications.admin_communications_settings',
            'admin_communications.api_communication_events_list',
            'admin_communications.api_communication_rules_list',
            'admin_communications.api_communication_rules_create',
            'admin_communications.api_communication_rules_update',
            'admin_communications.api_communication_rules_delete',
            'admin_communications.api_communication_marketing_templates',
        }
        self.assertFalse(required - endpoints, f'Faltan: {sorted(required - endpoints)}')

    def test_member_communication_preferences_routes(self):
        from app import app

        comm = [
            r for r in app.url_map.iter_rules()
            if r.rule == '/api/user/communication-preferences'
        ]
        self.assertTrue(comm, 'Falta /api/user/communication-preferences')
        methods = set()
        for r in comm:
            methods |= set(r.methods or ())
        self.assertIn('GET', methods)
        self.assertIn('PUT', methods)


if __name__ == '__main__':
    unittest.main()
