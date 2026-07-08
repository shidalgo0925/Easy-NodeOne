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
        self.assertIn(ev.COMMERCE_INVOICE_REQUESTED, ev.COMMERCE_EVENT_TYPES)
        self.assertIn(ev.COMMERCE_CASH_MOVEMENT_RECORDED, ev.COMMERCE_EVENT_TYPES)
        self.assertIn(ev.COMMERCE_CASH_SHIFT_RECONCILING, ev.COMMERCE_EVENT_TYPES)

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

    def test_order_model_status_alias(self):
        from models.commercial_core import CoreCommercialOrder

        row = CoreCommercialOrder()
        row.operational_status = 'confirmed'
        self.assertEqual(row.status, 'confirmed')
        row.status = 'in_progress'
        self.assertEqual(row.operational_status, 'in_progress')


class TestPaymentServiceAxis(unittest.TestCase):
    @patch('nodeone.core.commerce.cash.CashRegisterService.record_movement')
    @patch('nodeone.core.commerce.cash.CashRegisterService.require_open_shift')
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
        mock_require_shift,
        mock_record_movement,
    ):
        from nodeone.core.commerce.constants import ORDER_PAYMENT_STATUS_PAID, ORDER_STATUS_IN_PROGRESS
        from nodeone.core.commerce.payment import PaymentService

        shift = MagicMock()
        shift.id = 3
        mock_require_shift.return_value = shift

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

        PaymentService.capture(1, {'order_id': 7, 'amount': 10, 'register_ref': 'REG-1'})

        self.assertEqual(order.status, ORDER_STATUS_IN_PROGRESS)
        mock_payment_changed.assert_called_once()
        mock_fiscal_changed.assert_called_once()

    @patch('nodeone.core.commerce.cash.CashRegisterService.record_movement')
    @patch('nodeone.core.commerce.cash.CashRegisterService.require_open_shift')
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
        mock_require_shift,
        mock_record_movement,
    ):
        from nodeone.core.commerce.constants import ORDER_PAYMENT_STATUS_PAID
        from nodeone.core.commerce.payment import PaymentService

        shift = MagicMock()
        shift.id = 4
        mock_require_shift.return_value = shift

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

        PaymentService.capture(
            1,
            {'order_id': 8, 'amount': 5, 'skip_fiscal': True, 'register_ref': 'REG-1'},
        )

        order.maybe_mark_fiscal_pending.assert_called_once_with(skip_fiscal=True)
        mock_fiscal_changed.assert_not_called()


