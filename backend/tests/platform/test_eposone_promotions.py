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


class TestPromotionCompute(unittest.TestCase):
    def test_compute_discount_percent(self):
        from nodeone.modules.eposone.promotion_service import PromotionDTO, PromotionService

        promo = PromotionDTO(
            id=1,
            organization_id=1,
            promo_ref='PROMO-0001',
            name='20% off',
            promo_type='percent',
            value=20.0,
            code='SAVE20',
            active=True,
        )
        self.assertEqual(PromotionService.compute_discount(promo, 100.0), 20.0)
        self.assertEqual(PromotionService.compute_discount(promo, 50.0), 10.0)

    def test_compute_discount_fixed_capped_at_subtotal(self):
        from nodeone.modules.eposone.promotion_service import PromotionDTO, PromotionService

        promo = PromotionDTO(
            id=2,
            organization_id=1,
            promo_ref='PROMO-0002',
            name='$15 off',
            promo_type='fixed',
            value=15.0,
            code=None,
            active=True,
        )
        self.assertEqual(PromotionService.compute_discount(promo, 100.0), 15.0)
        self.assertEqual(PromotionService.compute_discount(promo, 10.0), 10.0)


class TestPromotionApplyToOrder(unittest.TestCase):
    @patch('app.db')
    @patch('nodeone.modules.eposone.promotion_service.EposonePromotion')
    @patch('nodeone.core.commerce.order.CoreCommercialOrder')
    def test_apply_promotion_by_code(self, mock_order_cls, mock_promo_cls, mock_db):
        from nodeone.core.commerce.order import OrderService

        line = MagicMock()
        line.line_total = 100.0
        row = MagicMock()
        row.id = 5
        row.organization_id = 1
        row.status = 'draft'
        row.payment_status = 'unpaid'
        row.tax_total = 0.0
        row.lines = [line]
        row.version = 1
        row.sync_payment_status.return_value = 'unpaid'
        mock_order_cls.query.filter_by.return_value.first.return_value = row

        promo_row = MagicMock()
        promo_row.id = 1
        promo_row.organization_id = 1
        promo_row.promo_ref = 'PROMO-0001'
        promo_row.name = 'Happy'
        promo_row.promo_type = 'percent'
        promo_row.value = 20.0
        promo_row.code = 'HAPPY20'
        promo_row.active = True
        mock_promo_cls.query.filter_by.return_value.first.return_value = promo_row

        with patch('nodeone.core.commerce.order.order_to_dto') as mock_dto:
            mock_dto.return_value = MagicMock(discount_total=20.0, grand_total=80.0)
            dto = OrderService.apply_promotion(1, 5, code='HAPPY20')
        self.assertEqual(row.promotion_ref, 'PROMO-0001')
        self.assertEqual(row.discount_total, 20.0)
        self.assertEqual(row.grand_total, 80.0)
        mock_db.session.commit.assert_called_once()
        self.assertIsNotNone(dto)


class TestPromotionSections(unittest.TestCase):
    def test_promotions_slug(self):
        from nodeone.modules.eposone.sections import EPOSONE_SECTION_SLUGS

        self.assertIn('promotions', EPOSONE_SECTION_SLUGS)


if __name__ == '__main__':
    unittest.main()
