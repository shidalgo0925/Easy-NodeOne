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
        from models.core_master import CoreAddress, CoreAttachment, CoreOrgUnit

        self.assertEqual(CoreOrgUnit.__tablename__, 'core_org_unit')
        self.assertEqual(CoreAddress.__tablename__, 'core_address')
        self.assertEqual(CoreAttachment.__tablename__, 'core_attachment')


if __name__ == '__main__':
    unittest.main()
