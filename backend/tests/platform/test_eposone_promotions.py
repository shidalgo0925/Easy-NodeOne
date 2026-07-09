"""Tests promociones EPosOne."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestPromotionService(unittest.TestCase):
    def test_next_promo_ref(self):
        from nodeone.modules.eposone.promotion_service import PromotionService

        with patch('nodeone.modules.eposone.promotion_service.EposonePromotion') as mock_model:
            mock_model.query.filter_by.return_value.with_entities.return_value.all.return_value = [
                ('PROMO-0005',),
            ]
            ref = PromotionService._next_promo_ref(1)
        self.assertEqual(ref, 'PROMO-0006')

    @patch('app.db')
    @patch('nodeone.modules.eposone.promotion_service.EposonePromotion')
    def test_create_promotion_percent(self, mock_promo_cls, mock_db):
        from nodeone.modules.eposone.promotion_service import PromotionService

        row = MagicMock()
        row.id = 1
        row.organization_id = 1
        row.promo_ref = 'PROMO-0001'
        row.name = 'Happy hour'
        row.promo_type = 'percent'
        row.value = 20.0
        row.code = 'HAPPY20'
        row.active = True
        mock_promo_cls.return_value = row
        mock_promo_cls.query.filter_by.return_value.first.return_value = None

        with patch.object(PromotionService, '_next_promo_ref', return_value='PROMO-0001'):
            dto = PromotionService.create_promotion(
                1,
                name='Happy hour',
                promo_type='percent',
                value=20,
                code='happy20',
            )
        self.assertEqual(dto.promo_ref, 'PROMO-0001')
        self.assertEqual(dto.code, 'HAPPY20')

    @patch('app.db')
    @patch('nodeone.modules.eposone.promotion_service.EposonePromotion')
    def test_set_active(self, mock_promo_cls, mock_db):
        from nodeone.modules.eposone.promotion_service import PromotionService

        row = MagicMock()
        row.id = 2
        row.organization_id = 1
        row.promo_ref = 'PROMO-0002'
        row.name = 'Descuento fijo'
        row.promo_type = 'fixed'
        row.value = 5.0
        row.code = None
        row.active = True
        mock_promo_cls.query.filter_by.return_value.first.return_value = row

        dto = PromotionService.set_active(1, 2, active=False)
        self.assertFalse(dto.active)
        self.assertFalse(row.active)


class TestPromotionSections(unittest.TestCase):
    def test_promotions_slug(self):
        from nodeone.modules.eposone.sections import EPOSONE_SECTION_SLUGS

        self.assertIn('promotions', EPOSONE_SECTION_SLUGS)


if __name__ == '__main__':
    unittest.main()
