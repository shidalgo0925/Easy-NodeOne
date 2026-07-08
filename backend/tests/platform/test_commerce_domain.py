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
        self.assertIn(ev.COMMERCE_ORDER_PAYMENT_STATUS_CHANGED, ev.COMMERCE_EVENT_TYPES)
        self.assertIn(ev.COMMERCE_ORDER_FISCAL_STATUS_CHANGED, ev.COMMERCE_EVENT_TYPES)

    def test_compute_order_payment_status(self):
        from nodeone.core.commerce.constants import (
            ORDER_PAYMENT_STATUS_OVERPAID,
            ORDER_PAYMENT_STATUS_PAID,
            ORDER_PAYMENT_STATUS_PARTIAL,
            ORDER_PAYMENT_STATUS_UNPAID,
            compute_order_payment_status,
        )

        self.assertEqual(compute_order_payment_status(0, 10), ORDER_PAYMENT_STATUS_UNPAID)
        self.assertEqual(compute_order_payment_status(5, 10), ORDER_PAYMENT_STATUS_PARTIAL)
        self.assertEqual(compute_order_payment_status(10, 10), ORDER_PAYMENT_STATUS_PAID)
        self.assertEqual(compute_order_payment_status(12, 10), ORDER_PAYMENT_STATUS_OVERPAID)


class TestPaymentServiceAxis(unittest.TestCase):
    @patch('nodeone.core.commerce.payment.OrderService.publish_fiscal_status_changed')
    @patch('nodeone.core.commerce.payment.OrderService.publish_payment_status_changed')
    @patch('nodeone.core.commerce.payment.PaymentService.publish_captured')
    @patch('nodeone.core.commerce.payment.PaymentService.publish_initiated')
    @patch('nodeone.core.commerce.payment.PaymentService._next_payment_ref', return_value='PAY-0001')
    @patch('app.db')
    @patch('nodeone.core.commerce.payment.CoreCommercialPayment')
    @patch('nodeone.core.commerce.payment.CoreCommercialOrder')
    def test_capture_updates_payment_status_not_operational(
        self,
        mock_order_cls,
        mock_payment_cls,
        mock_db,
        _next_ref,
        mock_initiated,
        mock_captured,
        mock_payment_changed,
        mock_fiscal_changed,
    ):
        from nodeone.core.commerce.constants import ORDER_PAYMENT_STATUS_PAID, ORDER_STATUS_IN_PROGRESS
        from nodeone.core.commerce.payment import PaymentService

        order = MagicMock()
        order.id = 7
        order.order_ref = 'POS-0001'
        order.status = ORDER_STATUS_IN_PROGRESS
        order.payment_status = 'unpaid'
        order.fiscal_status = 'not_required'
        order.amount_paid = 0.0
        order.grand_total = 10.0
        order.currency = 'USD'
        order.version = 1

        def _sync():
            order.payment_status = ORDER_PAYMENT_STATUS_PAID
            return ORDER_PAYMENT_STATUS_PAID

        order.sync_payment_status.side_effect = _sync

        def _fiscal(*, skip_fiscal=False):
            if skip_fiscal:
                return None
            order.fiscal_status = 'pending'
            return 'not_required'

        order.maybe_mark_fiscal_pending.side_effect = _fiscal
        mock_order_cls.query.filter_by.return_value.first.return_value = order

        pay_row = MagicMock()
        pay_row.id = 1
        pay_row.organization_id = 1
        pay_row.payment_ref = 'PAY-0001'
        pay_row.status = 'captured'
        pay_row.payment_type = 'cash'
        pay_row.amount = 10.0
        pay_row.currency = 'USD'
        pay_row.captured_at = None
        mock_payment_cls.return_value = pay_row

        PaymentService.capture(1, {'order_id': 7, 'amount': 10})

        self.assertEqual(order.status, ORDER_STATUS_IN_PROGRESS)
        mock_payment_changed.assert_called_once()
        mock_fiscal_changed.assert_called_once()

    @patch('nodeone.core.commerce.payment.OrderService.publish_fiscal_status_changed')
    @patch('nodeone.core.commerce.payment.OrderService.publish_payment_status_changed')
    @patch('nodeone.core.commerce.payment.PaymentService.publish_captured')
    @patch('nodeone.core.commerce.payment.PaymentService.publish_initiated')
    @patch('nodeone.core.commerce.payment.PaymentService._next_payment_ref', return_value='PAY-0002')
    @patch('app.db')
    @patch('nodeone.core.commerce.payment.CoreCommercialPayment')
    @patch('nodeone.core.commerce.payment.CoreCommercialOrder')
    def test_capture_skip_fiscal_opt_out(
        self,
        mock_order_cls,
        mock_payment_cls,
        mock_db,
        _next_ref,
        mock_initiated,
        mock_captured,
        mock_payment_changed,
        mock_fiscal_changed,
    ):
        from nodeone.core.commerce.constants import ORDER_PAYMENT_STATUS_PAID
        from nodeone.core.commerce.payment import PaymentService

        order = MagicMock()
        order.id = 8
        order.order_ref = 'POS-0002'
        order.status = 'confirmed'
        order.payment_status = 'unpaid'
        order.fiscal_status = 'not_required'
        order.amount_paid = 0.0
        order.grand_total = 5.0
        order.currency = 'USD'
        order.version = 1
        order.sync_payment_status.return_value = ORDER_PAYMENT_STATUS_PAID
        order.maybe_mark_fiscal_pending.return_value = None
        mock_order_cls.query.filter_by.return_value.first.return_value = order

        pay_row = MagicMock()
        pay_row.payment_ref = 'PAY-0002'
        pay_row.status = 'captured'
        pay_row.payment_type = 'cash'
        pay_row.amount = 5.0
        pay_row.currency = 'USD'
        pay_row.captured_at = None
        mock_payment_cls.return_value = pay_row

        PaymentService.capture(1, {'order_id': 8, 'amount': 5, 'skip_fiscal': True})

        order.maybe_mark_fiscal_pending.assert_called_once_with(skip_fiscal=True)
        mock_fiscal_changed.assert_not_called()


class TestOrderService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    def test_create_requires_lines(self):
        from nodeone.core.commerce.order import OrderService, OrderValidationError

        with self.app.app_context():
            with self.assertRaises(OrderValidationError):
                OrderService.create(1, {})

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
