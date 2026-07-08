"""Tests servicios Core compartidos — Etapa 11."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestContactService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    @patch('nodeone.modules.contacts.service.get_contact')
    def test_get_returns_dto(self, mock_get):
        from nodeone.core.services.contacts import ContactService

        row = MagicMock()
        row.id = 5
        row.organization_id = 1
        row.display_name = 'Acme'
        row.email = 'a@acme.com'
        row.phone = None
        row.mobile = None
        row.contact_type = 'company'
        row.identification_type = 'ruc'
        row.tax_id = '123'
        row.dv = '12'
        row.is_customer = True
        row.is_supplier = False
        row.is_member = False
        row.is_student = False
        row.is_participant = False
        row.is_instructor = False
        row.is_employee = False
        row.active = True
        row.role_labels.return_value = ['Cliente']
        mock_get.return_value = row

        dto = ContactService.get(1, 5)
        self.assertIsNotNone(dto)
        self.assertEqual(dto.display_name, 'Acme')
        self.assertEqual(dto.roles, ('Cliente',))
        self.assertEqual(dto.to_dict()['id'], 5)

    def test_product_service_not_ready(self):
        from nodeone.core.services.product import ProductService, ProductServiceNotReadyError

        with self.assertRaises(ProductServiceNotReadyError):
            ProductService.search(1)


class TestOrganizationService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    def test_resolve_active_without_request(self):
        from nodeone.core.services.organization import OrganizationService

        with self.app.app_context():
            self.assertIsNone(OrganizationService.resolve_active_id())


if __name__ == '__main__':
    unittest.main()
