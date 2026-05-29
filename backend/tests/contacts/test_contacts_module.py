"""Tests unitarios — módulo Contactos (validación y rutas)."""
import os
import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

os.environ.setdefault('NODEONE_CONTACTS_MODULE_ENABLED', '1')


class TestContactsValidation(unittest.TestCase):
    def test_display_name_required(self):
        from nodeone.modules.contacts import service as svc

        with self.assertRaises(svc.ContactValidationError):
            svc.validate_contact_payload({'contact_type': 'person'}, organization_id=1)

    def test_company_requires_company_name(self):
        from nodeone.modules.contacts import service as svc

        with self.assertRaises(svc.ContactValidationError):
            svc.validate_contact_payload(
                {'contact_type': 'company', 'display_name': 'ACME'},
                organization_id=1,
            )

    def test_ruc_requires_tax_id(self):
        from nodeone.modules.contacts import service as svc

        with self.assertRaises(svc.ContactValidationError):
            svc.validate_contact_payload(
                {
                    'contact_type': 'company',
                    'display_name': 'ACME SA',
                    'company_name': 'ACME SA',
                    'identification_type': 'ruc',
                },
                organization_id=1,
            )

    def test_consumer_final_clears_tax_id(self):
        from nodeone.modules.contacts import service as svc

        out = svc.validate_contact_payload(
            {
                'contact_type': 'consumer_final',
                'display_name': 'Cliente mostrador',
                'identification_type': 'consumer_final',
                'tax_id': '123',
            },
            organization_id=1,
        )
        self.assertIsNone(out['tax_id'])
        self.assertEqual(out['contact_type'], 'consumer_final')


class TestContactsRoutes(unittest.TestCase):
    def test_contacts_blueprint_registered(self):
        from app import app

        self.assertIn('contacts_admin', app.blueprints)
        endpoints = {r.endpoint for r in app.url_map.iter_rules()}
        self.assertIn('contacts_admin.contacts_index', endpoints)

    def test_legacy_crm_contacts_not_when_module_on(self):
        from nodeone.services.contacts_module import is_contacts_globally_allowed

        if not is_contacts_globally_allowed():
            self.skipTest('contacts module globally off')
        from app import app

        endpoints = {r.endpoint for r in app.url_map.iter_rules()}
        self.assertNotIn('admin_tenant_contacts', endpoints)


if __name__ == '__main__':
    unittest.main()
