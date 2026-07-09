"""Tests modelo maestro Core — Etapa 10b."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestCoreMasterConstants(unittest.TestCase):
    def test_org_unit_types(self):
        from nodeone.core.master.constants import (
            ORG_UNIT_TYPE_BRANCH,
            ORG_UNIT_TYPE_REGISTER,
            ORG_UNIT_TYPE_WAREHOUSE,
            ORG_UNIT_TYPES,
        )

        self.assertIn(ORG_UNIT_TYPE_BRANCH, ORG_UNIT_TYPES)
        self.assertIn(ORG_UNIT_TYPE_WAREHOUSE, ORG_UNIT_TYPES)
        self.assertIn(ORG_UNIT_TYPE_REGISTER, ORG_UNIT_TYPES)


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
        from models.core_master import CoreAddress, CoreAttachment, CoreContactLegacyLink, CoreOrgUnit, CoreProduct

        self.assertEqual(CoreOrgUnit.__tablename__, 'core_org_unit')
        self.assertEqual(CoreAddress.__tablename__, 'core_address')
        self.assertEqual(CoreAttachment.__tablename__, 'core_attachment')
        self.assertEqual(CoreProduct.__tablename__, 'core_product')
        self.assertEqual(CoreContactLegacyLink.__tablename__, 'core_contact_legacy_link')


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


class TestContactBridgeService(unittest.TestCase):
    def test_legacy_contact_to_dto(self):
        from nodeone.core.master.contact_bridge import CONTACT_SOURCE_LEGACY, legacy_contact_to_dto

        row = MagicMock()
        row.id = 7
        row.organization_id = 1
        row.legal_name = 'Acme SA'
        row.trade_name = None
        row.name = 'Acme'
        row.company = None
        row.email = 'acme@example.com'
        row.fiscal_email = None
        row.phone = '6000'
        row.fiscal_phone = None
        row.person_type = 'juridica'
        row.id_type = 'ruc'
        row.tax_id = '123'
        row.tax_dv = '45'
        row.is_customer = True
        row.is_supplier = False
        row.is_salesperson = False
        row.is_active = True
        dto = legacy_contact_to_dto(row)
        self.assertEqual(dto.display_name, 'Acme SA')
        self.assertEqual(dto.contact_type, 'company')
        self.assertIn('Cliente', dto.roles)

    @patch('nodeone.core.master.contact_bridge.ContactService.get')
    def test_resolve_canonical(self, mock_get):
        from nodeone.core.master.contact_bridge import CONTACT_SOURCE_CANONICAL, ContactBridgeService
        from nodeone.core.services.contacts import ContactDTO

        mock_get.return_value = ContactDTO(
            id=3,
            organization_id=1,
            display_name='Ana',
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
        with patch.object(ContactBridgeService, 'get_link_by_canonical', return_value=None):
            resolved = ContactBridgeService.resolve(1, 3)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.source, CONTACT_SOURCE_CANONICAL)

    @patch('nodeone.core.master.contact_bridge.ContactService.get', return_value=None)
    @patch('nodeone.core.master.contact_bridge.ContactBridgeService.get_link_by_legacy', return_value=None)
    @patch('nodeone.core.master.contact_bridge.ContactBridgeService.get_legacy')
    def test_resolve_legacy_projection(self, mock_legacy, _mock_link, _mock_get):
        from nodeone.core.master.contact_bridge import CONTACT_SOURCE_LEGACY, ContactBridgeService

        row = MagicMock()
        row.id = 9
        row.organization_id = 1
        row.legal_name = 'Legacy Co'
        row.trade_name = None
        row.name = 'Legacy'
        row.company = None
        row.email = 'legacy@example.com'
        row.fiscal_email = None
        row.phone = None
        row.fiscal_phone = None
        row.person_type = 'natural'
        row.id_type = None
        row.tax_id = None
        row.tax_dv = None
        row.is_customer = True
        row.is_supplier = False
        row.is_salesperson = False
        row.is_active = True
        mock_legacy.return_value = row
        resolved = ContactBridgeService.resolve(1, 9)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.source, CONTACT_SOURCE_LEGACY)

    @patch('nodeone.core.master.contact_bridge.ContactBridgeService.link')
    @patch('nodeone.core.master.contact_bridge.ContactService.create')
    @patch('nodeone.core.master.contact_bridge.ContactService.find_by_email', return_value=None)
    @patch('nodeone.core.master.contact_bridge.ContactService.find_by_tax_id', return_value=None)
    @patch('nodeone.core.master.contact_bridge.ContactBridgeService.get_link_by_legacy', return_value=None)
    @patch('nodeone.core.master.contact_bridge.ContactBridgeService.get_legacy')
    @patch('nodeone.core.master.contact_bridge.ContactBridgeService.resolve')
    def test_promote_legacy_creates_and_links(
        self,
        mock_resolve,
        mock_legacy,
        _mock_link_existing,
        _mock_tax,
        _mock_email,
        mock_create,
        mock_link,
    ):
        from nodeone.core.master.contact_bridge import CONTACT_SOURCE_LINKED, ContactBridgeService
        from nodeone.core.services.contacts import ContactDTO

        legacy_row = MagicMock()
        legacy_row.id = 9
        legacy_row.organization_id = 1
        legacy_row.legal_name = 'Legacy Co'
        legacy_row.trade_name = None
        legacy_row.name = 'Legacy'
        legacy_row.company = None
        legacy_row.email = 'legacy@example.com'
        legacy_row.fiscal_email = None
        legacy_row.phone = None
        legacy_row.fiscal_phone = None
        legacy_row.person_type = 'natural'
        legacy_row.id_type = None
        legacy_row.tax_id = None
        legacy_row.tax_dv = None
        legacy_row.is_customer = True
        legacy_row.is_supplier = False
        legacy_row.is_salesperson = False
        legacy_row.is_active = True
        mock_legacy.return_value = legacy_row

        created = ContactDTO(
            id=20,
            organization_id=1,
            display_name='Legacy Co',
            email='legacy@example.com',
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
        mock_create.return_value = created
        from nodeone.core.master.contact_bridge import ResolvedContactDTO

        mock_resolve.return_value = ResolvedContactDTO(
            contact=created,
            source=CONTACT_SOURCE_LINKED,
            canonical_contact_id=20,
            legacy_crm_contact_id=9,
        )

        resolved = ContactBridgeService.promote_legacy(1, 9)
        self.assertEqual(resolved.canonical_contact_id, 20)
        mock_link.assert_called_once()
        mock_create.assert_called_once()
        self.assertEqual(resolved.legacy_crm_contact_id, 9)


if __name__ == '__main__':
    unittest.main()
