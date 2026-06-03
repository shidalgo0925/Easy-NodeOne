"""Compat: /admin/contacts legacy CRM o módulo central Contactos."""
import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestContactsUnifiedToCrm(unittest.TestCase):
    def test_contacts_path_resolved(self):
        from app import app
        from nodeone.services.contacts_module import is_contacts_globally_allowed

        by_ep = {r.endpoint: str(r.rule) for r in app.url_map.iter_rules()}
        if is_contacts_globally_allowed():
            self.assertIn('contacts_admin.contacts_index', by_ep)
            self.assertEqual(by_ep.get('contacts_admin.contacts_index'), '/admin/contacts/')
        else:
            self.assertIn('admin_tenant_contacts', by_ep)
            self.assertEqual(by_ep.get('admin_tenant_contacts'), '/admin/contacts')


if __name__ == '__main__':
    unittest.main()
