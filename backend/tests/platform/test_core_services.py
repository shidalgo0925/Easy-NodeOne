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

    @staticmethod
    def _contact_dto(**kwargs):
        from nodeone.core.services.contacts import ContactDTO

        defaults = dict(
            id=10,
            organization_id=1,
            display_name='Ana Cliente',
            email='ana@example.com',
            phone=None,
            mobile=None,
            contact_type='person',
            identification_type='consumer_final',
            tax_id=None,
            dv=None,
            is_customer=True,
            is_supplier=False,
            is_member=False,
            is_student=False,
            is_participant=False,
            is_instructor=False,
            is_employee=False,
            active=True,
            roles=('Cliente',),
        )
        defaults.update(kwargs)
        return ContactDTO(**defaults)

    @patch('nodeone.core.services.contacts.ContactService.get')
    def test_resolve_ref_numeric_id(self, mock_get):
        from nodeone.core.services.contacts import ContactService

        mock_get.return_value = self._contact_dto()
        dto = ContactService.resolve_ref(1, '10')
        self.assertEqual(dto.id, 10)

    @patch('nodeone.core.services.contacts.ContactService.find_by_email')
    def test_resolve_ref_email(self, mock_find):
        from nodeone.core.services.contacts import ContactService

        mock_find.return_value = self._contact_dto()
        dto = ContactService.resolve_ref(1, 'ana@example.com')
        self.assertEqual(dto.email, 'ana@example.com')

    @patch('nodeone.core.services.contacts.ContactService.get')
    @patch('nodeone.core.master.contact_bridge.ContactBridgeService.resolve')
    def test_resolve_ref_legacy_linked(self, mock_resolve, mock_get):
        from types import SimpleNamespace

        from nodeone.core.services.contacts import ContactService

        mock_resolve.return_value = SimpleNamespace(canonical_contact_id=10)
        mock_get.return_value = self._contact_dto()
        dto = ContactService.resolve_ref(1, 'legacy:99')
        self.assertEqual(dto.id, 10)

    @patch('nodeone.core.master.contact_bridge.ContactBridgeService.resolve', return_value=None)
    @patch('nodeone.core.services.contacts.ContactService.get', return_value=None)
    def test_resolve_ref_invalid_contact_id(self, _mock_get, _mock_resolve):
        from nodeone.core.services.contacts import ContactService

        with self.assertRaises(ContactService.ValidationError):
            ContactService.resolve_ref(1, '999')

    @patch('nodeone.core.master.contact_bridge.ContactBridgeService.link')
    @patch('nodeone.modules.contacts.service.create_contact')
    def test_create_with_legacy_link(self, mock_create_contact, mock_link):
        from nodeone.core.services.contacts import ContactService

        row = MagicMock()
        row.id = 11
        row.organization_id = 1
        row.display_name = 'Nuevo'
        row.email = 'nuevo@example.com'
        row.phone = None
        row.mobile = None
        row.contact_type = 'person'
        row.identification_type = 'consumer_final'
        row.tax_id = None
        row.dv = None
        row.is_customer = True
        row.is_supplier = False
        row.is_member = False
        row.is_student = False
        row.is_participant = False
        row.is_instructor = False
        row.is_employee = False
        row.active = True
        row.role_labels.return_value = ['Cliente']
        mock_create_contact.return_value = row

        dto = ContactService.create_with_legacy_link(
            1,
            {'display_name': 'Nuevo', 'email': 'nuevo@example.com', 'is_customer': True, 'legacy_contact_id': 7},
        )
        self.assertEqual(dto.id, 11)
        mock_link.assert_called_once_with(1, contact_id=11, legacy_contact_id=7, link_source='eposone_create')

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