class TestPaymentRefund(unittest.TestCase):
    @patch('nodeone.core.commerce.payment.PaymentService.publish_refunded')
    @patch('nodeone.core.commerce.payment.OrderService.publish_status_changed')
    @patch('nodeone.core.commerce.payment.OrderService.publish_fiscal_status_changed')
    @patch('nodeone.core.commerce.payment.OrderService.publish_payment_status_changed')
    @patch('app.db')
    @patch('nodeone.core.commerce.payment.CoreCommercialPayment')
    @patch('nodeone.core.commerce.payment.CoreCommercialOrder')
    def test_refund_full_reverts_payment_and_order_axes(
        self,
        mock_order_cls,
        mock_payment_cls,
        mock_db,
        mock_payment_changed,
        mock_fiscal_changed,
        mock_status_changed,
        mock_refunded,
    ):
        from nodeone.core.commerce.constants import (
            ORDER_FISCAL_STATUS_NOT_REQUIRED,
            ORDER_FISCAL_STATUS_PENDING,
            ORDER_PAYMENT_STATUS_PAID,
            ORDER_PAYMENT_STATUS_UNPAID,
            ORDER_STATUS_DELIVERED,
            ORDER_STATUS_REFUNDED,
            PAYMENT_STATUS_REFUNDED,
        )
        from nodeone.core.commerce.payment import PaymentService

        order = MagicMock()
        order.id = 10
        order.order_ref = 'POS-0010'
        order.status = ORDER_STATUS_DELIVERED
        order.payment_status = ORDER_PAYMENT_STATUS_PAID
        order.fiscal_status = ORDER_FISCAL_STATUS_PENDING
        order.amount_paid = 15.0
        order.grand_total = 15.0
        order.version = 1

        def _sync():
            order.payment_status = ORDER_PAYMENT_STATUS_UNPAID
            return ORDER_PAYMENT_STATUS_UNPAID

        order.sync_payment_status.side_effect = _sync

        pay_row = MagicMock()
        pay_row.id = 5
        pay_row.order_id = 10
        pay_row.payment_ref = 'PAY-0010'
        pay_row.status = 'captured'
        pay_row.amount = 15.0
        pay_row.refunded_amount = 0.0
        pay_row.payment_type = 'card'
        pay_row.cash_shift_id = None
        pay_row.currency = 'USD'
        pay_row.captured_at = None

        mock_payment_cls.query.filter_by.return_value.first.return_value = pay_row
        mock_order_cls.query.filter_by.return_value.first.return_value = order

        result = PaymentService.refund(1, 5)

        self.assertEqual(pay_row.status, PAYMENT_STATUS_REFUNDED)
        self.assertEqual(order.amount_paid, 0.0)
        self.assertEqual(order.status, ORDER_STATUS_REFUNDED)
        self.assertEqual(order.fiscal_status, ORDER_FISCAL_STATUS_NOT_REQUIRED)
        mock_payment_changed.assert_called_once()
        mock_fiscal_changed.assert_called_once()
        mock_status_changed.assert_called_once()
        mock_refunded.assert_called_once()
        self.assertEqual(result.payment_ref, 'PAY-0010')

    @patch('nodeone.core.commerce.payment.PaymentService.publish_refunded')
    @patch('nodeone.core.commerce.payment.OrderService.publish_status_changed')
    @patch('nodeone.core.commerce.payment.OrderService.publish_payment_status_changed')
    @patch('app.db')
    @patch('nodeone.core.commerce.payment.CoreCommercialPayment')
    @patch('nodeone.core.commerce.payment.CoreCommercialOrder')
    def test_refund_partial_does_not_change_operational(
        self,
        mock_order_cls,
        mock_payment_cls,
        mock_db,
        mock_payment_changed,
        mock_status_changed,
        mock_refunded,
    ):
        from nodeone.core.commerce.constants import (
            ORDER_PAYMENT_STATUS_PARTIAL,
            ORDER_STATUS_DELIVERED,
            PAYMENT_STATUS_PARTIAL_REFUND,
        )
        from nodeone.core.commerce.payment import PaymentService

        order = MagicMock()
        order.id = 11
        order.order_ref = 'POS-0011'
        order.status = ORDER_STATUS_DELIVERED
        order.payment_status = 'paid'
        order.fiscal_status = 'invoiced'
        order.amount_paid = 20.0
        order.grand_total = 20.0
        order.version = 1
        order.sync_payment_status.return_value = ORDER_PAYMENT_STATUS_PARTIAL

        pay_row = MagicMock()
        pay_row.id = 6
        pay_row.order_id = 11
        pay_row.payment_ref = 'PAY-0011'
        pay_row.status = 'captured'
        pay_row.amount = 20.0
        pay_row.refunded_amount = 0.0
        pay_row.payment_type = 'card'
        pay_row.cash_shift_id = None
        pay_row.currency = 'USD'
        pay_row.captured_at = None

        mock_payment_cls.query.filter_by.return_value.first.return_value = pay_row
        mock_order_cls.query.filter_by.return_value.first.return_value = order

        PaymentService.refund(1, 6, amount=5.0)

        self.assertEqual(pay_row.status, PAYMENT_STATUS_PARTIAL_REFUND)
        self.assertEqual(pay_row.refunded_amount, 5.0)
        self.assertEqual(order.amount_paid, 15.0)
        self.assertEqual(order.status, ORDER_STATUS_DELIVERED)
        mock_status_changed.assert_not_called()
        mock_payment_changed.assert_called_once()
        mock_refunded.assert_called_once()

    @patch('nodeone.core.commerce.payment.CoreCommercialPayment')
    def test_refund_rejects_non_captured(self, mock_payment_cls):
        from nodeone.core.commerce.order import OrderValidationError
        from nodeone.core.commerce.payment import PaymentService

        pay_row = MagicMock()
        pay_row.status = 'refunded'
        mock_payment_cls.query.filter_by.return_value.first.return_value = pay_row

        with self.assertRaises(OrderValidationError):
            PaymentService.refund(1, 99)

    @patch('nodeone.core.commerce.payment.PaymentService.publish_refunded')
    @patch('nodeone.core.commerce.payment.OrderService.publish_status_changed')
    @patch('nodeone.core.commerce.payment.OrderService.publish_payment_status_changed')
    @patch('app.db')
    @patch('nodeone.core.commerce.payment.CoreCommercialPayment')
    @patch('nodeone.core.commerce.payment.CoreCommercialOrder')
    def test_chained_partial_refunds_until_full(
        self,
        mock_order_cls,
        mock_payment_cls,
        mock_db,
        mock_payment_changed,
        mock_status_changed,
        mock_refunded,
    ):
        from nodeone.core.commerce.constants import (
            ORDER_PAYMENT_STATUS_PAID,
            ORDER_PAYMENT_STATUS_UNPAID,
            PAYMENT_STATUS_PARTIAL_REFUND,
            PAYMENT_STATUS_REFUNDED,
        )
        from nodeone.core.commerce.payment import PaymentService

        order = MagicMock()
        order.id = 12
        order.order_ref = 'POS-0012'
        order.status = 'delivered'
        order.payment_status = ORDER_PAYMENT_STATUS_PAID
        order.fiscal_status = 'not_required'
        order.amount_paid = 20.0
        order.grand_total = 20.0
        order.version = 1

        def _sync():
            order.payment_status = ORDER_PAYMENT_STATUS_UNPAID
            return ORDER_PAYMENT_STATUS_UNPAID

        order.sync_payment_status.side_effect = _sync

        pay_row = MagicMock()
        pay_row.id = 7
        pay_row.order_id = 12
        pay_row.payment_ref = 'PAY-0012'
        pay_row.status = 'captured'
        pay_row.amount = 20.0
        pay_row.refunded_amount = 0.0
        pay_row.payment_type = 'card'
        pay_row.cash_shift_id = None
        pay_row.currency = 'USD'
        pay_row.captured_at = None

        mock_payment_cls.query.filter_by.return_value.first.return_value = pay_row
        mock_order_cls.query.filter_by.return_value.first.return_value = order

        PaymentService.refund(1, 7, amount=8.0)
        self.assertEqual(pay_row.refunded_amount, 8.0)
        self.assertEqual(pay_row.status, PAYMENT_STATUS_PARTIAL_REFUND)
        self.assertEqual(order.amount_paid, 12.0)

        PaymentService.refund(1, 7, amount=12.0)
        self.assertEqual(pay_row.refunded_amount, 20.0)
        self.assertEqual(pay_row.status, PAYMENT_STATUS_REFUNDED)
        self.assertEqual(order.amount_paid, 0.0)
        self.assertEqual(mock_refunded.call_count, 2)

    @patch('nodeone.core.commerce.payment.CoreCommercialPayment')
    def test_refund_rejects_when_nothing_left(self, mock_payment_cls):
        from nodeone.core.commerce.order import OrderValidationError
        from nodeone.core.commerce.payment import PaymentService

        pay_row = MagicMock()
        pay_row.status = 'partial_refund'
        pay_row.amount = 10.0
        pay_row.refunded_amount = 10.0
        mock_payment_cls.query.filter_by.return_value.first.return_value = pay_row

        with self.assertRaises(OrderValidationError):
            PaymentService.refund(1, 50, amount=1.0)


