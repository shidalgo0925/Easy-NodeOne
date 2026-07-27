"""Tests menú digital EPosOne — Etapa 17."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestDigitalMenuService(unittest.TestCase):
    def test_next_menu_ref(self):
        from nodeone.modules.eposone.digital_menu_service import DigitalMenuService

        with patch('nodeone.modules.eposone.digital_menu_service.EposoneDigitalMenu') as mock_model:
            mock_model.query.filter_by.return_value.with_entities.return_value.all.return_value = [
                ('MENU-0002',),
            ]
            ref = DigitalMenuService._next_menu_ref(1)
        self.assertEqual(ref, 'MENU-0003')

    @patch('app.db')
    @patch('nodeone.modules.eposone.digital_menu_service.EposoneDigitalMenu')
    def test_create_menu(self, mock_menu_cls, mock_db):
        from nodeone.modules.eposone.digital_menu_service import DigitalMenuService

        row = MagicMock()
        row.id = 1
        row.organization_id = 1
        row.menu_ref = 'MENU-0001'
        row.name = 'Almuerzo'
        row.public_token = 'tok123'
        row.active = True
        item = MagicMock(
            id=10,
            name='Sopa',
            description=None,
            category=None,
            price=5.0,
            available=True,
            sort_order=0,
        )
        row.items = [item]
        mock_menu_cls.return_value = row

        with patch.object(DigitalMenuService, '_next_menu_ref', return_value='MENU-0001'):
            with patch.object(DigitalMenuService, '_build_items', return_value=[item]):
                dto = DigitalMenuService.create_menu(
                    1,
                    name='Almuerzo',
                    items=[{'name': 'Sopa', 'price': 5}],
                )
        self.assertEqual(dto.name, 'Almuerzo')
        self.assertEqual(len(dto.items), 1)

    @patch('app.db')
    @patch('nodeone.modules.eposone.digital_menu_service.EposoneDigitalMenu')
    def test_set_active(self, mock_menu_cls, mock_db):
        from nodeone.modules.eposone.digital_menu_service import DigitalMenuService

        row = MagicMock()
        row.id = 1
        row.organization_id = 1
        row.menu_ref = 'MENU-0001'
        row.name = 'Almuerzo'
        row.public_token = 'tok123'
        row.active = True
        row.items = []
        mock_menu_cls.query.filter_by.return_value.first.return_value = row

        dto = DigitalMenuService.set_active(1, 1, active=False)
        self.assertFalse(dto.active)
        self.assertFalse(row.active)


class TestDigitalMenuSections(unittest.TestCase):
    def test_digital_menu_slug(self):
        from nodeone.modules.eposone.sections import EPOSONE_SECTION_SLUGS

        self.assertIn('digital-menu', EPOSONE_SECTION_SLUGS)


if __name__ == '__main__':
    unittest.main()
