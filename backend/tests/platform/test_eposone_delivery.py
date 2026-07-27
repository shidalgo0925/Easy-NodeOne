"""Tests Delivery EPosOne — Etapa 16."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestDeliveryService(unittest.TestCase):
    def test_delivery_transitions(self):
        from models.eposone_delivery import DELIVERY_STATUS_PENDING, DELIVERY_TRANSITIONS

        self.assertIn('assigned', DELIVERY_TRANSITIONS[DELIVERY_STATUS_PENDING])

    @patch('nodeone.modules.eposone.delivery_service.AuditService.publish_domain_event')
    @patch('app.db')
    @patch('nodeone.modules.eposone.delivery_service.EposoneDelivery')
    @patch('nodeone.modules.eposone.delivery_service.CoreCommercialOrder')
    def test_create_for_order(self, mock_order_cls, mock_delivery_cls, mock_db, _mock_pub):
        from nodeone.modules.eposone.delivery_service import EposoneDeliveryService

        order = MagicMock()
        order.id = 3
        order.order_ref = 'POS-0002'
        order.lines = [MagicMock(quantity=2.0)]
        mock_order_cls.query.filter_by.return_value.first.return_value = order
        mock_delivery_cls.query.filter_by.return_value.first.return_value = None

        row = MagicMock()
        row.id = 1
        row.organization_id = 1
        row.order_ref = 'POS-0002'
        row.status = 'pending'
        row.delivered_qty = 0.0
        row.total_qty = 2.0
        mock_delivery_cls.return_value = row

        dto = EposoneDeliveryService.create_for_order(1, 3, destination_address='Calle 1')
        self.assertEqual(dto.order_ref, 'POS-0002')
        self.assertEqual(dto.total_qty, 2.0)


class TestDeliverySections(unittest.TestCase):
    def test_delivery_section_slug(self):
        from nodeone.modules.eposone.sections import EPOSONE_SECTION_SLUGS

        self.assertIn('delivery', EPOSONE_SECTION_SLUGS)


if __name__ == '__main__':
    unittest.main()