class TestCashRegisterService(unittest.TestCase):
    @patch('nodeone.core.commerce.cash.CashRegisterService.publish_shift_opened')
    @patch('app.db')
    @patch('nodeone.core.commerce.cash.CoreCashShift')
    def test_open_shift_rejects_duplicate(self, mock_shift_cls, mock_db, _publish):
        from nodeone.core.commerce.cash import CashRegisterService
        from nodeone.core.commerce.order import OrderValidationError

        mock_shift_cls.query.filter_by.return_value.first.return_value = MagicMock()
        with self.assertRaises(OrderValidationError):
            CashRegisterService.open_shift(1, register_ref='REG-1', opening_balance=50)

    @patch('nodeone.core.commerce.cash.CashRegisterService.publish_shift_reconciling')
    @patch('nodeone.core.commerce.cash.CashRegisterService.publish_count_recorded')
    @patch('nodeone.core.commerce.cash.CashRegisterService.compute_expected_balance', return_value=120.0)
    @patch('app.db')
    @patch('nodeone.core.commerce.cash.CoreCashShift')
    def test_begin_reconcile_hides_variance_from_dto(
        self,
        mock_shift_cls,
        mock_db,
        mock_expected,
        _count,
        _reconciling,
    ):
        from nodeone.core.commerce.cash import CashRegisterService
        from nodeone.core.commerce.constants import CASH_SHIFT_OPEN, CASH_SHIFT_RECONCILING

        row = MagicMock()
        row.id = 2
        row.organization_id = 1
        row.register_ref = 'REG-1'
        row.status = CASH_SHIFT_OPEN
        row.opening_balance = 100.0
        row.counted_amount = None
        row.expected_balance = None
        row.closing_balance = None
        row.opened_at = None
        row.closed_at = None
        mock_shift_cls.query.filter_by.return_value.first.return_value = row

        dto = CashRegisterService.begin_reconcile(1, 2, counted_amount=115.0)

        self.assertEqual(row.status, CASH_SHIFT_RECONCILING)
        self.assertEqual(row.counted_amount, 115.0)
        self.assertEqual(row.expected_balance, 120.0)
        self.assertIsNone(dto.expected_balance)
        self.assertIsNone(dto.cash_variance)

    @patch('nodeone.core.commerce.cash.CashRegisterService.publish_shift_closed')
    @patch('app.db')
    @patch('nodeone.core.commerce.cash.CoreCashShift')
    def test_close_shift_requires_reconciling(self, mock_shift_cls, mock_db, _publish):
        from nodeone.core.commerce.cash import CashRegisterService
        from nodeone.core.commerce.constants import CASH_SHIFT_OPEN
        from nodeone.core.commerce.order import OrderValidationError

        row = MagicMock()
        row.status = CASH_SHIFT_OPEN
        mock_shift_cls.query.filter_by.return_value.first.return_value = row

        with self.assertRaises(OrderValidationError):
            CashRegisterService.close_shift(1, 2)


