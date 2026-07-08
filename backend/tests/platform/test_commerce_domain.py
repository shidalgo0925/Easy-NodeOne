"""Tests dominio comercial — Etapa 12."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestCommerceConstants(unittest.TestCase):
    def test_order_transitions(self):
        from nodeone.core.commerce.constants import (
            ORDER_STATUS_CANCELLED,
            ORDER_STATUS_CONFIRMED,
            ORDER_STATUS_DRAFT,
            ORDER_STATUS_DELIVERED,
            ORDER_STATUS_IN_PROGRESS,
            can_transition_order_status,
        )

        self.assertTrue(can_transition_order_status(ORDER_STATUS_DRAFT, ORDER_STATUS_CONFIRMED))
        self.assertTrue(
            can_transition_order_status(ORDER_STATUS_CONFIRMED, ORDER_STATUS_IN_PROGRESS)
        )
        self.assertFalse(can_transition_order_status(ORDER_STATUS_DRAFT, ORDER_STATUS_DELIVERED))
        self.assertFalse(can_transition_order_status(ORDER_STATUS_CANCELLED, ORDER_STATUS_CONFIRMED))

    def test_commerce_event_types_complete(self):
        from nodeone.core.commerce import events as ev

        self.assertIn(ev.COMMERCE_ORDER_CREATED, ev.COMMERCE_EVENT_TYPES)
        self.assertIn(ev.COMMERCE_PAYMENT_CAPTURED, ev.COMMERCE_EVENT_TYPES)


class TestOrderService(unittest.TestCase):
    def test_create_not_ready(self):
        from nodeone.core.commerce.order import CommerceNotReadyError, OrderService

        with self.assertRaises(CommerceNotReadyError):
            OrderService.create(1, {'order_ref': 'O-1'})

    @patch('nodeone.core.commerce.order.AuditService.publish_domain_event')
    def test_publish_created(self, mock_publish):
        from nodeone.core.commerce.events import COMMERCE_ORDER_CREATED
        from nodeone.core.commerce.order import OrderService

        OrderService.publish_created(1, order_ref='O-100', status='created', grand_total=9.5)
        mock_publish.assert_called_once()
        args = mock_publish.call_args[0]
        self.assertEqual(args[0], 1)
        self.assertEqual(args[1], COMMERCE_ORDER_CREATED)
        self.assertEqual(args[2]['order_ref'], 'O-100')


class TestInvoiceService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    @patch('nodeone.modules.accounting.models.InvoiceLine')
    @patch('nodeone.modules.accounting.models.Invoice')
    def test_get_returns_dto(self, mock_invoice_cls, mock_line_cls):
        from nodeone.core.commerce.invoice import InvoiceService

        row = MagicMock()
        row.id = 10
        row.organization_id = 1
        row.number = 'INV-001'
        row.status = 'posted'
        row.contact_id = 5
        row.currency = 'USD'
        row.grand_total = 100.0
        row.amount_paid = 0.0
        row.date = None

        line = MagicMock()
        line.description = 'Item'
        line.quantity = 1.0
        line.price_unit = 100.0
        line.total = 100.0
        line.product_id = None

        mock_invoice_cls.query.filter_by.return_value.first.return_value = row
        mock_line_cls.query.filter_by.return_value.order_by.return_value.all.return_value = [line]

        dto = InvoiceService.get(1, 10)
        self.assertIsNotNone(dto)
        self.assertEqual(dto.number, 'INV-001')
        self.assertEqual(dto.kind, 'fiscal')
        self.assertEqual(len(dto.lines), 1)


if __name__ == '__main__':
    unittest.main()
