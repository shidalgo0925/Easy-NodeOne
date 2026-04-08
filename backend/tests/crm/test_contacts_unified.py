"""Compat: /admin/contacts sigue existiendo pero unificado a CRM."""
import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestContactsUnifiedToCrm(unittest.TestCase):
    def test_contacts_endpoint_registered(self):
        from app import app

        endpoints = {r.endpoint for r in app.url_map.iter_rules()}
        self.assertIn('admin_tenant_contacts', endpoints)
        self.assertIn('admin_tenant_contact_delete', endpoints)

    def test_contacts_path_kept(self):
        from app import app

        by_ep = {r.endpoint: str(r.rule) for r in app.url_map.iter_rules()}
        self.assertEqual(by_ep.get('admin_tenant_contacts'), '/admin/contacts')


if __name__ == '__main__':
    unittest.main()
