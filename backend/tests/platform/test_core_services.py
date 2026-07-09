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

    @patch('nodeone.core.services.product.CoreProductService.search', return_value=[])
    def test_product_service_search(self, mock_search):
        from nodeone.core.services.product import ProductService

        items = ProductService.search(1, query='café')
        self.assertEqual(items, [])
        mock_search.assert_called_once_with(1, query='café', product_type=None, status=None, limit=50)

    @patch('app.db')
    @patch('nodeone.core.master.product.CoreProduct')
    def test_product_service_create(self, mock_model, mock_db):
        from nodeone.core.services.product import ProductService

        mock_model.query.filter_by.return_value.first.return_value = None
        row = MagicMock()
        row.id = 1
        row.organization_id = 1
        row.product_ref = 'SKU-001'
        row.name = 'Café'
        row.product_type = 'good'
        row.status = 'active'
        row.tracks_inventory = True
        row.unit_price = 3.5
        row.currency = 'USD'
        row.description = None
        row.source_app_id = 'eposone'
        mock_model.return_value = row
        dto = ProductService.create(
            1,
            {
                'product_ref': 'SKU-001',
                'name': 'Café',
                'product_type': 'good',
                'tracks_inventory': True,
                'unit_price': 3.5,
                'source_app_id': 'eposone',
            },
        )
        self.assertEqual(dto.product_ref, 'SKU-001')
        self.assertTrue(dto.tracks_inventory)


class TestOrgUnitServiceFacade(unittest.TestCase):
    @patch('nodeone.core.services.org_unit._CoreOrgUnitService.list_units', return_value=[])
    def test_list_units_delegates(self, mock_list):
        from nodeone.core.services.org_unit import OrgUnitService

        items = OrgUnitService.list_units(1, unit_type='branch')
        self.assertEqual(items, [])
        mock_list.assert_called_once_with(1, unit_type='branch', status=None)


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