class TestCommerceFiscalService(unittest.TestCase):
    @patch('nodeone.core.commerce.fiscal.AuditService.publish_domain_event')
    @patch('nodeone.core.commerce.fiscal.CoreCommercialOrder')
    def test_request_for_pending_order(self, mock_order_cls, mock_publish):
        from nodeone.core.commerce.events import COMMERCE_INVOICE_REQUESTED
        from nodeone.core.commerce.fiscal import CommerceFiscalService

        order = MagicMock()
        order.id = 3
        order.order_ref = 'POS-0003'
        order.fiscal_status = 'pending'
        order.grand_total = 20.0
        order.contact_id = None
        order.payment_status = 'paid'
        mock_order_cls.query.filter_by.return_value.first.return_value = order

        result = CommerceFiscalService.request_for_order(1, 3)
        self.assertEqual(result['status'], 'queued')
        mock_publish.assert_called_once()
        self.assertEqual(mock_publish.call_args[0][1], COMMERCE_INVOICE_REQUESTED)

    @patch('nodeone.core.commerce.fiscal.CoreCommercialOrder')
    def test_process_pending_without_contact_stays_pending(self, mock_order_cls):
        from nodeone.core.commerce.fiscal import CommerceFiscalService

        order = MagicMock()
        order.id = 4
        order.order_ref = 'POS-0004'
        order.fiscal_status = 'pending'
        order.contact_id = None
        mock_order_cls.query.filter_by.return_value.first.return_value = order

        result = CommerceFiscalService.process_pending_order(1, 4)
        self.assertEqual(result['status'], 'pending')
        self.assertEqual(result['reason'], 'no_fiscal_contact')

    @patch('nodeone.core.commerce.fiscal.CommerceFiscalService.process_from_event')
    def test_invoice_requested_handler_swallows_errors(self, mock_process):
        from nodeone.core.commerce.fiscal_handlers import _on_invoice_requested
        from nodeone.core.platform.events import DomainEventMessage

        mock_process.side_effect = RuntimeError('boom')
        msg = DomainEventMessage(
            id=1,
            organization_id=1,
            event_type='commerce.invoice.requested',
            payload={'order_id': 9},
            source_app_id='eposone',
            created_at=None,
        )
        _on_invoice_requested(msg)

    @patch('nodeone.core.commerce.fiscal_handlers.subscribe')
    def test_register_handlers_once(self, mock_subscribe):
        import nodeone.core.commerce.fiscal_handlers as mod

        mod._REGISTERED = False
        mod.register_commerce_fiscal_handlers()
        mod.register_commerce_fiscal_handlers()
        self.assertEqual(mock_subscribe.call_count, 1)


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
