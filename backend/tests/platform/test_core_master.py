"""Tests modelo maestro Core — Etapa 10b."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestCoreMasterConstants(unittest.TestCase):
    def test_org_unit_types(self):
        from nodeone.core.master.constants import ORG_UNIT_TYPE_BRANCH, ORG_UNIT_TYPES

        self.assertIn(ORG_UNIT_TYPE_BRANCH, ORG_UNIT_TYPES)


class TestOrgUnitService(unittest.TestCase):
    @patch('app.db')
    @patch('nodeone.core.master.org_unit.CoreOrgUnit')
    def test_create_branch(self, mock_model, mock_db):
        from nodeone.core.master.constants import ORG_UNIT_TYPE_BRANCH
        from nodeone.core.master.org_unit import OrgUnitService

        mock_model.query.filter_by.return_value.first.return_value = None
        row = MagicMock(
            id=1,
            organization_id=1,
            unit_ref='SUC-01',
            name='Sucursal Centro',
            unit_type=ORG_UNIT_TYPE_BRANCH,
            status='active',
            parent_id=None,
            notes=None,
        )
        mock_model.return_value = row
        dto = OrgUnitService.create(
            1,
            unit_ref='SUC-01',
            name='Sucursal Centro',
            unit_type=ORG_UNIT_TYPE_BRANCH,
        )
        self.assertEqual(dto.unit_ref, 'SUC-01')
        self.assertEqual(dto.unit_type, ORG_UNIT_TYPE_BRANCH)
        mock_db.session.add.assert_called_once()
        mock_db.session.commit.assert_called_once()

    @patch('nodeone.core.master.org_unit.CoreOrgUnit')
    def test_create_rejects_duplicate_ref(self, mock_model):
        from nodeone.core.master.constants import MasterDataError, ORG_UNIT_TYPE_BRANCH
        from nodeone.core.master.org_unit import OrgUnitService

        mock_model.query.filter_by.return_value.first.return_value = MagicMock()
        with self.assertRaises(MasterDataError):
            OrgUnitService.create(
                1,
                unit_ref='SUC-01',
                name='Dup',
                unit_type=ORG_UNIT_TYPE_BRANCH,
            )

    @patch('nodeone.core.master.org_unit.CoreOrgUnit')
    def test_list_units(self, mock_model):
        from nodeone.core.master.org_unit import OrgUnitService

        row = MagicMock()
        row.id = 2
        row.organization_id = 1
        row.unit_ref = 'WH-01'
        row.name = 'Bodega'
        row.unit_type = 'warehouse'
        row.status = 'active'
        row.parent_id = 1
        row.notes = None
        mock_model.query.filter_by.return_value.filter_by.return_value.order_by.return_value.all.return_value = [
            row
        ]
        items = OrgUnitService.list_units(1, unit_type='warehouse')
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].unit_ref, 'WH-01')


class TestCoreMasterModels(unittest.TestCase):
    def test_model_tables(self):
        from models.core_master import CoreAddress, CoreAttachment, CoreOrgUnit, CoreProduct

        self.assertEqual(CoreOrgUnit.__tablename__, 'core_org_unit')
        self.assertEqual(CoreAddress.__tablename__, 'core_address')
        self.assertEqual(CoreAttachment.__tablename__, 'core_attachment')
        self.assertEqual(CoreProduct.__tablename__, 'core_product')


class TestCoreProductService(unittest.TestCase):
    def test_legacy_catalog_map(self):
        from nodeone.core.master.constants import LEGACY_CATALOG_SOURCES, PRODUCT_TYPE_SERVICE

        self.assertIn(PRODUCT_TYPE_SERVICE, LEGACY_CATALOG_SOURCES)

    @patch('app.db')
    @patch('nodeone.core.master.product.CoreProduct')
    def test_create_product(self, mock_model, mock_db):
        from nodeone.core.master.constants import PRODUCT_TYPE_GOOD
        from nodeone.core.master.product import CoreProductService

        mock_model.query.filter_by.return_value.first.return_value = None
        row = MagicMock()
        row.id = 10
        row.organization_id = 1
        row.product_ref = 'SKU-100'
        row.name = 'Agua'
        row.product_type = PRODUCT_TYPE_GOOD
        row.status = 'active'
        row.tracks_inventory = False
        row.unit_price = 1.0
        row.currency = 'USD'
        row.description = None
        row.source_app_id = None
        mock_model.return_value = row
        dto = CoreProductService.create(
            1,
            {'product_ref': 'SKU-100', 'name': 'Agua', 'product_type': PRODUCT_TYPE_GOOD},
        )
        self.assertEqual(dto.name, 'Agua')


class TestUserContactLinkService(unittest.TestCase):
    @patch('nodeone.core.services.user_contact.ContactService.get')
    @patch('app.db')
    @patch('models.users.User')
    def test_link_user_to_contact(self, mock_user_cls, mock_db, mock_get_contact):
        from nodeone.core.services.contacts import ContactDTO
        from nodeone.core.services.user_contact import UserContactLinkService

        user = MagicMock()
        user.id = 5
        user.organization_id = 1
        user.linked_contact_id = None
        mock_user_cls.query.get.return_value = user

        contact_dto = ContactDTO(
            id=99,
            organization_id=1,
            display_name='Ana',
            email='ana@example.com',
            phone=None,
            mobile=None,
            contact_type='person',
            identification_type='consumer_final',
            tax_id=None,
            dv=None,
            is_customer=False,
            is_supplier=False,
            is_member=False,
            is_student=False,
            is_participant=False,
            is_instructor=False,
            is_employee=True,
            active=True,
            roles=('Empleado',),
        )
        mock_get_contact.return_value = contact_dto

        def _commit_side_effect():
            user.linked_contact_id = 99

        mock_db.session.commit.side_effect = _commit_side_effect

        dto = UserContactLinkService.link(5, 1, 99)
        self.assertEqual(dto.linked_contact_id, 99)
        self.assertEqual(dto.contact.display_name, 'Ana')
        mock_db.session.commit.assert_called()

    @patch('models.users.User')
    def test_link_rejects_org_mismatch(self, mock_user_cls):
        from nodeone.core.master.constants import MasterDataError
        from nodeone.core.services.user_contact import UserContactLinkService

        user = MagicMock()
        user.id = 5
        user.organization_id = 2
        mock_user_cls.query.get.return_value = user
        with self.assertRaises(MasterDataError):
            UserContactLinkService.link(5, 1, 99)


if __name__ == '__main__':
    unittest.main()
